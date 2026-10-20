"""Live end-to-end verification of the video / image / Kasm fixes.

Runs the real router code against the real providers the Admin uses
(PixRouter + Kasm Workspaces) using the configuration from the exported
config file and the production database.

Run with:
    set PYTHONPATH=Z:\\open-web-ui\\backend
    set WEBUI_SECRET_KEY=...
    python test/live_provider_check.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / 'backend'
sys.path.insert(0, str(BACKEND))

PIX_KEY = os.environ.get('PIX_KEY', '')
PIX_URL = 'https://pixrouter.com/v1'
KASM_URL = 'https://38.210.77.108:8443'
KASM_API_KEY = os.environ.get('KASM_API_KEY', '')
KASM_API_SECRET = os.environ.get('KASM_API_SECRET', '')
KASM_USER = os.environ.get('KASM_USER', '')
KASM_PASSWORD = os.environ.get('KASM_PASSWORD', '')

# The Admin's saved configuration (from webui.db).
ADMIN_CONFIG = {
    'video_generation.enable': True,
    'video_generation.engine': 'openai',
    'video_generation.model': 'agnes/agnes-video-2.5-flash',
    'video_generation.size': '720P',
    'video_generation.openai.api_base_url': '',
    'video_generation.openai.api_key': '',
    'video_generation.openai.params': {'mode': 'text'},
    'video_generation.openai.endpoint': '/video/generations',
    'video_generation.durations': '4 - 12',
    'video_generation.duration_default': '12',
    'video_generation.aspect_ratios': '21:9, 16:9, 4:3, 1:1, 3:4, 9:16',
    'video_generation.aspect_ratio_default': '16:9',
    'video_generation.sizes': '720P',
    'video_generation.size_default': '720P',
    'video_generation.image_input.enable': True,
    'video_generation.image_input.max': 5,
    'video_generation.image_input.mode': 'image',
    'image_generation.enable': True,
    'image_generation.engine': 'openai',
    'image_generation.model': 'agnes/agnes-image-2.5-flash',
    'image_generation.size': '4096x4096',
    'image_generation.steps': 50,
    'image_generation.prompt.enable': True,
    'image_generation.openai.api_base_url': '',
    'image_generation.openai.api_key': '',
    'image_generation.openai.params': {'ratio': '1:1'},
}

USER_SETTINGS = {
    'ui': {
        'directConnections': {
            'OPENAI_API_BASE_URLS': [PIX_URL],
            'OPENAI_API_KEYS': [PIX_KEY],
            'OPENAI_API_CONFIGS': {'0': {'enable': True, 'connection_type': 'external'}},
        }
    }
}

RESULTS = []


def record(name, ok, detail):
    RESULTS.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}\n       {detail}")


class FakeUser:
    id = '84593fb0-1617-40ed-8bbd-4bd7a0fa0c8b'
    role = 'admin'
    settings = USER_SETTINGS
    email = 'salihsimsekhp@gmail.com'
    name = 'Salih'


def patch_config(config_cls, values):
    """Serve the Admin's configuration from memory instead of the database."""

    async def get_many(*keys):
        return {k: values.get(k) for k in keys}

    async def get(key, default=None):
        return values.get(key, default)

    config_cls.get_many = staticmethod(get_many)
    config_cls.get = staticmethod(get)


def record_payloads(sink):
    """Wrap aiohttp.ClientSession.post so the outgoing JSON body is captured.

    The real request still goes out, so the provider answers exactly as it
    would in production.
    """
    import aiohttp

    original = aiohttp.ClientSession.post

    def wrapper(self, url, *args, **kwargs):
        if kwargs.get('json') is not None:
            sink.append((str(url), kwargs['json']))
        return original(self, url, *args, **kwargs)

    aiohttp.ClientSession.post = wrapper
    return original


def fake_post_session(status, body, sink=None):
    """Return a ClientSession replacement that always answers with `body`."""
    import aiohttp

    original = aiohttp.ClientSession

    class Resp:
        def __init__(self):
            self.status = status

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def text(self):
            return body

        async def json(self, **k):
            return {}

    class FakeSession:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def post(self, url, **kwargs):
            if sink is not None and kwargs.get('json') is not None:
                sink.append((str(url), kwargs['json']))
            return Resp()

    aiohttp.ClientSession = FakeSession
    return original


def fake_image_session(status, body, sink=None):
    """Patch images.get_session with a session that always answers with `body`."""
    import open_webui.routers.images as images

    class Resp:
        def __init__(self):
            self.status = status

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def text(self):
            return body

        async def json(self, **k):
            return {}

    class FakeSession:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def post(self, url, **kwargs):
            if sink is not None and kwargs.get('json') is not None:
                sink.append((str(url), kwargs['json']))
            return Resp()

    original = images.get_session

    async def fake_get_session(*a, **k):
        return FakeSession()

    images.get_session = fake_get_session
    return original


