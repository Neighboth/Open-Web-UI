"""Tests for the browser control helpers.

The DevTools protocol client itself needs a real browser, but the pieces that
decide *what* to do - the page snapshot script, the click/select/find
scripts, the key table and the URL handling - are plain data and can be
checked directly.
"""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / 'backend'
sys.path.insert(0, str(BACKEND))

from open_webui.utils.browser_cdp import (  # noqa: E402
    KEY_SPECS,
    PAGE_SNAPSHOT_SCRIPT,
    build_click_script,
    build_find_script,
    build_select_script,
    is_http_url,
    normalize_url,
)


def test_snapshot_script_collects_text_and_elements():
    script = PAGE_SNAPSHOT_SCRIPT
    assert 'innerText' in script
    assert 'interactive' in script
    assert 'getBoundingClientRect' in script
    # The model needs the position of an element to be able to aim at it.
    assert 'x:' in script and 'y:' in script


def test_click_script_searches_by_text():
    script = build_click_script('Submit')
    assert '"Submit"' in script
    assert 'getBoundingClientRect' in script
    assert 'found' in script


def test_click_script_escapes_quotes():
    script = build_click_script('Say "hi"')
    assert '\\"hi\\"' in script


def test_select_script_picks_an_option():
    script = build_select_script('Germany')
    assert '"Germany"' in script
    assert "new Event('change'" in script


def test_find_script_scrolls_into_view():
    script = build_find_script('Total')
    assert '"Total"' in script
    assert 'scrollIntoView' in script


def test_key_table_covers_the_usual_keys():
    for key in ('enter', 'tab', 'escape', 'backspace', 'delete', 'space', 'arrowdown', 'ctrl+a'):
        assert key in KEY_SPECS, key
    assert KEY_SPECS['enter']['vk'] == 13
    assert KEY_SPECS['backspace']['vk'] == 8
    assert KEY_SPECS['delete']['vk'] == 46


def test_url_normalisation():
    assert normalize_url('https://example.com/a/b', '/c') == 'https://example.com/c'
    assert normalize_url('https://example.com/a/b', 'https://other.com/x') == 'https://other.com/x'
    assert normalize_url('', 'https://x.com') == 'https://x.com'
    assert is_http_url('https://x.com') is True
    assert is_http_url('javascript:alert(1)') is False
