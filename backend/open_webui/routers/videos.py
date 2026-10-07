import asyncio
import json
import logging
from typing import Optional, Any

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from open_webui.models.config import Config
from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.video_defaults import resolve_duration, resolve_size

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
    'VIDEOS_OPENAI_API_ENDPOINT': 'video_generation.openai.endpoint',
    'VIDEO_DURATIONS': 'video_generation.durations',
    'VIDEO_DURATION_DEFAULT': 'video_generation.duration_default',
    'VIDEO_ASPECT_RATIOS': 'video_generation.aspect_ratios',
    'VIDEO_ASPECT_RATIO_DEFAULT': 'video_generation.aspect_ratio_default',
    'VIDEO_SIZES': 'video_generation.sizes',
    'VIDEO_SIZE_DEFAULT': 'video_generation.size_default',
    'VIDEO_IMAGE_INPUT_ENABLED': 'video_generation.image_input.enable',
    'VIDEO_IMAGE_INPUT_MAX': 'video_generation.image_input.max',
    'VIDEO_IMAGE_INPUT_MODE': 'video_generation.image_input.mode',
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
    'VIDEOS_OPENAI_API_ENDPOINT': '/video/generations',
    'VIDEO_DURATIONS': '4 - 12',
    'VIDEO_DURATION_DEFAULT': '12',
    'VIDEO_ASPECT_RATIOS': '21:9, 16:9, 4:3, 1:1, 3:4, 9:16',
    'VIDEO_ASPECT_RATIO_DEFAULT': '16:9',
    'VIDEO_SIZES': '720P, 1080P, 1024x1024',
    'VIDEO_SIZE_DEFAULT': '720P',
    'VIDEO_IMAGE_INPUT_ENABLED': True,
    'VIDEO_IMAGE_INPUT_MAX': 5,
    'VIDEO_IMAGE_INPUT_MODE': 'image',
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
        log.warning(f'Failed to fetch video config values: {e}')
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
                    f'{base_url}/models',
                    headers={'Authorization': f'Bearer {api_key}'},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if 'data' in data and isinstance(data['data'], list):
                            return [{'id': m['id'], 'name': m.get('id', '')} for m in data['data']]
        except Exception as e:
            log.debug(f'Failed to fetch models from OpenAI endpoint: {e}')

    return default_models


