"""Regression tests for the Kasm preview fallback.

A failed container start used to fall back to the configured Kasm URL.  When
that URL is the Kasm dashboard, the embedded preview showed the dashboard plus
a login toast, which is what the "iframe opens and then errors" report was
about.  The dashboard must never be returned as a browser session view.
"""

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / 'backend'
sys.path.insert(0, str(BACKEND))

from open_webui.routers import browser  # noqa: E402

KASM = 'https://kasm.example.test:8443'


def test_kasm_root_is_a_dashboard():
    assert browser._is_kasm_dashboard_url(KASM, KASM)
    assert browser._is_kasm_dashboard_url(f'{KASM}/', KASM)
    assert browser._is_kasm_dashboard_url(f'{KASM}/?password=secret', KASM)


def test_real_session_urls_are_not_a_dashboard():
    session = f'{KASM}/#/connect/kasm/kasm-id/user-id/token'
    assert not browser._is_kasm_dashboard_url(session, KASM)
    assert not browser._is_kasm_dashboard_url(f'{KASM}/guacamole', KASM)
    assert not browser._is_kasm_dashboard_url('https://live.example.test/vnc.html', KASM)


def test_empty_url_counts_as_dashboard():
    assert browser._is_kasm_dashboard_url('', KASM)


class _User:
    id = '00000000-0000-4000-8000-000000000000'
    role = 'admin'
    settings: dict = {}
    email = 'admin@example.test'
    name = 'Admin'


def test_network_failure_does_not_return_the_dashboard():
    """The Kasm server being unreachable must surface as an error."""
    import aiohttp

    config = {
        'browser_sandbox.enable': True,
        'browser_sandbox.provider': 'kasm',
        'browser_sandbox.kasm.url': KASM,
        'browser_sandbox.kasm.api_key': 'key',
        'browser_sandbox.kasm.api_secret': 'secret',
        'browser_sandbox.kasm.user': 'user@example.test',
        'browser_sandbox.kasm.password': 'password',
        'browser_sandbox.kasm.browsers': ['chrome'],
        'browser_sandbox.kasm.cdp_url': '',
        'browser_sandbox.live_url': f'{KASM}/?password=password',
        'browser_sandbox.url': None,
        'browser_sandbox.auth_token': None,
    }

    async def get_many(*keys):
        return {k: config.get(k) for k in keys}

    async def get(key, default=None):
        return config.get(key, default)

    browser.Config.get_many = staticmethod(get_many)
    browser.Config.get = staticmethod(get)

    original_session = aiohttp.ClientSession

    class Failing:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def post(self, *a, **k):
            raise OSError('Kasm server unreachable')

    aiohttp.ClientSession = Failing
    try:
        result = asyncio.run(
            browser.start_browser_session(
                request=None,
                form_data=browser.StartSessionForm(browser_id='chrome', chat_id='test-chat'),
                user=_User(),
            )
        )
    finally:
        aiohttp.ClientSession = original_session

    assert result.get('status') is False, result
    assert result.get('live_url') is None, result
    assert 'Kasm' in str(result.get('error')), result
