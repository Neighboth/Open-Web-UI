"""End-to-end check of the Gemini Live path against the real gateway.

It uses the same helpers the backend uses: the connection builder, the setup
message and the translation layer.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

BACKEND = Path(r"Z:\open-web-ui\backend")
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("WEBUI_SECRET_KEY", "x-test-secret-key-for-local-verification-only-0123456789")
os.environ.setdefault("WEBUI_AUTH", "False")
os.environ.setdefault("DATABASE_URL", "sqlite:///C:/Users/simse/AppData/Local/Temp/opencode/test.db")
os.environ.setdefault("WEBUI_DIR", r"C:\Users\simse\AppData\Local\Temp\opencode\webui-test")

import aiohttp  # noqa: E402

from open_webui.routers.audio.gemini_live import build_setup, gemini_to_events  # noqa: E402
from open_webui.routers.audio.realtime import _get_realtime_connection  # noqa: E402

KEY = os.environ.get("PIX_KEY", "")
MODEL = os.environ.get("REALTIME_MODEL", "google/gemini-3.8-live")
TEMPLATE = os.environ.get(
    "GEMINI_WS_URL", "wss://pixrouter.com/v1/realtime?model={model}"
)

CONFIG = {
    "audio.realtime.provider": "gemini",
    "audio.realtime.auth_type": "api_key",
    "audio.realtime.openai.api_key": KEY,
    "audio.realtime.openai.api_base_url": "",
    "audio.realtime.model": MODEL,
    "audio.realtime.voice": "Marathon",
    "audio.realtime.transcription_model": "openai/whisper-large-v3",
    "audio.realtime.gemini.ws_url": TEMPLATE,
}


async def main():
    ws_url, headers = await _get_realtime_connection(
        CONFIG, model=MODEL, direct_key=None, direct_url=None
    )
    print("WS URL :", ws_url)
    print("Headers:", {k: (v[:12] + '...' if len(v) > 12 else v) for k, v in headers.items()})
    print()

    setup = build_setup(
        MODEL,
        CONFIG["audio.realtime.voice"],
        "You are a helpful assistant.",
        [
            {
                "type": "function",
                "name": "generate_chat_completion",
                "description": "Delegate to the chat model",
                "parameters": {"type": "object", "properties": {"request": {"type": "string"}}},
            }
        ],
    )
    print("Setup mesaji:", json.dumps(setup, ensure_ascii=False)[:220])
    print()

    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.ws_connect(ws_url, headers=headers, heartbeat=20, max_msg_size=4 * 1024 * 1024) as ws:
            await ws.send_json(setup)
            print("Setup gonderildi, yanit bekleniyor...")
            for _ in range(4):
                try:
                    message = await asyncio.wait_for(ws.receive(), timeout=30)
                except asyncio.TimeoutError:
                    print("   [zaman asimi] yanit gelmedi")
                    break
                if message.type != aiohttp.WSMsgType.TEXT:
                    print("   ", message.type)
                    break
                data = json.loads(message.data)
                print("   <<", json.dumps(data, ensure_ascii=False)[:260])
                events = gemini_to_events(data)
                for event in events:
                    print("      -> ceviri:", json.dumps(event, ensure_ascii=False)[:200])

            # Try the audio path: an empty media chunk.
            await ws.send_json(
                {"realtimeInput": {"mediaChunks": [{"mimeType": "audio/pcm;rate=16000", "data": ""}]}}
            )
            print("Bos medya parcasi gonderildi, 20s bekleniyor...")
            try:
                message = await asyncio.wait_for(ws.receive(), timeout=20)
                if message.type == aiohttp.WSMsgType.TEXT:
                    print("   <<", message.data[:300])
                else:
                    print("   ", message.type)
            except asyncio.TimeoutError:
                print("   [zaman asimi] (ses akisi icin normal olabilir)")


asyncio.run(main())
