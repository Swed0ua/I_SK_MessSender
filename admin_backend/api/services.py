from __future__ import annotations

import logging
import threading
import uuid
from typing import Any

import httpx
from django.conf import settings
from django.utils import timezone

from admin_backend.api.models import Notification
from app.phone import PhoneError, normalize_phone

logger = logging.getLogger(__name__)

MESSAGE_TYPE_ADMIN_MANUAL = "admin_manual"


def _require_mailing_url() -> str:
    url = settings.MYCHATBOT_MAILING_WEBHOOK_URL
    if not url:
        raise RuntimeError("MYCHATBOT_MAILING_WEBHOOK_URL is not configured")
    return url


def _new_notification(*, phone: str, text: str, campaign_id: str | None) -> Notification:
    now = timezone.now()
    payload: dict[str, Any] = {"text": text, "source": "admin"}
    if campaign_id:
        payload["campaign_id"] = campaign_id
        payload["source"] = "admin_bulk"
    return Notification(
        id=uuid.uuid4(),
        phone=phone,
        message_type=MESSAGE_TYPE_ADMIN_MANUAL,
        idempotency_key=None,
        payload=payload,
        status="pending",
        provider_response=None,
        error=None,
        created_at=now,
        updated_at=now,
        sent_at=None,
    )


def _deliver(notif: Notification, *, text: str, webhook_url: str) -> None:
    body = {"phone": notif.phone, "context": text}
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(webhook_url, json=body)
        provider_response: dict[str, Any] = {
            "status_code": response.status_code,
            "body": (response.text or "")[:1000],
        }
        if 200 <= response.status_code < 300:
            notif.status = "sent"
            notif.sent_at = timezone.now()
            notif.provider_response = provider_response
            notif.error = None
            logger.info("admin_sent id=%s phone=%s", notif.id, notif.phone)
        else:
            notif.status = "failed"
            notif.error = f"webhook HTTP {response.status_code}"
            notif.provider_response = provider_response
            logger.error("admin_failed id=%s phone=%s error=%s", notif.id, notif.phone, notif.error)
    except httpx.HTTPError as exc:
        notif.status = "failed"
        notif.error = str(exc)
        logger.exception("admin_request_failed id=%s phone=%s", notif.id, notif.phone)

    notif.updated_at = timezone.now()
    notif.save(update_fields=["status", "provider_response", "error", "sent_at", "updated_at"])


def send_manual_message(*, phone_raw: str, text: str) -> Notification:
    webhook_url = _require_mailing_url()
    try:
        phone = normalize_phone(phone_raw)
    except PhoneError as exc:
        raise ValueError(str(exc)) from exc

    notif = _new_notification(phone=phone, text=text, campaign_id=None)
    notif.save(force_insert=True)
    _deliver(notif, text=text, webhook_url=webhook_url)
    return notif


def enqueue_bulk_campaign(*, phones: list[str], text: str) -> dict[str, Any]:
    """Insert pending rows and send sequentially in a background thread."""
    webhook_url = _require_mailing_url()
    campaign_id = str(uuid.uuid4())
    ids: list[uuid.UUID] = []

    for phone in phones:
        notif = _new_notification(phone=phone, text=text, campaign_id=campaign_id)
        notif.save(force_insert=True)
        ids.append(notif.id)

    def _run() -> None:
        from django.db import close_old_connections

        close_old_connections()
        try:
            for notif_id in ids:
                notif = Notification.objects.filter(id=notif_id).first()
                if notif is None:
                    continue
                _deliver(notif, text=text, webhook_url=webhook_url)
        finally:
            close_old_connections()

    threading.Thread(target=_run, name=f"bulk-{campaign_id[:8]}", daemon=True).start()
    logger.info("admin_bulk_enqueued campaign_id=%s count=%s", campaign_id, len(ids))
    return {"campaign_id": campaign_id, "total": len(ids), "status": "pending"}
