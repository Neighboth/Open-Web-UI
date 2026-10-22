"""Regression tests for the Kasm browser session behaviour.

The Kasm server is often only briefly unavailable, so every API call is
retried silently with an exponential backoff.  The shared Kasm account is used
by everybody: nobody has to create an account to open a browser.
"""

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / 'backend'
sys.path.insert(0, str(BACKEND))

from open_webui.routers import browser  # noqa: E402

KASM = 'https://kasm.example.test:8443'

CONFIG = {
    'browser_sandbox.enable': True,
    'browser_sandbox.provider': 'kasm',
    'browser_sandbox.kasm.url': KASM,
    'browser_sandbox.kasm.api_key': 'key',
    'browser_sandbox.kasm.api_secret': 'secret',
    'browser_sandbox.kasm.user': 'shared-account',
    'browser_sandbox.kasm.password': 'shared-password',
    'browser_sandbox.kasm.browsers': ['chrome'],
    'browser_sandbox.kasm.cdp_url': '',
    'browser_sandbox.kasm.enable_sharing': False,
    'browser_sandbox.live_url': f'{KASM}/?password=shared-password',
    'browser_sandbox.url': None,
    'browser_sandbox.auth_token': None,
}


class _User:
    def __init__(self, role='user'):
        self.id = '11111111-1111-4111-8111-111111111111'
        self.role = role
        self.settings: dict = {}
        self.email = 'user@example.test'
        self.name = 'User'


def _patch_config(values):
    async def get_many(*keys):
        return {k: values.get(k) for k in keys}

    async def get(key, default=None):
        return values.get(key, default)

    browser.Config.get_many = staticmethod(get_many)
    browser.Config.get = staticmethod(get)


def _patch_session():
    """Replace the Kasm API calls so no container is created."""
    import aiohttp

    class Resp:
        status = 200

        def __init__(self, payload):
            self._payload = payload

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def text(self):
            import json

            return json.dumps(self._payload)

        async def json(self, **k):
            return self._payload

    class FakeSession:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def post(self, url, **kwargs):
            if 'get_images' in url:
                return Resp(
                    {
                        'images': [
                            {
                                'image_id': 'chrome-image-id',
                                'friendly_name': 'Chrome',
                                'name': 'kasmweb/chrome:1.19.0',
                            }
                        ]
                    }
                )
            if 'authenticate' in url:
                return Resp({'user_id': 'kasm-user-id'})
            return Resp(
                {
                    'kasm_id': 'kasm-id',
                    'session_token': 'token',
                    'kasm_url': f'{KASM}/#/connect/kasm/kasm-id/token',
                }
            )

    original = aiohttp.ClientSession
    aiohttp.ClientSession = FakeSession
    return original


def test_any_role_may_use_the_shared_account():
    """Nobody has to create an account to open a browser."""
    _patch_config(dict(CONFIG))
    original = _patch_session()
    try:
        result = asyncio.run(
            browser.start_browser_session(
                request=None,
                form_data=browser.StartSessionForm(browser_id='chrome', chat_id='c1'),
                user=_User(role='user'),
            )
        )
    finally:
        import aiohttp

        aiohttp.ClientSession = original

    assert result.get('status') is True, result
    assert result.get('live_url'), result


def test_kasm_post_retries_with_a_growing_delay(monkeypatch=None):
    """A failing call is repeated five times before the user hears about it."""
    calls = []
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    browser.asyncio.sleep = fake_sleep

    async def operation():
        calls.append(1)
        raise browser.KasmError('server unreachable')

    try:
        asyncio.run(browser.kasm_retry(operation, attempts=5, base_delay=1.0))
    except browser.KasmError:
        pass
    finally:
        browser.asyncio.sleep = asyncio.sleep

    assert len(calls) == 5, calls
    # 1s, 2s, 4s, 8s between the five attempts.
    assert delays == [1.0, 2.0, 4.0, 8.0], delays


def test_kasm_post_returns_the_first_success():
    calls = []

    async def operation():
        calls.append(1)
        if len(calls) < 3:
            raise browser.KasmError('not yet')
        return 'ok'

    result = asyncio.run(browser.kasm_retry(operation, attempts=5, base_delay=0))
    assert result == 'ok'
    assert len(calls) == 3, calls


def test_own_kasm_account_is_optional_and_used_when_present():
    """An administrator can keep their sessions on their own Kasm account."""
    from open_webui.utils.browser_session import get_user_kasm_credentials

    class U:
        settings = {'browserSandboxKasm': {'user': 'mine', 'password': 'secret'}}

    assert get_user_kasm_credentials(U()) == ('mine', 'secret')
    # A user without their own account falls back to the shared one.
    assert get_user_kasm_credentials(_User(role='user')) == (None, None)


def test_own_kasm_account_is_used_for_the_session():
    _patch_config(dict(CONFIG))
    original = _patch_session()
    used = {}

    import aiohttp

    class OwnResp:
        status = 200

        def __init__(self, payload):
            self._payload = payload

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def text(self):
            import json

            return json.dumps(self._payload)

        async def json(self, **k):
            return self._payload

    class Recorder:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def post(self, url, **kwargs):
            if 'authenticate' in url:
                used['username'] = (kwargs.get('json') or {}).get('username')
                return OwnResp({'user_id': 'own-user-id'})
            if 'get_images' in url:
                return OwnResp(
                    {
                        'images': [
                            {'image_id': 'chrome-image-id', 'friendly_name': 'Chrome', 'name': 'kasmweb/chrome:1.19.0'}
                        ]
                    }
                )
            return OwnResp(
                {
                    'kasm_id': 'kasm-id',
                    'session_token': 'token',
                    'kasm_url': f'{KASM}/#/connect/kasm/kasm-id/token',
                }
            )

    aiohttp.ClientSession = Recorder
    try:
        user = _User(role='admin')
        user.settings = {'browserSandboxKasm': {'user': 'own-account', 'password': 'secret'}}
        result = asyncio.run(
            browser.start_browser_session(
                request=None,
                form_data=browser.StartSessionForm(browser_id='chrome', chat_id='c-own'),
                user=user,
            )
        )
    finally:
        aiohttp.ClientSession = original

    assert result.get('status') is True, result
    assert used.get('username') == 'own-account', used


def test_tls_status_flags_an_untrusted_certificate():
    """A frame with an untrusted certificate is blocked by the browser."""
    import socket
    import ssl

    from open_webui.routers import browser as browser_module

    class FakeContext:
        def __init__(self, *a, **k):
            pass

        def wrap_socket(self, sock, **kwargs):
            raise ssl.SSLCertVerificationError(1, '[X509: NO_CERTIFICATE_OR_CRL_FOUND]')

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    original_context = ssl.create_default_context
    original_socket = socket.create_connection
    ssl.create_default_context = lambda *a, **k: FakeContext()
    socket.create_connection = lambda *a, **k: FakeSocket()
    browser_module._KASM_TLS_CACHE.clear()
    try:
        status = browser_module.kasm_tls_status('https://kasm.example.test:8443')
    finally:
        ssl.create_default_context = original_context
        socket.create_connection = original_socket
        browser_module._KASM_TLS_CACHE.clear()

    assert status['applicable'] is True
    assert status['trusted'] is False
    assert status['detail']


def test_tls_status_ignores_plain_http():
    from open_webui.routers import browser as browser_module

    status = browser_module.kasm_tls_status('http://kasm.example.test:8443')
    assert status['applicable'] is False
    assert status['trusted'] is True
