from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx
from django.conf import settings
from django.utils import timezone

from admin_backend.api.models import Notification
from app.phone import PhoneError, normalize_phone

logger = logging.getLogger(__name__)

MESSAGE_TYPE_ADMIN_MANUAL = "admin_manual"


def send_manual_message(*, phone_raw: str, text: str) -> Notification:
    if not settings.MYCHATBOT_MAILING_WEBHOOK_URL:
        raise RuntimeError("MYCHATBOT_MAILING_WEBHOOK_URL is not configured")

    try:
        phone = normalize_phone(phone_raw)
    except PhoneError as exc:
        raise ValueError(str(exc)) from exc

    now = timezone.now()
    notif = Notification(
        id=uuid.uuid4(),
        phone=phone,
        message_type=MESSAGE_TYPE_ADMIN_MANUAL,
        idempotency_key=None,
        payload={"text": text, "source": "admin"},
        status="pending",
        provider_response=None,
        error=None,
        created_at=now,
        updated_at=now,
        sent_at=None,
    )
    notif.save(force_insert=True)

    body = {"phone": phone, "context": text}
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(settings.MYCHATBOT_MAILING_WEBHOOK_URL, json=body)
        provider_response: dict[str, Any] = {
            "status_code": response.status_code,
            "body": (response.text or "")[:1000],
        }
        if 200 <= response.status_code < 300:
            notif.status = "sent"
            notif.sent_at = timezone.now()
            notif.provider_response = provider_response
            notif.error = None
            logger.info("admin_manual_sent id=%s phone=%s", notif.id, phone)
        else:
            notif.status = "failed"
            notif.error = f"webhook HTTP {response.status_code}"
            notif.provider_response = provider_response
            logger.error("admin_manual_failed id=%s phone=%s error=%s", notif.id, phone, notif.error)
    except httpx.HTTPError as exc:
        notif.status = "failed"
        notif.error = str(exc)
        logger.exception("admin_manual_request_failed id=%s phone=%s", notif.id, phone)

    notif.updated_at = timezone.now()
    notif.save(update_fields=["status", "provider_response", "error", "sent_at", "updated_at"])
    return notif
