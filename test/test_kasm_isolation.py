"""Regression tests for the Kasm account isolation.

The browser sandbox used one Kasm account for the whole instance, so any user
who opened a browser session received a session token minted for the Admin's
Kasm account.  Now a user may bring their own Kasm account, and the shared
account is limited to the roles the Admin allows.
"""

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / 'backend'
sys.path.insert(0, str(BACKEND))

from open_webui.routers import browser  # noqa: E402
from open_webui.utils.browser_session import get_user_kasm_credentials  # noqa: E402

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
    'browser_sandbox.allowed_roles': ['admin'],
    'browser_sandbox.live_url': f'{KASM}/?password=shared-password',
    'browser_sandbox.url': None,
    'browser_sandbox.auth_token': None,
}


class _User:
    def __init__(self, role='user', settings=None):
        self.id = '11111111-1111-4111-8111-111111111111'
        self.role = role
        self.settings = settings or {}
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
            return '{}'

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


def test_user_kasm_credentials_are_read_from_the_settings():
    assert get_user_kasm_credentials(_User(settings={'browserSandboxKasm': {'user': 'u', 'password': 'p'}})) == (
        'u',
        'p',
    )
    assert get_user_kasm_credentials(
        _User(settings={'ui': {'browserSandboxKasm': {'user': 'u', 'password': 'p'}}})
    ) == ('u', 'p')
    assert get_user_kasm_credentials(_User(settings={})) == (None, None)
    assert get_user_kasm_credentials(_User(settings={'browserSandboxKasm': {'user': 'u'}})) == (None, None)
    assert get_user_kasm_credentials(None) == (None, None)


def test_shared_account_is_restricted_to_the_allowed_roles():
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

    assert result.get('status') is False, result
    assert 'shared Kasm account' in str(result.get('error')), result


def test_own_kasm_account_bypasses_the_role_restriction():
    _patch_config(dict(CONFIG))
    original = _patch_session()
    try:
        result = asyncio.run(
            browser.start_browser_session(
                request=None,
                form_data=browser.StartSessionForm(browser_id='chrome', chat_id='c2'),
                user=_User(role='user', settings={'browserSandboxKasm': {'user': 'mine', 'password': 'secret'}}),
            )
        )
    finally:
        import aiohttp

        aiohttp.ClientSession = original

    assert result.get('status') is True, result
    assert result.get('live_url'), result


def test_admin_may_use_the_shared_account():
    _patch_config(dict(CONFIG))
    original = _patch_session()
    try:
        result = asyncio.run(
            browser.start_browser_session(
                request=None,
                form_data=browser.StartSessionForm(browser_id='chrome', chat_id='c3'),
                user=_User(role='admin'),
            )
        )
    finally:
        import aiohttp

        aiohttp.ClientSession = original

    assert result.get('status') is True, result
