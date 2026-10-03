
import asyncio
import logging
from typing import Optional

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from open_webui.models.users import Users
from open_webui.utils.auth import get_verified_user
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.config import Config

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS['MODELS'])

router = APIRouter()

class VideoGenerationConfig(BaseModel):
    ENABLE_VIDEO_GENERATION: bool
    VIDEO_GENERATION_ENGINE: str
    VIDEO_GENERATION_MODEL: str
    VIDEOS_OPENAI_API_BASE_URL: str
    VIDEOS_OPENAI_API_KEY: str

@router.get('/config')
async def get_config(request: Request, user=Depends(get_verified_user)):
    return {
        'video_generation_enabled': await Config.get('video_generation.enable', False),
        'video_generation_engine': await Config.get('video_generation.engine', 'openai'),
        'video_generation_model': await Config.get('video_generation.model', ''),
        'videos_openai_api_base_url': await Config.get('video_generation.openai.api_base_url', 'https://api.openai.com/v1'),
        'videos_openai_api_key': await Config.get('video_generation.openai.api_key', ''),
    }

@router.post('/config')
async def update_config(request: Request, form_data: VideoGenerationConfig, user=Depends(get_verified_user)):
    if user.role != 'admin':
        raise HTTPException(status_code=403, detail='Unauthorized')
    await Config.upsert({'video_generation.enable': form_data.ENABLE_VIDEO_GENERATION})
    await Config.upsert({'video_generation.engine': form_data.VIDEO_GENERATION_ENGINE})
    await Config.upsert({'video_generation.model': form_data.VIDEO_GENERATION_MODEL})
    await Config.upsert({'video_generation.openai.api_base_url': form_data.VIDEOS_OPENAI_API_BASE_URL})
    await Config.upsert({'video_generation.openai.api_key': form_data.VIDEOS_OPENAI_API_KEY})
    return await get_config(request, user)

@router.post('/generations')
async def video_generations(request: Request, form_data: dict, user=Depends(get_verified_user)):
    # Very similar to images/generations but for video
    if not await Config.get('video_generation.enable', False):
        raise HTTPException(status_code=400, detail='Video generation is disabled')

    # Get OpenAI API credentials
    base_url = await Config.get('video_generation.openai.api_base_url')
    api_key = await Config.get('video_generation.openai.api_key')
    
    if not api_key:
        from open_webui.utils.direct_connections import get_user_direct_connection
        u_key, u_url, _ = get_user_direct_connection(user)
        if u_key:
            api_key = u_key
            if not base_url:
                base_url = u_url or 'https://api.openai.com/v1'

    base_url = (base_url or 'https://api.openai.com/v1').rstrip('/')
    headers = {}
    headers['Authorization'] = f'Bearer {api_key}'
    headers['Content-Type'] = 'application/json'

    url = f'{base_url}/video/generations'
    
    # Send request
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=form_data) as response:
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
