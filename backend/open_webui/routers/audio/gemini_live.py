"""Translation between the Gemini Live API and the bridge event vocabulary.

The browser side of the call bridge speaks an OpenAI Realtime shaped protocol
(``input_audio_buffer.append``, ``response.output_audio.delta``,
``conversation.item.create`` and so on).  The Gemini Live API speaks a different
wire format (``realtimeInput``/``serverContent``/``toolCall``), so the two are
translated here instead of teaching the frontend a second protocol.
"""

import base64
from typing import Any

from open_webui.utils.json_codec import JSONCodec

# The Gemini Live WebSocket endpoint of the public API.  A gateway can expose
# the same service under a different path; the Admin can then point
# audio.realtime.gemini.ws_url at it.
GEMINI_LIVE_PATH = '/v1beta/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent'

# Prebuilt Gemini voices.  The Admin setting keeps its OpenAI voice name and it
# is mapped onto one of these.
GEMINI_VOICES = ('Puck', 'Charon', 'Kore', 'Fenrir', 'Aoede', 'Leda', 'Orus', 'Zephyr')

OPENAI_TO_GEMINI_VOICE = {
    'alloy': 'Aoede',
    'ash': 'Aoede',
    'ballad': 'Leda',
    'coral': 'Leda',
    'echo': 'Charon',
    'fable': 'Fenrir',
    'onyx': 'Kore',
    'nova': 'Leda',
    'sage': 'Orus',
    'shimmer': 'Orus',
    'verse': 'Zephyr',
    'marathon': 'Puck',
}

# The bridge records microphone audio at 24 kHz, the Gemini Live API expects
# 16 kHz mono PCM16.
BRIDGE_INPUT_RATE = 24000
GEMINI_INPUT_RATE = 16000


def resolve_gemini_voice(voice: str | None, default: str = 'Puck') -> str:
    """Map a configured voice name onto a Gemini prebuilt voice."""
    text = (voice or '').strip()
    if not text:
        return default
    for name in GEMINI_VOICES:
        if text.lower() == name.lower():
            return name
    key = text.lower().replace('-', '').replace('_', '').replace(' ', '')
    return OPENAI_TO_GEMINI_VOICE.get(key, default)


def gemini_model_name(model: str) -> str:
    """Turn a routed model id into the name the Gemini API expects."""
    name = (model or '').strip().split('/')[-1]
    if name.startswith('models/'):
        name = name[len('models/') :]
    return name


def resample_pcm16_24k_to_16k(pcm: bytes) -> bytes:
    """Resample mono 16 bit PCM from 24 kHz down to 16 kHz.

    The ratio is exactly 2:3, so two of every three samples are kept.  The
    result is a tenth of a millisecond shorter than the input, which the model
    does not notice.
    """
    samples = len(pcm) // 2
    if samples < 3:
        return pcm
    out = bytearray()
    for index in range(0, samples - 2, 3):
        out += pcm[index * 2 : index * 2 + 4]
    return bytes(out)


def build_setup(
    model: str,
    voice: str,
    instructions: str,
    tools: list[dict] | None = None,
    *,
    transcription_model: str | None = None,
) -> dict:
    """Build the Gemini Live setup message."""
    setup: dict[str, Any] = {
        'model': f'models/{gemini_model_name(model)}',
        'generation_config': {
            'response_modalities': ['AUDIO'],
            'speech_config': {
                'voice_config': {
                    'prebuilt_voice_config': {'voice_name': resolve_gemini_voice(voice)},
                }
            },
        },
        'system_instruction': {'parts': [{'text': instructions}]},
        # Transcripts are requested from the model itself; Gemini does not take
        # a transcription model id the way the OpenAI Realtime API does.
        'input_audio_transcription': {},
        'output_audio_transcription': {},
    }

    declarations = []
    for tool in tools or []:
        if tool.get('type') not in (None, 'function'):
            continue
        name = tool.get('name')
        if not name:
            continue
        declarations.append(
            {
                'name': name,
                'description': tool.get('description', ''),
                'parameters': tool.get('parameters') or {'type': 'object', 'properties': {}},
            }
        )
    if declarations:
        setup['tools'] = [{'function_declarations': declarations}]
    return {'setup': setup}


