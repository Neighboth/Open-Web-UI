import asyncio
import logging
from typing import Optional, Any

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from open_webui.models.config import Config
from open_webui.utils.auth import get_admin_user, get_verified_user

log = logging.getLogger(__name__)

router = APIRouter()

VIDEO_CONFIG_KEYS = {
    'ENABLE_VIDEO_GENERATION': 'video_generation.enable',
    'ENABLE_VIDEO_PROMPT_GENERATION': 'video_generation.prompt_generation.enable',
    'VIDEO_GENERATION_ENGINE': 'video_generation.engine',
    'VIDEO_GENERATION_MODEL': 'video_generation.model',
    'VIDEO_SIZE': 'video_generation.size',
    'VIDEO_STEPS': 'video_generation.steps',
    'VIDEOS_OPENAI_API_BASE_URL': 'video_generation.openai.api_base_url',
    'VIDEOS_OPENAI_API_KEY': 'video_generation.openai.api_key',
    'VIDEOS_OPENAI_API_VERSION': 'video_generation.openai.api_version',
    'VIDEOS_OPENAI_API_PARAMS': 'video_generation.openai.params',
    'AUTOMATIC1111_BASE_URL': 'video_generation.automatic1111.base_url',
    'AUTOMATIC1111_API_AUTH': 'video_generation.automatic1111.api_auth',
    'AUTOMATIC1111_PARAMS': 'video_generation.automatic1111.params',
    'COMFYUI_BASE_URL': 'video_generation.comfyui.base_url',
    'COMFYUI_API_KEY': 'video_generation.comfyui.api_key',
    'COMFYUI_WORKFLOW': 'video_generation.comfyui.workflow',
    'COMFYUI_WORKFLOW_NODES': 'video_generation.comfyui.nodes',
    'VIDEOS_GEMINI_API_BASE_URL': 'video_generation.gemini.api_base_url',
    'VIDEOS_GEMINI_API_KEY': 'video_generation.gemini.api_key',
    'VIDEOS_GEMINI_ENDPOINT_METHOD': 'video_generation.gemini.endpoint_method',
    'ENABLE_VIDEO_EDIT': 'videos.edit.enable',
    'VIDEO_EDIT_ENGINE': 'videos.edit.engine',
    'VIDEO_EDIT_MODEL': 'videos.edit.model',
    'VIDEO_EDIT_SIZE': 'videos.edit.size',
    'VIDEOS_EDIT_OPENAI_API_BASE_URL': 'videos.edit.openai.api_base_url',
    'VIDEOS_EDIT_OPENAI_API_KEY': 'videos.edit.openai.api_key',
    'VIDEOS_EDIT_OPENAI_API_VERSION': 'videos.edit.openai.api_version',
    'VIDEOS_EDIT_GEMINI_API_BASE_URL': 'videos.edit.gemini.api_base_url',
    'VIDEOS_EDIT_GEMINI_API_KEY': 'videos.edit.gemini.api_key',
    'VIDEOS_EDIT_COMFYUI_BASE_URL': 'videos.edit.comfyui.base_url',
    'VIDEOS_EDIT_COMFYUI_API_KEY': 'videos.edit.comfyui.api_key',
    'VIDEOS_EDIT_COMFYUI_WORKFLOW': 'videos.edit.comfyui.workflow',
    'VIDEOS_EDIT_COMFYUI_WORKFLOW_NODES': 'videos.edit.comfyui.nodes',
}

DEFAULT_CONFIG = {
    'ENABLE_VIDEO_GENERATION': False,
    'ENABLE_VIDEO_PROMPT_GENERATION': True,
    'VIDEO_GENERATION_ENGINE': 'openai',
    'VIDEO_GENERATION_MODEL': '',
    'VIDEO_SIZE': '1024x1024',
    'VIDEO_STEPS': 30,
    'VIDEOS_OPENAI_API_BASE_URL': '',
    'VIDEOS_OPENAI_API_KEY': '',
    'VIDEOS_OPENAI_API_VERSION': '',
    'VIDEOS_OPENAI_API_PARAMS': {},
    'AUTOMATIC1111_BASE_URL': '',
    'AUTOMATIC1111_API_AUTH': '',
    'AUTOMATIC1111_PARAMS': {},
    'COMFYUI_BASE_URL': '',
    'COMFYUI_API_KEY': '',
    'COMFYUI_WORKFLOW': '',
    'COMFYUI_WORKFLOW_NODES': [],
    'VIDEOS_GEMINI_API_BASE_URL': '',
    'VIDEOS_GEMINI_API_KEY': '',
    'VIDEOS_GEMINI_ENDPOINT_METHOD': 'predict',
    'ENABLE_VIDEO_EDIT': False,
    'VIDEO_EDIT_ENGINE': 'openai',
    'VIDEO_EDIT_MODEL': '',
    'VIDEO_EDIT_SIZE': '1024x1024',
    'VIDEOS_EDIT_OPENAI_API_BASE_URL': '',
    'VIDEOS_EDIT_OPENAI_API_KEY': '',
    'VIDEOS_EDIT_OPENAI_API_VERSION': '',
    'VIDEOS_EDIT_GEMINI_API_BASE_URL': '',
    'VIDEOS_EDIT_GEMINI_API_KEY': '',
    'VIDEOS_EDIT_COMFYUI_BASE_URL': '',
    'VIDEOS_EDIT_COMFYUI_API_KEY': '',
    'VIDEOS_EDIT_COMFYUI_WORKFLOW': '',
    'VIDEOS_EDIT_COMFYUI_WORKFLOW_NODES': [],
}

