"""Regression tests for the video generation request builder.

The Admin can configure extra provider parameters (for example
``{"mode": "text"}``) and a request mode.  Both settings were missing from
``VIDEO_CONFIG_KEYS``, so they were never read and the provider answered
"mode is required" for every request.
"""

import asyncio
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / 'backend'
sys.path.insert(0, str(BACKEND))

from open_webui.routers import videos  # noqa: E402


def test_admin_params_and_mode_are_read_from_the_config():
    assert videos.VIDEO_CONFIG_KEYS['VIDEOS_OPENAI_API_PARAMS'] == 'video_generation.openai.params'
    assert videos.VIDEO_CONFIG_KEYS['VIDEO_GENERATION_MODE'] == 'video_generation.mode'
    assert videos.DEFAULT_CONFIG['VIDEOS_OPENAI_API_PARAMS'] == {}
    assert videos.DEFAULT_CONFIG['VIDEO_GENERATION_MODE'] == ''


class _Resp:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def text(self):
        return self._body

    async def json(self, **k):
        return {}


class _Session:
    def __init__(self, status, body, sink):
        self._status = status
        self._body = body
        self._sink = sink

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    def post(self, url, **kwargs):
        if kwargs.get('json') is not None:
            # Copy: the router mutates the same dict between retries.
            self._sink.append(dict(kwargs['json']))
        return _Resp(self._status, self._body)


def _patch(sink, status, body):
    import aiohttp

    original = aiohttp.ClientSession

    class Fake:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def post(self, url, **kwargs):
            return _Session(status, body, sink).post(url, **kwargs)

    aiohttp.ClientSession = Fake
    return original


def _config(values):
    async def get_many(*keys):
        return {k: values.get(k) for k in keys}

    async def get(key, default=None):
        return values.get(key, default)

    videos.Config.get_many = staticmethod(get_many)
    videos.Config.get = staticmethod(get)


BASE_CONFIG = {
    # The Config store is keyed by the storage key, not by the field name.
    'video_generation.enable': True,
    'video_generation.engine': 'openai',
    'video_generation.model': 'agnes/agnes-video-2.5-flash',
    'video_generation.size': '720P',
    'video_generation.openai.api_base_url': 'https://provider.example.test/v1',
    'video_generation.openai.api_key': 'test-key',
    'video_generation.openai.params': {'mode': 'text'},
    'video_generation.mode': '',
    'video_generation.size_default': '720P',
    'video_generation.duration_default': '12',
    'video_generation.aspect_ratio_default': '16:9',
    'video_generation.image_input.max': 5,
    'video_generation.image_input.mode': 'image',
}


def _run(coro):
    return asyncio.run(coro)


def test_admin_params_reach_the_provider_payload():
    import aiohttp

    sent = []
    original = _patch(sent, 503, json.dumps({'code': 'video_queue_full', 'message': 'busy'}))
    _config(dict(BASE_CONFIG))
    try:
        _run(videos.video_generations(request=None, form_data={'prompt': 'a red cube'}, user=None))
    except Exception:
        pass
    finally:
        aiohttp.ClientSession = original

    assert sent, 'the provider was never called'
    assert sent[0]['mode'] == 'text', sent[0]


def test_admin_mode_field_reaches_the_provider_payload():
    import aiohttp

    sent = []
    original = _patch(sent, 503, json.dumps({'code': 'video_queue_full', 'message': 'busy'}))
    config = dict(BASE_CONFIG)
    config['video_generation.openai.params'] = {}
    config['video_generation.mode'] = 'text'
    _config(config)
    try:
        _run(videos.video_generations(request=None, form_data={'prompt': 'a red cube'}, user=None))
    except Exception:
        pass
    finally:
        aiohttp.ClientSession = original

    assert sent and sent[0]['mode'] == 'text', sent


def test_params_stored_as_a_json_string_are_parsed():
    import aiohttp

    sent = []
    original = _patch(sent, 503, json.dumps({'code': 'video_queue_full', 'message': 'busy'}))
    config = dict(BASE_CONFIG)
    config['video_generation.openai.params'] = '{\n  "mode": "text"\n}'
    _config(config)
    try:
        _run(videos.video_generations(request=None, form_data={'prompt': 'a red cube'}, user=None))
    except Exception:
        pass
    finally:
        aiohttp.ClientSession = original

    assert sent and sent[0]['mode'] == 'text', sent


def test_unsupported_parameter_is_dropped_and_the_request_is_retried():
    import aiohttp

    sent = []
    body = json.dumps(
        {
            'code': 'fail_to_fetch_task',
            'message': json.dumps(
                {
                    'code': 'invalid_request',
                    'message': 'duration is not an allowed request field',
                    'data': {'param': 'duration'},
                }
            ),
        }
    )
    original = _patch(sent, 400, body)
    _config(dict(BASE_CONFIG))
    try:
        _run(videos.video_generations(request=None, form_data={'prompt': 'x'}, user=None))
    except Exception:
        pass
    finally:
        aiohttp.ClientSession = original

    assert len(sent) == 2, sent
    assert 'duration' in sent[0]
    assert 'duration' not in sent[1], sent[1]


def test_required_parameter_is_not_removed():
    """A "mode is required" complaint must not delete the mode from the payload."""
    import aiohttp

    sent = []
    body = json.dumps(
        {
            'code': 'fail_to_fetch_task',
            'message': json.dumps(
                {
                    'code': 'invalid_request',
                    'message': 'mode is required (request id: test)',
                    'data': {'param': 'mode'},
                }
            ),
        }
    )
    original = _patch(sent, 400, body)
    _config(dict(BASE_CONFIG))
    error = None
    try:
        _run(videos.video_generations(request=None, form_data={'prompt': 'x'}, user=None))
    except Exception as exc:
        error = exc
    finally:
        aiohttp.ClientSession = original

    assert len(sent) == 1, sent
    assert sent[0]['mode'] == 'text', sent[0]
    assert error is not None
