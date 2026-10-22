"""Tests for the browser control tools.

The tools have to reach the model when the browser integration is on, and they
must stay out of the way when it is off.
"""

import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / 'backend'
sys.path.insert(0, str(BACKEND))

BROWSER_TOOLS = {
    'request_browser_session',
    'browser_view',
    'browser_screenshot',
    'browser_click',
    'browser_scroll',
    'browser_type',
    'browser_press',
    'browser_drag',
    'browser_select',
    'browser_delete',
    'browser_open',
    'browser_wait',
}


class _Request:
    class state:  # noqa: N801
        internal = False


def _patch_config():
    from open_webui.models.config import Config

    async def get_many(*keys):
        return {key: True for key in keys}

    async def get(key, default=None):
        if key in {'browser_sandbox.enable', 'image_generation.enable', 'video_generation.enable'}:
            return True
        return default

    Config.get_many = staticmethod(get_many)
    Config.get = staticmethod(get)


def _tools(features: dict) -> dict:
    from open_webui.utils.tools import get_builtin_tools

    _patch_config()
    return asyncio.run(
        get_builtin_tools(
            request=_Request(),
            extra_params={'__user__': {'id': 'u1', 'role': 'admin'}},
            features=features,
        )
    )


def test_browser_tools_are_registered_when_the_feature_is_on():
    """The model has to see the browser tools when the integration is enabled."""
    names = set(_tools({'browser': True, 'browser_id': 'chrome'}))
    missing = BROWSER_TOOLS - names
    assert not missing, f'araçlar modele ulaşmıyor: {sorted(missing)}'


def test_browser_tools_are_absent_when_the_feature_is_off():
    names = set(_tools({}))
    assert not (BROWSER_TOOLS & names), 'kapalıyken tarayıcı araçları gelmemeli'


def test_browser_tool_names_exist():
    from open_webui.tools import builtin

    for name in BROWSER_TOOLS:
        assert hasattr(builtin, name), name