def command_to_gemini(command: dict) -> list[dict]:
    """Translate one bridge command into Gemini Live messages."""
    kind = command.get('type')

    if kind == 'input_audio_buffer.append':
        pcm = base64.b64decode(command['audio'], validate=True)
        pcm = resample_pcm16_24k_to_16k(pcm)
        return [
            {
                'realtimeInput': {
                    'mediaChunks': [
                        {
                            'mimeType': f'audio/pcm;rate={GEMINI_INPUT_RATE}',
                            'data': base64.b64encode(pcm).decode(),
                        }
                    ]
                }
            }
        ]

    if kind == 'conversation.item.create':
        item = command.get('item') or {}
        item_type = item.get('type')
        if item_type == 'message':
            parts = [
                {'text': content.get('text', '')}
                for content in item.get('content') or []
                if content.get('type') in {'input_text', 'text'} and content.get('text')
            ]
            if not parts:
                return []
            return [
                {
                    'clientContent': {
                        'turns': [{'role': 'user', 'parts': parts}],
                        'turnComplete': True,
                    }
                }
            ]
        if item_type == 'function_call_output':
            output = item.get('output')
            if isinstance(output, str):
                try:
                    output = JSONCodec.loads(output)
                except Exception:
                    output = {'result': output}
            if not isinstance(output, dict):
                output = {'result': output}
            return [
                {
                    'toolResponse': {
                        'functionResponses': [
                            {
                                'id': item.get('call_id'),
                                'response': output,
                            }
                        ]
                    }
                }
            ]
        return []

    # input_audio_buffer.commit / clear, response.cancel, response.create and
    # conversation.item.truncate have no Gemini Live equivalent: the model
    # closes the turn on its own and continues after a tool response.
    return []


def gemini_to_events(message: dict) -> list[dict]:
    """Translate a Gemini Live message into bridge events."""
    if not isinstance(message, dict):
        return []

    if 'error' in message:
        error = message.get('error')
        if isinstance(error, dict):
            text = error.get('message') or error.get('code') or 'Gemini Live error'
        else:
            text = str(error)
        return [{'type': 'error', 'error': {'message': str(text)[:400], 'code': 'provider_error'}}]

    if 'toolCall' in message:
        events = []
        for call in (message.get('toolCall') or {}).get('functionCalls') or []:
            call_id = call.get('id') or ''
            events.append(
                {
                    'type': 'response.output_item.done',
                    'response_id': call_id,
                    'item': {
                        'type': 'function_call',
                        'status': 'completed',
                        'name': call.get('name'),
                        'call_id': call_id,
                        'arguments': JSONCodec.dumps(call.get('args') or {}),
                    },
                }
            )
        return events

    content = message.get('serverContent')
    if not isinstance(content, dict):
        return []

    events: list[dict] = []
    if content.get('interrupted'):
        events.append({'type': 'input_audio_buffer.speech_started'})

    turn = content.get('modelTurn') or {}
    for part in turn.get('parts') or []:
        inline = part.get('inlineData') or part.get('inline_data')
        if inline and inline.get('data'):
            events.append(
                {
                    'type': 'response.output_audio.delta',
                    'item_id': 'gemini_response',
                    'content_index': 0,
                    'delta': inline['data'],
                }
            )
        elif part.get('text'):
            events.append(
                {
                    'type': 'response.output_audio_transcript.delta',
                    'item_id': 'gemini_response',
                    'content_index': 0,
                    'delta': part['text'],
                }
            )

    transcription = content.get('inputTranscription') or content.get('input_transcription')
    if isinstance(transcription, dict) and transcription.get('text'):
        events.append(
            {
                'type': 'conversation.item.input_audio_transcription.completed',
                'item_id': 'gemini_input',
                'transcript': transcription['text'],
            }
        )

    return events
