from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.templates import MESSAGE_TEMPLATES

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SendResult:
    ok: bool
    provider_response: dict[str, Any] | None = None
    error: str | None = None


class MessageSender(Protocol):
    async def send(
        self,
        phone: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> SendResult: ...


async def send_webhook_message(*, url: str, phone: str, context: str) -> SendResult:
    """POST message to MyChatbot webhook. Auth is the unique URL itself."""
    body = {"context": context, "phone": phone}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=body)
    except httpx.HTTPError as exc:
        logger.error("webhook_request_failed phone=%s error=%s", phone, exc)
        return SendResult(ok=False, error=str(exc))

    text = (response.text or "")[:1000]
    provider_response: dict[str, Any] = {
        "status_code": response.status_code,
        "body": text,
    }

    if 200 <= response.status_code < 300:
        logger.info("webhook_sent phone=%s status=%s", phone, response.status_code)
        return SendResult(ok=True, provider_response=provider_response)

    error = f"webhook HTTP {response.status_code}: {text}"
    logger.error("webhook_rejected phone=%s error=%s", phone, error)
    return SendResult(ok=False, provider_response=provider_response, error=error)


class WebhookSender:
    def __init__(self, webhook_url: str) -> None:
        self._url = webhook_url

    async def send(
        self,
        phone: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> SendResult:
        context = MESSAGE_TEMPLATES.get(message_type)
        if not context:
            logger.warning(
                "decision=skipped phone=%s message_type=%s reason=no_template",
                phone,
                message_type,
            )
            return SendResult(ok=False, error=f"no template for message_type={message_type}")

        logger.info(
            "webhook_send phone=%s message_type=%s context=%r",
            phone,
            message_type,
            context,
        )
        return await send_webhook_message(url=self._url, phone=phone, context=context)
