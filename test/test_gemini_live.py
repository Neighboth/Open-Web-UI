"""Tests for the Gemini Live translation layer.

The browser side of the call bridge speaks an OpenAI Realtime shaped protocol.
The Gemini Live API speaks its own format, so both directions are translated
in open_webui.routers.audio.gemini_live.
"""

import base64
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / 'backend'
sys.path.insert(0, str(BACKEND))

from open_webui.routers.audio.gemini_live import (  # noqa: E402
    build_setup,
    command_to_gemini,
    gemini_model_name,
    gemini_to_events,
    resample_pcm16_24k_to_16k,
    resolve_gemini_voice,
)


def test_voice_mapping():
    assert resolve_gemini_voice('Puck') == 'Puck'
    assert resolve_gemini_voice('puck') == 'Puck'
    # The Admin setting uses an OpenAI voice name; it is mapped onto Gemini.
    assert resolve_gemini_voice('Marathon') == 'Puck'
    assert resolve_gemini_voice('alloy') == 'Aoede'
    assert resolve_gemini_voice('echo') == 'Charon'
    assert resolve_gemini_voice('') == 'Puck'
    assert resolve_gemini_voice(None) == 'Puck'


def test_model_name_strips_the_route_prefix():
    assert gemini_model_name('google/gemini-3.8-live') == 'gemini-3.8-live'
    assert gemini_model_name('gemini-3.8-live') == 'gemini-3.8-live'
    assert gemini_model_name('models/gemini-3.8-live') == 'gemini-3.8-live'


def test_resample_24k_to_16k():
    # 24 kHz PCM16 -> 16 kHz keeps two of every three samples.
    pcm = b''.join(int(i).to_bytes(2, 'little', signed=True) for i in range(30))
    out = resample_pcm16_24k_to_16k(pcm)
    assert len(out) == 20 * 2
    # The first two samples are kept, the third is dropped.
    assert out[:4] == pcm[:4]
    assert out[4:6] == pcm[6:8]


def test_setup_message():
    setup = build_setup(
        'google/gemini-3.8-live',
        'Marathon',
        'You are helpful.',
        [
            {
                'type': 'function',
                'name': 'generate_chat_completion',
                'description': 'Delegate to the chat model',
                'parameters': {'type': 'object', 'properties': {'request': {'type': 'string'}}},
            }
        ],
    )['setup']
    assert setup['model'] == 'models/gemini-3.8-live'
    assert setup['generation_config']['response_modalities'] == ['AUDIO']
    assert setup['generation_config']['speech_config']['voice_config']['prebuilt_voice_config']['voice_name'] == 'Puck'
    assert setup['system_instruction']['parts'][0]['text'] == 'You are helpful.'
    assert setup['tools'][0]['function_declarations'][0]['name'] == 'generate_chat_completion'
    assert 'input_audio_transcription' in setup
    assert 'output_audio_transcription' in setup


def test_audio_command_is_resampled_and_wrapped():
    pcm = b''.join(int(i).to_bytes(2, 'little', signed=True) for i in range(30))
    command = {'type': 'input_audio_buffer.append', 'audio': base64.b64encode(pcm).decode()}
    messages = command_to_gemini(command)
    assert len(messages) == 1
    chunk = messages[0]['realtimeInput']['mediaChunks'][0]
    assert chunk['mimeType'] == 'audio/pcm;rate=16000'
    assert len(base64.b64decode(chunk['data'])) == 20 * 2


def test_text_message_becomes_a_client_turn():
    command = {
        'type': 'conversation.item.create',
        'item': {
            'id': 'x',
            'type': 'message',
            'role': 'system',
            'content': [{'type': 'input_text', 'text': 'hello there'}],
        },
    }
    messages = command_to_gemini(command)
    assert messages == [
        {'clientContent': {'turns': [{'role': 'user', 'parts': [{'text': 'hello there'}]}], 'turnComplete': True}}
    ]


def test_function_output_becomes_a_tool_response():
    command = {
        'type': 'conversation.item.create',
        'item': {
            'type': 'function_call_output',
            'call_id': 'call-1',
            'output': '{"status": "completed", "answer": "42"}',
        },
    }
    messages = command_to_gemini(command)
    assert messages == [
        {
            'toolResponse': {
                'functionResponses': [
                    {'id': 'call-1', 'response': {'status': 'completed', 'answer': '42'}}
                ]
            }
        }
    ]


def test_commands_without_a_gemini_equivalent_are_dropped():
    assert command_to_gemini({'type': 'input_audio_buffer.commit'}) == []
    assert command_to_gemini({'type': 'input_audio_buffer.clear'}) == []
    assert command_to_gemini({'type': 'response.cancel', 'response_id': 'r'}) == []
    assert command_to_gemini({'type': 'response.create', 'response': {}}) == []


def test_model_audio_becomes_an_audio_delta():
    events = gemini_to_events(
        {
            'serverContent': {
                'modelTurn': {
                    'parts': [
                        {'inlineData': {'mimeType': 'audio/pcm;rate=24000', 'data': 'QUJD'}},
                        {'text': 'hello'},
                    ]
                }
            }
        }
    )
    kinds = [e['type'] for e in events]
    assert 'response.output_audio.delta' in kinds
    assert 'response.output_audio_transcript.delta' in kinds
    audio = next(e for e in events if e['type'] == 'response.output_audio.delta')
    assert audio['delta'] == 'QUJD'
    text = next(e for e in events if e['type'] == 'response.output_audio_transcript.delta')
    assert text['delta'] == 'hello'


def test_input_transcription_and_interruption():
    events = gemini_to_events(
        {
            'serverContent': {
                'interrupted': True,
                'inputTranscription': {'text': 'merhaba'},
            }
        }
    )
    kinds = [e['type'] for e in events]
    assert 'input_audio_buffer.speech_started' in kinds
    assert 'conversation.item.input_audio_transcription.completed' in kinds
    transcript = next(e for e in events if e['type'].endswith('transcription.completed'))
    assert transcript['transcript'] == 'merhaba'


def test_tool_call_becomes_a_function_call_item():
    events = gemini_to_events(
        {
            'toolCall': {
                'functionCalls': [
                    {'id': 'call-9', 'name': 'generate_chat_completion', 'args': {'request': 'hi'}}
                ]
            }
        }
    )
    assert len(events) == 1
    event = events[0]
    assert event['type'] == 'response.output_item.done'
    assert event['item']['type'] == 'function_call'
    assert event['item']['call_id'] == 'call-9'
    assert event['item']['name'] == 'generate_chat_completion'
    assert event['item']['status'] == 'completed'


def test_error_message_is_forwarded():
    events = gemini_to_events({'error': {'message': 'model not found', 'code': 404}})
    assert events[0]['type'] == 'error'
    assert 'model not found' in events[0]['error']['message']