async def main():
    from open_webui.models.config import Config
    import open_webui.routers.videos as videos
    import open_webui.routers.images as images
    import open_webui.routers.browser as browser
    from open_webui.utils.browser_session import is_safe_kasm_connection_url

    user = FakeUser()
    patch_config(Config, ADMIN_CONFIG)

    # ------------------------------------------------------------------
    print('\n=== 1) VIDEO: admin "mode" degeri payload-a ekleniyor mu? (canli istek) ===')
    # ------------------------------------------------------------------
    import aiohttp

    sent = []
    original_post = record_payloads(sent)
    try:
        await videos.video_generations(request=None, form_data={'prompt': 'a red cube'}, user=user)
        err = 'hata firlatilmadi'
    except Exception as e:
        err = f'{type(e).__name__}: {e}'
    finally:
        aiohttp.ClientSession.post = original_post

    payloads = [p for _, p in sent]
    first = payloads[0] if payloads else {}
    record(
        'video: admin "mode" degeri payload-a ekleniyor',
        first.get('mode') == 'text',
        f"gonderilen payload = {json.dumps(first, ensure_ascii=False)}  |  hata = {err[:160]}",
    )

    # ------------------------------------------------------------------
    print('\n=== 2) VIDEO: desteklenmeyen alan otomatik dusuruluyor (duration) ===')
    # ------------------------------------------------------------------
    attempts = []
    original_session = fake_post_session(
        400,
        json.dumps(
            {
                'code': 'fail_to_fetch_task',
                'message': json.dumps(
                    {
                        'code': 'invalid_request',
                        'message': 'duration is not an allowed request field (request id: test)',
                        'data': {'param': 'duration'},
                    }
                ),
                'data': None,
            }
        ),
        sink=attempts,
    )
    try:
        await videos.video_generations(request=None, form_data={'prompt': 'x'}, user=user)
        err = 'hata firlatilmadi'
    except Exception as e:
        err = f'{type(e).__name__}: {e}'
    finally:
        aiohttp.ClientSession = original_session

    record(
        'video: "not an allowed request field" hatasinda alan dusurulup tekrar denenir',
        len(attempts) >= 2 and 'duration' not in attempts[-1][1],
        f'deneme sayisi = {len(attempts)}, son payload = {json.dumps(attempts[-1][1]) if attempts else None}',
    )

    # ------------------------------------------------------------------
    print('\n=== 3) VIDEO: "required" hatasinda parametre SILINMIYOR ===')
    # ------------------------------------------------------------------
    attempts2 = []
    original_session = fake_post_session(
        400,
        json.dumps(
            {
                'code': 'fail_to_fetch_task',
                'message': json.dumps(
                    {
                        'code': 'invalid_request',
                        'message': 'mode is required (request id: test)',
                        'data': {'param': 'mode'},
                    }
                ),
                'data': None,
            }
        ),
        sink=attempts2,
    )
    try:
        await videos.video_generations(request=None, form_data={'prompt': 'x'}, user=user)
        err = 'hata firlatilmadi'
    except Exception as e:
        err = f'{type(e).__name__}: {e}'
    finally:
        aiohttp.ClientSession = original_session

    record(
        'video: "required" hatasinda mode payload-da kalir, tek deneme yapilir',
        len(attempts2) == 1 and attempts2[0][1].get('mode') == 'text',
        f'deneme sayisi = {len(attempts2)}, hata = {err[:220]}',
    )

    # ------------------------------------------------------------------
    print('\n=== 4) IMAGE: saglayici hata mesaji artik gorunuyor ===')
    # ------------------------------------------------------------------
    original_session = fake_image_session(
        400,
        json.dumps(
            {
                'error': {
                    'message': 'Model agnes-image-2.5-flash is an image model. Use /v1/images/generations.',
                    'type': 'AgnesAI_error',
                    'code': 'invalid_request',
                }
            }
        ),
    )
    try:
        await images.image_generations(
            request=None,
            form_data=images.CreateImageForm(prompt='a red cube'),
            user=user,
        )
        msg = 'hata firlatilmadi'
    except Exception as e:
        msg = f'{type(e).__name__}: {e}'
    finally:
        images.get_session = original_session

    record(
        'image: saglayicinin "is an image model" mesaji HTTPException detail-inde',
        'is an image model' in msg and 'gpt-image-1' in msg,
        f'hata = {msg[:300]}',
    )

    # ------------------------------------------------------------------
    print('\n=== 5) IMAGE: desteklenmeyen boyut 1024x1024 ile tekrar denenir ===')
    # ------------------------------------------------------------------
    image_sends = []
    original_session = fake_image_session(502, 'upstream error: size not supported', sink=image_sends)
    try:
        await images.image_generations(
            request=None,
            form_data=images.CreateImageForm(prompt='a red cube'),
            user=user,
        )
        msg = 'hata firlatilmadi'
    except Exception as e:
        msg = f'{type(e).__name__}: {str(e)[:200]}'
    finally:
        images.get_session = original_session

    record(
        'image: 502 + "size" hatasi 1024x1024 ile tekrar denenir',
        len(image_sends) >= 2 and image_sends[-1][1].get('size') == '1024x1024',
        f'istekler = {json.dumps([s[1] for s in image_sends])[:300]} | hata = {msg[:160]}',
    )

    # ------------------------------------------------------------------
    print('\n=== 6) KASM: gercek Kasm connect URL-i guvenli kabul ediliyor ===')
    # ------------------------------------------------------------------
    real_url = (
        f'{KASM_URL}/#/connect/kasm/cdc8d55f-a57c-4262-b353-dc915f445a14/'
        'dd4798760d5549cb9aaf7bffbb49d4da/session-token-value'
    )
    record(
        'kasm: 5 parcali connect URL (kasm_id/user_id/token) guvenli',
        is_safe_kasm_connection_url(real_url, KASM_URL),
        f'url = {real_url[:110]}...',
    )
    record(
        'kasm: 4 parcali connect URL (kasm_id/token) guvenli',
        is_safe_kasm_connection_url(f'{KASM_URL}/#/connect/kasm/abc/token', KASM_URL),
        'eski bicim hala destekleniyor',
    )
    record(
        'kasm: Kasm dashboard URL-i oturum goruntusu olarak kullanilmaz',
        browser._is_kasm_dashboard_url(f'{KASM_URL}/?password=secret', KASM_URL)
        and not browser._is_kasm_dashboard_url('https://live.example.com/vnc.html', KASM_URL),
        'dashboard -> True, gercek live view -> False',
    )

    # ------------------------------------------------------------------
    print('\n=== 7) KASM: gercek sunucuda konteyner + guvenli URL ===')
    # ------------------------------------------------------------------
    try:
        patch_config(
            Config,
            {
                'browser_sandbox.enable': True,
                'browser_sandbox.provider': 'kasm',
                'browser_sandbox.kasm.url': KASM_URL,
                'browser_sandbox.kasm.api_key': KASM_API_KEY,
                'browser_sandbox.kasm.api_secret': KASM_API_SECRET,
                'browser_sandbox.kasm.user': KASM_USER,
                'browser_sandbox.kasm.password': KASM_PASSWORD,
                'browser_sandbox.kasm.browsers': ['chrome'],
                'browser_sandbox.live_url': f'{KASM_URL}/?password={KASM_PASSWORD}',
                'browser_sandbox.url': None,
                'browser_sandbox.auth_token': None,
                'browser_sandbox.kasm.cdp_url': '',
            },
        )
        result = await browser.start_browser_session(
            request=None, form_data=browser.StartSessionForm(browser_id='chrome', chat_id='live-check'), user=user
        )
        live_url = result.get('live_url') or ''
        safe = is_safe_kasm_connection_url(live_url, KASM_URL)
        record(
            'kasm: konteyner baslatildi ve connect URL guvenli',
            bool(result.get('status')) and safe,
            f"status={result.get('status')} provider={result.get('provider')} "
            f"url={live_url[:110]}... guvenli={safe}",
        )
        if result.get('status'):
            # A second start must reuse the running container instead of
            # destroying it, otherwise the embedded preview dies.
            again = await browser.start_browser_session(
                request=None, form_data=browser.StartSessionForm(browser_id='chrome', chat_id='live-check'), user=user
            )
            record(
                'kasm: ikinci istek konteyneri yok etmiyor, ayni URL-i donduruyor',
                again.get('live_url') == live_url,
                f"ilk  = {live_url[-40:]}\n       ikinci = {str(again.get('live_url'))[-40:]}",
            )
            await browser.stop_browser_session(
                request=None, form_data=browser.StopSessionForm(chat_id='live-check'), user=user
            )
    except Exception as e:
        record('kasm: konteyner baslatildi ve connect URL guvenli', False, f'{type(e).__name__}: {e}')

    print('\n' + '=' * 74)
    failed = [r for r in RESULTS if not r[1]]
    print(f'TOPLAM: {len(RESULTS)} kontrol, BASARILI: {len(RESULTS) - len(failed)}, BASARISIZ: {len(failed)}')
    for name, ok, _detail in RESULTS:
        print(f"  {'OK  ' if ok else 'HATA'}  {name}")
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