@router.post('/verify')
async def verify_connection(request: Request, form_data: dict, user=Depends(get_admin_user)):
    url = (form_data.get('url') or '').rstrip('/')
    if not url:
        raise HTTPException(status_code=400, detail='URL is required')
    return {'status': True}


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
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

    endpoint = config.get('VIDEOS_OPENAI_API_ENDPOINT') or '/video/generations'
    if not endpoint.startswith('/'):
        endpoint = '/' + endpoint
    url = f'{base_url}{endpoint}'

    model = form_data.get('model') or config.get('VIDEO_GENERATION_MODEL') or 'kling-video'
    payload = {
        'model': model,
        'prompt': form_data.get('prompt', ''),
    }

    # Mode
    if form_data.get('mode'):
        payload['mode'] = form_data.get('mode')
    elif config.get('VIDEO_GENERATION_MODE'):
        payload['mode'] = config.get('VIDEO_GENERATION_MODE')

    # Size / Resolution.  Resolve this once and only merge non-empty request
    # values below, so an omitted/blank tool argument cannot replace the Admin
    # default with an accidental null value.
    size_val = resolve_size(
        form_data.get('size'),
        config.get('VIDEO_SIZE_DEFAULT'),
        config.get('VIDEO_SIZE'),
    )
    if size_val:
        payload['size'] = size_val

    # Duration
    duration_val = resolve_duration(form_data.get('duration'), config.get('VIDEO_DURATION_DEFAULT'))
    if duration_val:
        payload['duration'] = duration_val

    # Aspect Ratio
    aspect_ratio_val = form_data.get('aspect_ratio') or config.get('VIDEO_ASPECT_RATIO_DEFAULT')
    if aspect_ratio_val:
        payload['aspect_ratio'] = aspect_ratio_val

    # Images / Image references
    images = form_data.get('images')
    if images and isinstance(images, list) and len(images) > 0:
        max_imgs = int(config.get('VIDEO_IMAGE_INPUT_MAX') or 5)
        allowed_images = images[:max_imgs]
        payload['images'] = allowed_images
        payload['image'] = allowed_images[0]
        img_mode = config.get('VIDEO_IMAGE_INPUT_MODE') or 'image'
        if not form_data.get('mode'):
            payload['mode'] = img_mode
    elif form_data.get('image'):
        payload['image'] = form_data.get('image')
        img_mode = config.get('VIDEO_IMAGE_INPUT_MODE') or 'image'
        if not form_data.get('mode'):
            payload['mode'] = img_mode

    extra_params = config.get('VIDEOS_OPENAI_API_PARAMS') or {}
    if isinstance(extra_params, dict):
        payload.update(extra_params)
    for k, v in form_data.items():
        if k not in ['prompt', 'model', 'size', 'duration'] and v is not None:
            payload[k] = v

    async with aiohttp.ClientSession() as session:
        try:
            for attempt in range(4):
                modified_payload = False
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status >= 400:
                        err_text = await response.text()
                        log.error(f'Video generation upstream error ({response.status}): {err_text}')
                        try:
                            err_json = json.loads(err_text)
                            err_msg = (
                                err_json.get('error', {}).get('message')
                                if isinstance(err_json.get('error'), dict)
                                else err_json.get('error')
                                or err_json.get('detail')
                                or err_json.get('message')
                                or err_text
                            )
                            # Handle stringified JSON in message (like Pixrouter's invalid_request)
                            if isinstance(err_msg, str) and err_msg.startswith('{') and 'invalid_request' in err_msg:
                                inner_err = json.loads(err_msg)
                                param_name = inner_err.get('data', {}).get('param')
                                if param_name and param_name in payload and attempt < 3:
                                    log.info(
                                        f"Removing unsupported param '{param_name}' and retrying ({attempt + 1}/3)..."
                                    )
                                    del payload[param_name]
                                    modified_payload = True
                        except Exception:
                            err_msg = err_text

                        if attempt == 3 or not modified_payload or response.status not in [400]:
                            raise HTTPException(
                                status_code=response.status, detail=f'API Error ({response.status}): {err_msg}'
                            )
                        else:
                            continue

                    res_data = await response.json()
                    break

                # Extract task or video items
                items = []
                if isinstance(res_data, list):
                    items = res_data
                elif isinstance(res_data, dict):
                    if 'data' in res_data and isinstance(res_data['data'], list):
                        items = res_data['data']
                    elif 'videos' in res_data and isinstance(res_data['videos'], list):
                        items = res_data['videos']
                    else:
                        items = [res_data]

                # If the item is an asynchronous task (queued/processing), poll until it succeeds
                final_results = []
                for item in items:
                    task_id = item.get('task_id') or item.get('id')
                    status = str(item.get('status', '')).lower()
                    url_val = item.get('url') or (item.get('metadata') or {}).get('url') or item.get('result_url')

                    if (
                        not url_val
                        and task_id
                        and status in ['queued', 'processing', 'submitted', 'pending', 'running']
                    ):
                        poll_url = f'{base_url}/video/generations/{task_id}'
                        # Poll every 4 seconds for up to 180 seconds
                        for _ in range(45):
                            await asyncio.sleep(4)
                            try:
                                async with session.get(
                                    poll_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
                                ) as poll_resp:
                                    if poll_resp.status == 200:
                                        p_data = await poll_resp.json()
                                        d = p_data.get('data') or p_data
                                        p_status = str(d.get('status', '')).upper()
                                        found_url = (
                                            d.get('result_url')
                                            or (d.get('data') or {}).get('metadata', {}).get('url')
                                            or (d.get('metadata') or {}).get('url')
                                            or d.get('url')
                                        )
                                        if found_url and (
                                            p_status in ['SUCCESS', 'SUCCEEDED', 'COMPLETED']
                                            or 'http' in str(found_url)
                                        ):
                                            item['url'] = found_url
                                            break
                                        if p_status in ['FAIL', 'FAILED', 'ERROR']:
                                            break
                            except Exception as pe:
                                log.debug(f'Video task poll exception: {pe}')

                    if item.get('url'):
                        final_results.append(item)
                    elif item.get('result_url'):
                        final_results.append({'url': item.get('result_url'), 'id': task_id})
                    else:
                        final_results.append(item)

                return final_results
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
