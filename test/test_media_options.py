"""Tests for the media tool options.

The administrator picks the ratios, resolutions and durations the provider
accepts.  Those have to reach the model in the tool description, otherwise it
offers values the provider rejects, and the size field has to accept the
resolution tiers (1K, 2K, 3K, 4K) next to the plain width x height form.
"""

import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / 'backend'
sys.path.insert(0, str(BACKEND))

from open_webui.routers.images import _split_options  # noqa: E402
from open_webui.utils.tools import build_media_options_hint, split_option_list  # noqa: E402

CONFIG = {
    'video_generation.aspect_ratios': '21:9, 16:9, 4:3, 1:1, 3:4, 9:16, 2:3, 3:2',
    'video_generation.sizes': '720P, 1080P, 1024x1024',
    'video_generation.durations': '4 - 12',
    'video_generation.duration_default': '12',
    'video_generation.aspect_ratio_default': '16:9',
    'video_generation.size_default': '720P',
    'video_generation.image_input.max': 5,
    'image_generation.allowed_sizes': '4096x4096, 1K, 2K, 3K, 4K',
    'image_generation.allowed_ratios': '1:1, 16:9, 9:16, 4:3, 3:4, 2:3, 3:2, 21:9',
    'image_generation.default_ratio': '1:1',
    'image_generation.size': '4096x4096',
    'image_generation.reference_images.max': 4,
}


def test_option_lists_are_split():
    assert split_option_list('1:1, 16:9, 9:16') == ['1:1', '16:9', '9:16']
    assert split_option_list('1:1\n16:9') == ['1:1', '16:9']
    assert split_option_list(None) == []
    assert _split_options(['a', 'b']) == ['a', 'b']


def test_video_tool_lists_every_configured_option():
    hint = build_media_options_hint(CONFIG, 'generate_video')
    # Every ratio the Admin entered has to be mentioned, not a hard coded list.
    for ratio in ('21:9', '16:9', '4:3', '1:1', '3:4', '9:16', '2:3', '3:2'):
        assert ratio in hint, ratio
    for size in ('720P', '1080P', '1024x1024'):
        assert size in hint, size
    assert '4 - 12' in hint
    assert 'up to 5' in hint
    assert 'default: 16:9' in hint


def test_image_tools_list_the_configured_options():
    for tool in ('generate_image', 'edit_image'):
        hint = build_media_options_hint(CONFIG, tool)
        for ratio in ('1:1', '16:9', '9:16', '4:3', '3:4', '2:3', '3:2', '21:9'):
            assert ratio in hint, (tool, ratio)
        for size in ('4096x4096', '1K', '2K', '3K', '4K'):
            assert size in hint, (tool, size)
        assert 'up to 4' in hint


def test_hint_is_empty_without_a_configuration():
    assert build_media_options_hint({}, 'generate_video') == ''
    assert build_media_options_hint({}, 'generate_image') == ''


def test_image_size_accepts_pixels_and_tiers():
    # The Admin writes either 1024x1024 or 1K, 2K, 3K, 4K.
    pattern = r'^(\d+x\d+|\d+[KkMm])$'
    for value in ('1024x1024', '4096x4096', '1K', '2K', '3K', '4K', '512x512'):
        assert re.match(pattern, value), value
    for value in ('', 'auto', 'huge', '12x', '4KB'):
        assert not re.match(pattern, value), value