async def get_config_values() -> dict:
    try:
        values = await Config.get_many(*VIDEO_CONFIG_KEYS.values())
    except Exception as e:
        log.warning(f"Failed to fetch video config values: {e}")
        values = {}

    result = {}
    for field, storage_key in VIDEO_CONFIG_KEYS.items():
        if storage_key in values and values[storage_key] is not None:
            result[field] = values[storage_key]
        else:
            result[field] = DEFAULT_CONFIG.get(field)
    return result

@router.get('/config')
async def get_config(request: Request, user=Depends(get_admin_user)):
    return await get_config_values()

@router.post('/config')
@router.post('/config/update')
async def update_config(request: Request, form_data: dict, user=Depends(get_admin_user)):
    updates = {}
    for field, storage_key in VIDEO_CONFIG_KEYS.items():
        if field in form_data:
            updates[storage_key] = form_data[field]
    if updates:
        await Config.upsert(updates)
    return await get_config_values()

@router.get('/models')
async def get_models(request: Request, user=Depends(get_verified_user)):
    config = await get_config_values()
    engine = config.get('VIDEO_GENERATION_ENGINE', 'openai')
    base_url = config.get('VIDEOS_OPENAI_API_BASE_URL', '')
    api_key = config.get('VIDEOS_OPENAI_API_KEY', '')

    if not api_key:
        try:
            from open_webui.utils.direct_connections import get_user_direct_connection
            u_key, u_url, _ = get_user_direct_connection(user)
            if u_key:
                api_key = u_key
                if not base_url:
                    base_url = u_url or 'https://api.openai.com/v1'
        except Exception:
            pass

    default_models = [
        {'id': 'sora', 'name': 'Sora'},
        {'id': 'runway-gen3', 'name': 'Runway Gen-3'},
        {'id': 'luma-dream-machine', 'name': 'Luma Dream Machine'},
        {'id': 'cogvideox', 'name': 'CogVideoX'},
        {'id': 'kling-video', 'name': 'Kling Video'},
    ]

    if engine == 'openai' and api_key:
        base_url = (base_url or 'https://api.openai.com/v1').rstrip('/')
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if 'data' in data and isinstance(data['data'], list):
                            return [{'id': m['id'], 'name': m.get('id', '')} for m in data['data']]
        except Exception as e:
            log.debug(f"Failed to fetch models from OpenAI endpoint: {e}")

    return default_models

@router.post('/verify')
async def verify_connection(request: Request, form_data: dict, user=Depends(get_admin_user)):
    url = (form_data.get('url') or '').rstrip('/')
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    return {"status": True}

@router.post('/generations')
async def video_generations(request: Request, form_data: dict, user=Depends(get_verified_user)):
    config = await get_config_values()
    if not config.get('ENABLE_VIDEO_GENERATION', False):
        raise HTTPException(status_code=400, detail='Video generation is disabled')

    base_url = config.get('VIDEOS_OPENAI_API_BASE_URL')
    api_key = config.get('VIDEOS_OPENAI_API_KEY')

    if not api_key:
        try:
            from open_webui.utils.direct_connections import get_user_direct_connection
            u_key, u_url, _ = get_user_direct_connection(user)
            if u_key:
                api_key = u_key
                if not base_url:
                    base_url = u_url or 'https://api.openai.com/v1'
        except Exception:
            pass

    base_url = (base_url or 'https://api.openai.com/v1').rstrip('/')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    url = f'{base_url}/video/generations'

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=form_data) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
