"""Smoke-test AlphaSMS Viber send (imports production helper).

Usage (from project root):
  python -m tests.test_alphasms_hello +380501234567
  python -m tests.test_alphasms_hello +380501234567 "Привіт з тесту"
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running as script: python tests/test_alphasms_hello.py ...
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.alphasms import send_viber_text
from app.config import load_settings


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m tests.test_alphasms_hello <+380...> [text]")
        sys.exit(1)

    phone = sys.argv[1].strip()
    text = sys.argv[2].strip() if len(sys.argv) > 2 else "Привіт"

    settings = load_settings()
    if not settings.alphasms_api_key or not settings.alphasms_viber_signature:
        print("Missing ALPHASMS_API_KEY or ALPHASMS_VIBER_SIGNATURE in .env")
        sys.exit(1)

    print(f"Sending to {phone!r}: {text!r}")
    result = await send_viber_text(
        api_key=settings.alphasms_api_key,
        viber_signature=settings.alphasms_viber_signature,
        phone=phone,
        text=text,
    )
    print("ok=", result.ok)
    print("error=", result.error)
    print("provider_response=", result.provider_response)
    sys.exit(0 if result.ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
