"""Live check of the Realtime verification endpoint against the real provider."""

import asyncio
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / 'backend'
sys.path.insert(0, str(BACKEND))

PIX_KEY = os.environ.get('PIX_KEY', '')
PIX_URL = os.environ.get('PIX_URL', 'https://provider.example.test/v1')
REALTIME_MODEL = os.environ.get('REALTIME_MODEL', 'google/gemini-3.1-flash-live-preview')
SECOND_REALTIME_MODEL = os.environ.get('SECOND_REALTIME_MODEL', 'mistralai/voxtral-mini-realtime-latest')

ADMIN_CONFIG = {
    'audio.realtime.enabled': True,
    'audio.realtime.provider': 'openai',
    'audio.realtime.auth_type': 'api_key',
    'audio.realtime.openai.api_base_url': '',
    'audio.realtime.openai.api_key': '',
    'audio.realtime.model': REALTIME_MODEL,
    'audio.realtime.voice': 'Marathon',
    'audio.realtime.transcription_model': 'openai/whisper-large-v3',
}

USER_SETTINGS = {
    'ui': {
        'directConnections': {
            'OPENAI_API_BASE_URLS': [PIX_URL],
            'OPENAI_API_KEYS': [PIX_KEY],
            'OPENAI_API_CONFIGS': {'0': {'enable': True}},
        }
    }
}


class FakeUser:
    """A stand-in for the signed-in Admin; no real account data is used."""

    id = '00000000-0000-4000-8000-000000000000'
    role = 'admin'
    settings = USER_SETTINGS
    email = 'admin@example.test'
    name = 'Admin'


async def main():
    from open_webui.models.config import Config
    from open_webui.routers.audio.realtime import verify_realtime_connection

    async def get_many(*keys):
        return {k: ADMIN_CONFIG.get(k) for k in keys}

    async def get(key, default=None):
        return ADMIN_CONFIG.get(key, default)

    Config.get_many = staticmethod(get_many)
    Config.get = staticmethod(get)

    for model in [REALTIME_MODEL, SECOND_REALTIME_MODEL]:
        ADMIN_CONFIG['audio.realtime.model'] = model
        result = await verify_realtime_connection(request=None, user=FakeUser())
        print(f'\nmodel = {model}')
        print(f'  status = {result.get("status")}')
        print(f'  error  = {result.get("error")}')
        print(f'  message= {result.get("message")}')


if __name__ == '__main__':
    asyncio.run(main())
