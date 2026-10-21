import asyncio
import os
import sys
from pathlib import Path

BACKEND = Path(r"Z:\open-web-ui\backend")
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("WEBUI_SECRET_KEY", "x-test-secret-key-for-local-verification-only-0123456789")
os.environ.setdefault("WEBUI_AUTH", "False")
os.environ.setdefault("DATABASE_URL", "sqlite:///C:/Users/simse/AppData/Local/Temp/opencode/test.db")
os.environ.setdefault("WEBUI_DIR", r"C:\Users\simse\AppData\Local\Temp\opencode\webui-test")

from open_webui.routers.browser import kasm_tls_status  # noqa: E402

print("=" * 74)
print("Kasm TLS guven kontrolu")
print("=" * 74)
for url in (
    os.environ.get("KASM_URL", ""),
    "http://38.210.77.108:8443",
    "https://example.com",
):
    if not url:
        continue
    status = kasm_tls_status(url)
    print(f"  {url}")
    print(f"     applicable={status['applicable']}  trusted={status['trusted']}")
    if status["detail"]:
        print(f"     detail: {status['detail']}")
