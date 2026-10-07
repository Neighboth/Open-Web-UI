from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / 'backend' / 'open_webui' / 'utils' / 'video_defaults.py'
SPEC = spec_from_file_location('video_defaults', MODULE_PATH)
VIDEO_DEFAULTS = module_from_spec(SPEC)
SPEC.loader.exec_module(VIDEO_DEFAULTS)
filter_unrequested_video_options = VIDEO_DEFAULTS.filter_unrequested_video_options
resolve_duration = VIDEO_DEFAULTS.resolve_duration
resolve_size = VIDEO_DEFAULTS.resolve_size


def test_model_inferred_video_options_fall_back_to_admin_defaults():
    messages = [{'role': 'user', 'content': 'Create a cinematic mountain video'}]

    result = filter_unrequested_video_options(
        {'prompt': 'cinematic mountain video', 'size': '1080P', 'duration': 8},
        messages,
    )

    assert result == {'prompt': 'cinematic mountain video'}
    assert resolve_size(result.get('size'), '720P', '1024x1024') == '720P'
    assert resolve_duration(result.get('duration'), '12') == 12


def test_explicit_video_options_are_preserved():
    messages = [{'role': 'user', 'content': 'Make it 1080P and 8 seconds long'}]

    result = filter_unrequested_video_options(
        {'prompt': 'mountain video', 'size': '1080P', 'duration': 8},
        messages,
    )

    assert result['size'] == '1080P'
    assert result['duration'] == 8


def test_natural_duration_variants_are_recognized():
    for text in ('Make an 8-second clip', 'Create an 8-second-long clip', 'duration of 8'):
        messages = [{'role': 'user', 'content': text}]
        result = filter_unrequested_video_options({'duration': 8}, messages)
        assert result['duration'] == 8


def test_empty_and_invalid_values_use_configured_defaults():
    assert resolve_size('', '720P', '1024x1024') == '720P'
    assert resolve_size(None, '', '1024x1024') == '1024x1024'
    assert resolve_duration('', '12') == 12
    assert resolve_duration(0, '12') == '12'
    assert resolve_duration(-1, 12) == 12
