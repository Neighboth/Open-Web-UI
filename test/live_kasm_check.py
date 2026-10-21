"""Live Kasm verification: does the preview really work, and is the shared
account leak closed?"""

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

KASM = os.environ.get("KASM_URL", "https://38.210.77.108:8443")
API_KEY = os.environ.get("KASM_API_KEY", "")
API_SECRET = os.environ.get("KASM_API_SECRET", "")
KASM_USER = os.environ.get("KASM_USER", "")
KASM_PASSWORD = os.environ.get("KASM_PASSWORD", "")

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

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
    "browser_sandbox.allowed_roles": ["admin"],
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


class Admin:
    id = "84593fb0-1617-40ed-8bbd-4bd7a0fa0c8b"
    role = "admin"
    settings: dict = {}
    email = "admin@example.test"
    name = "Admin"


class Ordinary:
    id = "5f9611ee-68d4-4dfd-8d8f-8cfeb391bbca"
    role = "user"
    settings: dict = {}
    email = "user@example.test"
    name = "Ordinary"


class OrdinaryWithOwn:
    id = "5b97105d-18b0-45e8-a028-4aeec737e11c"
    role = "user"
    settings = {"browserSandboxKasm": {"user": KASM_USER, "password": KASM_PASSWORD}}
    email = "user2@example.test"
    name = "Ordinary2"


def cleanup(kasm_id):
    if not kasm_id:
        return
    kid = str(kasm_id).replace("-", "")
    st, d = post(
        "/api/public/destroy_kasm",
        {
            "kasm_id": kid,
            "user_id": "dd4798760d5549cb9aaf7bffbb49d4da",
            "api_key": API_KEY,
            "api_key_secret": API_SECRET,
        },
    )
    print(f"       (konteyner {kid[:12]} temizlendi: {st})")


async def main():
    print("=" * 78)
    print("1) ADMIN paylasilan hesapla oturum aciliyor mu?")
    print("=" * 78)
    res = await browser.start_browser_session(
        request=None,
        form_data=browser.StartSessionForm(browser_id="chrome", chat_id="live-admin"),
        user=Admin(),
    )
    live_url = res.get("live_url") or ""
    print(f"       status={res.get('status')} provider={res.get('provider')}")
    print(f"       live_url={live_url[:120]}...")
    if not res.get("status"):
        record("admin: paylasilan hesapla oturum acilir", False, str(res.get("error"))[:200])
        return

    kasm_id = None
    token = None
    if "#/connect/kasm/" in live_url:
        parts = live_url.split("#/connect/kasm/")[1].split("/")
        kasm_id = parts[0]
        token = parts[-1]

    # The container really is running and the session token is accepted.
    st, d = post(
        "/api/public/get_kasm_status",
        {"kasm_id": kasm_id, "user_id": "dd4798760d5549cb9aaf7bffbb49d4da", "api_key": API_KEY, "api_key_secret": API_SECRET},
    )
    status_text = json.dumps(d, ensure_ascii=False)[:220] if not isinstance(d, str) else d[:220]
    record(
        "kasm: konteyner gercekten calisiyor (get_kasm_status)",
        st == 200,
        f"HTTP {st} -> {status_text}",
    )

    st, d = post("/api/public/get_kasms", {"api_key": API_KEY, "api_key_secret": API_SECRET})
    running = []
    if isinstance(d, dict):
        for k in d.get("kasms", []):
            if (k.get("kasm_id") or "").replace("-", "") == str(kasm_id).replace("-", ""):
                running.append(k)
    record(
        "kasm: konteyner listede ve paylasim linki kapali",
        bool(running) and not running[0].get("share_id"),
        f"share_id={running[0].get('share_id') if running else 'yok'} user_id={running[0].get('user_id') if running else '-'}",
    )

    st, body = http_get("/")
    record(
        "kasm: SPA sayfasi iframe icin yukleniyor (X-Frame-Options yok)",
        st == 200 and "x-frame-options" not in body.lower(),
        f"HTTP {st}, HTML {len(body)} bayt",
    )

    cleanup(kasm_id)

    print()
    print("=" * 78)
    print("2) ADMIN OLMAYAN kullanici paylasilan hesabi kullanabiliyor mu? (olmamali)")
    print("=" * 78)
    res2 = await browser.start_browser_session(
        request=None,
        form_data=browser.StartSessionForm(browser_id="chrome", chat_id="live-user"),
        user=Ordinary(),
    )
    record(
        "kasm: siradan kullanici paylasilan hesabi kullanamaz",
        res2.get("status") is False and "shared Kasm account" in str(res2.get("error")),
        f"status={res2.get('status')} error={str(res2.get('error'))[:180]}",
    )

    print()
    print("=" * 78)
    print("3) KENDI hesabi olan siradan kullanici")
    print("=" * 78)
    res3 = await browser.start_browser_session(
        request=None,
        form_data=browser.StartSessionForm(browser_id="chrome", chat_id="live-user-own"),
        user=OrdinaryWithOwn(),
    )
    record(
        "kasm: kendi hesabi olan kullanici erisebiliyor",
        bool(res3.get("status")),
        f"status={res3.get('status')} live_url={(res3.get('live_url') or '')[:100]}",
    )
    if res3.get("live_url") and "#/connect/kasm/" in res3["live_url"]:
        cleanup(res3["live_url"].split("#/connect/kasm/")[1].split("/")[0])

    print()
    print("=" * 78)
    failed = [r for r in RESULTS if not r[1]]
    print(f"TOPLAM: {len(RESULTS)} kontrol, BASARILI: {len(RESULTS) - len(failed)}, BASARISIZ: {len(failed)}")
    for name, ok in RESULTS:
        print(f"  {'OK  ' if ok else 'HATA'}  {name}")


asyncio.run(main())
