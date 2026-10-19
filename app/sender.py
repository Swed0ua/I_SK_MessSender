from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.templates import MAILING_MESSAGE_TYPES, MESSAGE_TEMPLATES, render_template

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
    """POST to MyChatbot Trigger Outreach. Auth is the unique URL itself."""
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
    """MyChatbot Trigger Outreach sender.

    render=False — static template text (welcome).
    render=True  — template with payload placeholders (Bitrix mailing).
    """

    def __init__(self, webhook_url: str, *, render: bool = False) -> None:
        self._url = webhook_url
        self._render = render

    async def send(
        self,
        phone: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> SendResult:
        if self._render:
            context = render_template(message_type, payload)
        else:
            context = MESSAGE_TEMPLATES.get(message_type)

        if not context:
            logger.warning(
                "decision=skipped phone=%s message_type=%s reason=no_template",
                phone,
                message_type,
            )
            return SendResult(ok=False, error=f"no template for message_type={message_type}")

        logger.info(
            "webhook_send phone=%s message_type=%s render=%s",
            phone,
            message_type,
            self._render,
        )
        return await send_webhook_message(url=self._url, phone=phone, context=context)


class RoutingSender:
    """Welcome → PROVIDER trigger; Bitrix mailing → separate Trigger Outreach URL."""

    def __init__(self, welcome: WebhookSender, mailing: WebhookSender | None) -> None:
        self._welcome = welcome
        self._mailing = mailing

    async def send(
        self,
        phone: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> SendResult:
        if message_type in MAILING_MESSAGE_TYPES:
            if self._mailing is None:
                return SendResult(ok=False, error="mailing trigger is not configured")
            return await self._mailing.send(phone, message_type, payload)
        return await self._welcome.send(phone, message_type, payload)
