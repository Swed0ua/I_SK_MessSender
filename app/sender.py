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


async def send_mailing_message(
    *,
    url: str,
    phone: str,
    context: str,
    api_token: str | None = None,
    phone_id: str | None = None,
) -> SendResult:
    """POST to MyChatbot mailing trigger (separate token/URL from welcome webhook)."""
    body: dict[str, Any] = {"phone_number": phone, "context": context}
    if phone_id:
        body["phone_id"] = phone_id

    headers: dict[str, str] = {}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=body, headers=headers or None)
    except httpx.HTTPError as exc:
        logger.error("mailing_request_failed phone=%s error=%s", phone, exc)
        return SendResult(ok=False, error=str(exc))

    text = (response.text or "")[:1000]
    provider_response: dict[str, Any] = {
        "status_code": response.status_code,
        "body": text,
    }

    if 200 <= response.status_code < 300:
        logger.info("mailing_sent phone=%s status=%s", phone, response.status_code)
        return SendResult(ok=True, provider_response=provider_response)

    error = f"mailing HTTP {response.status_code}: {text}"
    logger.error("mailing_rejected phone=%s error=%s", phone, error)
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


class MailingSender:
    def __init__(
        self,
        webhook_url: str,
        *,
        api_token: str | None = None,
        phone_id: str | None = None,
    ) -> None:
        self._url = webhook_url
        self._api_token = api_token
        self._phone_id = phone_id

    async def send(
        self,
        phone: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> SendResult:
        context = render_template(message_type, payload)
        if not context:
            logger.warning(
                "decision=skipped phone=%s message_type=%s reason=no_template",
                phone,
                message_type,
            )
            return SendResult(ok=False, error=f"no template for message_type={message_type}")

        logger.info(
            "mailing_send phone=%s message_type=%s",
            phone,
            message_type,
        )
        return await send_mailing_message(
            url=self._url,
            phone=phone,
            context=context,
            api_token=self._api_token,
            phone_id=self._phone_id,
        )


class RoutingSender:
    """Routes welcome types to webhook trigger; Bitrix mailing types to mailing API."""

    def __init__(self, webhook: WebhookSender, mailing: MailingSender | None) -> None:
        self._webhook = webhook
        self._mailing = mailing

    async def send(
        self,
        phone: str,
        message_type: str,
        payload: dict[str, Any],
    ) -> SendResult:
        if message_type in MAILING_MESSAGE_TYPES:
            if self._mailing is None:
                return SendResult(ok=False, error="mailing sender is not configured")
            return await self._mailing.send(phone, message_type, payload)
        return await self._webhook.send(phone, message_type, payload)
