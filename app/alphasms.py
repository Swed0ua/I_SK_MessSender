from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any

import httpx

from app.sender import SendResult
from app.templates import render_template

logger = logging.getLogger(__name__)

ALPHASMS_API_URL = "https://alphasms.ua/api/json.php"


def _phone_int(phone: str) -> int:
    digits = "".join(ch for ch in phone if ch.isdigit())
    return int(digits)


async def send_viber_text(
    *,
    api_key: str,
    viber_signature: str,
    phone: str,
    text: str,
) -> SendResult:
    """Send plain Viber text via AlphaSMS API."""
    msg_id = datetime.now().strftime("%Y%m%d%H%M%S%f") + str(random.randint(1000, 9999))
    body = {
        "auth": api_key,
        "data": [
            {
                "type": "viber",
                "id": msg_id,
                "phone": _phone_int(phone),
                "viber_type": "text",
                "viber_signature": viber_signature,
                "viber_message": text,
            }
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(ALPHASMS_API_URL, json=body)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.error("alphasms_request_failed phone=%s error=%s", phone, exc)
        return SendResult(ok=False, error=str(exc))
    except ValueError as exc:
        return SendResult(ok=False, error=f"alphasms invalid json: {exc}")

    provider_response: dict[str, Any] = {"body": data}
    ok = bool(data.get("success")) and isinstance(data.get("data"), list)
    item_ok = ok and data["data"] and data["data"][0].get("success")
    if item_ok:
        logger.info("alphasms_sent phone=%s", phone)
        return SendResult(ok=True, provider_response=provider_response)

    error = str(data.get("error") or data)
    if isinstance(data.get("data"), list) and data["data"]:
        error = str(data["data"][0].get("error") or error)
    logger.error("alphasms_rejected phone=%s error=%s", phone, error)
    return SendResult(ok=False, provider_response=provider_response, error=error[:4000])


class AlphaSmsSender:
    """AlphaSMS Viber text sender (Bitrix invoice mailings)."""

    def __init__(self, api_key: str, viber_signature: str) -> None:
        self._api_key = api_key
        self._viber_signature = viber_signature

    async def send(
        self,
        phone: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> SendResult:
        text = render_template(message_type, payload)
        if not text:
            return SendResult(ok=False, error=f"no template for message_type={message_type}")
        return await send_viber_text(
            api_key=self._api_key,
            viber_signature=self._viber_signature,
            phone=phone,
            text=text,
        )
