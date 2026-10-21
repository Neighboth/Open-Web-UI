"""Live Kasm verification: does the preview really work, and does the retry
survive a hiccup of the Kasm server?"""

import asyncio
import json
import os
import ssl
import sys
import urllib.request
import urllib.error
from pathlib import Path

BACKEND = Path(r"Z:\open-web-ui\backend")
sys.path.insert(0, str(BACKEND))

KASM = os.environ.get("KASM_URL", "https://kasm.example.test:8443")
API_KEY = os.environ.get("KASM_API_KEY", "")
API_SECRET = os.environ.get("KASM_API_SECRET", "")
KASM_USER = os.environ.get("KASM_USER", "")
KASM_PASSWORD = os.environ.get("KASM_PASSWORD", "")
KASM_USER_ID = os.environ.get("KASM_USER_ID", "kasm-user-id")

RESULTS = []


def record(name, ok, detail):
    RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}\n       {detail}")


def post(path, payload, timeout=60):
    req = urllib.request.Request(
        f"{KASM}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return None, f"EXC {type(e).__name__}: {e}"


CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def http_get(path, timeout=60):
    req = urllib.request.Request(f"{KASM}{path}", headers={"Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)


os.environ.setdefault("WEBUI_SECRET_KEY", "x-test-secret-key-for-local-verification-only-0123456789")
os.environ.setdefault("WEBUI_AUTH", "False")
os.environ.setdefault("DATABASE_URL", "sqlite:///C:/Users/simse/AppData/Local/Temp/opencode/test.db")
os.environ.setdefault("WEBUI_DIR", r"C:\Users\simse\AppData\Local\Temp\opencode\webui-test")

from open_webui.models.config import Config  # noqa: E402
from open_webui.routers import browser  # noqa: E402

CONFIG = {
    "browser_sandbox.enable": True,
    "browser_sandbox.provider": "kasm",
    "browser_sandbox.kasm.url": KASM,
    "browser_sandbox.kasm.api_key": API_KEY,
    "browser_sandbox.kasm.api_secret": API_SECRET,
    "browser_sandbox.kasm.user": KASM_USER,
    "browser_sandbox.kasm.password": KASM_PASSWORD,
    "browser_sandbox.kasm.browsers": ["chrome"],
    "browser_sandbox.kasm.cdp_url": "",
    "browser_sandbox.kasm.enable_sharing": False,
    "browser_sandbox.live_url": f"{KASM}/?password={KASM_PASSWORD}",
    "browser_sandbox.url": None,
    "browser_sandbox.auth_token": None,
}


async def get_many(*keys):
    return {k: CONFIG.get(k) for k in keys}


async def get(key, default=None):
    return CONFIG.get(key, default)


Config.get_many = staticmethod(get_many)
Config.get = staticmethod(get)


class Ordinary:
    id = "5f9611ee-68d4-4dfd-8d8f-8cfeb391bbca"
    role = "user"
    settings: dict = {}
    email = "user@example.test"
    name = "Ordinary"


def cleanup(kasm_id):
    if not kasm_id:
        return
    kid = str(kasm_id).replace("-", "")
    st, _ = post(
        "/api/public/destroy_kasm",
        {
            "kasm_id": kid,
            "user_id": KASM_USER_ID,
            "api_key": API_KEY,
            "api_key_secret": API_SECRET,
        },
    )
    print(f"       (konteyner {kid[:12]} temizlendi: {st})")


async def main():
    print("=" * 78)
    print("1) SIRADAN kullanici (hesap istemeden) tarayici acabiliyor mu?")
    print("=" * 78)
    res = await browser.start_browser_session(
        request=None,
        form_data=browser.StartSessionForm(browser_id="chrome", chat_id="live-user"),
        user=Ordinary(),
    )
    live_url = res.get("live_url") or ""
    print(f"       status={res.get('status')} provider={res.get('provider')}")
    print(f"       live_url={live_url[:110]}...")
    record(
        "kasm: hesap istemeden tarayici acilir (paylasilan hesap)",
        bool(res.get("status")) and bool(live_url),
        f"status={res.get('status')} error={str(res.get('error'))[:160]}",
    )
    if not res.get("status"):
        return

    kasm_id = live_url.split("#/connect/kasm/")[1].split("/")[0] if "#/connect/kasm/" in live_url else None

    st, d = post(
        "/api/public/get_kasm_status",
        {
            "kasm_id": kasm_id,
            "user_id": KASM_USER_ID,
            "api_key": API_KEY,
            "api_key_secret": API_SECRET,
        },
    )
    record(
        "kasm: konteyner gercekten calisiyor (get_kasm_status)",
        st == 200,
        f"HTTP {st}",
    )

    st, d = post("/api/public/get_kasms", {"api_key": API_KEY, "api_key_secret": API_SECRET})
    running = []
    if isinstance(d, dict):
        for k in d.get("kasms", []):
            if (k.get("kasm_id") or "").replace("-", "") == str(kasm_id).replace("-", ""):
                running.append(k)
    record(
        "kasm: paylasim linki kapali (share_id yok)",
        bool(running) and not running[0].get("share_id"),
        f"share_id={running[0].get('share_id') if running else 'yok'}",
    )

    st, body = http_get("/")
    record(
        "kasm: SPA sayfasi iframe icin yukleniyor",
        st == 200,
        f"HTTP {st}, HTML {len(body)} bayt",
    )

    print()
    print("=" * 78)
    print("2) Katlanarak sessiz yeniden deneme (1s, 2s, 4s, 8s)")
    print("=" * 78)
    calls = []
    delays = []

    async def fake_sleep(delay):
        delays.append(delay)

    real_sleep = asyncio.sleep
    asyncio.sleep = fake_sleep

    async def failing():
        calls.append(1)
        raise browser.KasmError("server unreachable")

    try:
        await browser.kasm_retry(failing, attempts=5, base_delay=1.0)
    except browser.KasmError:
        pass
    finally:
        asyncio.sleep = real_sleep

    record(
        "kasm: 5 kez denenir, aralar 1s/2s/4s/8s",
        len(calls) == 5 and delays == [1.0, 2.0, 4.0, 8.0],
        f"deneme={len(calls)} bekleme={delays}",
    )

    cleanup(kasm_id)

    print()
    print("=" * 78)
    failed = [r for r in RESULTS if not r[1]]
    print(f"TOPLAM: {len(RESULTS)} kontrol, BASARILI: {len(RESULTS) - len(failed)}, BASARISIZ: {len(failed)}")
    for name, ok in RESULTS:
        print(f"  {'OK  ' if ok else 'HATA'}  {name}")


asyncio.run(main())
