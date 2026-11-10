from __future__ import annotations

import logging
from typing import Any

from fastapi import Request

from app import db
from app.bitrix_client import BitrixClient, BitrixError, first_phone
from app.bitrix_config import (
    FIELD_CABINET_PHONE,
    FIELD_CONTACT_FOP_TOV,
    FIELD_INVOICE_1C,
    FIELD_PDF_URL,
    STAGE_MESSAGE_TYPES,
)
from app.phone import PhoneError, normalize_phone
from app.worker import NotificationWorker

logger = logging.getLogger(__name__)


def _str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


async def parse_bitrix_request(request: Request) -> dict[str, Any]:
    """Parse Bitrix webhook body (form or JSON)."""
    content_type = (request.headers.get("content-type") or "").lower()

    if "application/json" in content_type:
        body = await request.json()
        if isinstance(body, dict):
            return body

    if (
        "application/x-www-form-urlencoded" in content_type
        or "multipart/form-data" in content_type
        or content_type == ""
    ):
        form = await request.form()
        return {str(k): v for k, v in form.items()}

    return {}


def extract_deal_id(payload: dict[str, Any]) -> str | None:
    """Deal ID from Bitrix event/robot payload."""
    flat = _str(payload.get("data[FIELDS][ID]"))
    if flat:
        return flat

    data = payload.get("data")
    if isinstance(data, dict):
        fields = data.get("FIELDS")
        if isinstance(fields, dict):
            deal_id = _str(fields.get("ID"))
            if deal_id:
                return deal_id
        deal_id = _str(data.get("ID") or data.get("id"))
        if deal_id:
            return deal_id

    return _str(payload.get("ID") or payload.get("id"))


async def enqueue_mailing(
    *,
    phone_raw: str,
    message_type: str,
    stage_id: str,
    deal_id: str,
    payload: dict[str, Any],
    pool: Any,
    worker: NotificationWorker,
) -> dict[str, Any]:
    try:
        phone = normalize_phone(phone_raw)
    except PhoneError as exc:
        return {"accepted": False, "reason": "invalid_phone", "detail": str(exc)}

    idempotency_key = f"bitrix:{deal_id}:{stage_id}"
    row_payload = {**payload, "deal_id": deal_id, "stage_id": stage_id}

    row, created = await db.insert_notification(
        pool,
        phone=phone,
        message_type=message_type,
        payload=row_payload,
        idempotency_key=idempotency_key,
    )

    if not created:
        logger.info(
            "bitrix_mailing duplicate id=%s phone=%s deal_id=%s stage_id=%s",
            row["id"],
            phone,
            deal_id,
            stage_id,
        )
        return {
            "accepted": True,
            "duplicate": True,
            "id": row["id"],
            "status": row["status"],
            "message_type": message_type,
        }

    worker.enqueue(row["id"])
    logger.info(
        "bitrix_mailing accepted id=%s phone=%s deal_id=%s stage_id=%s message_type=%s",
        row["id"],
        phone,
        deal_id,
        stage_id,
        message_type,
    )
    return {
        "accepted": True,
        "duplicate": False,
        "id": row["id"],
        "status": "pending",
        "phone": phone,
        "message_type": message_type,
    }


async def dispatch_notification_mailing(
    payload: dict[str, Any],
    *,
    pool: Any,
    worker: NotificationWorker,
    bitrix: BitrixClient,
) -> dict[str, Any]:
    deal_id = extract_deal_id(payload)
    if not deal_id:
        return {"accepted": False, "reason": "missing_deal_id"}

    try:
        deal = await bitrix.get_deal(deal_id)
    except BitrixError as exc:
        logger.exception("bitrix_get_deal_failed deal_id=%s", deal_id)
        return {"accepted": False, "reason": "bitrix_error", "detail": str(exc)}

    stage_id = _str(deal.get("STAGE_ID"))
    if not stage_id:
        return {"accepted": False, "reason": "missing_stage_id"}

    message_type = STAGE_MESSAGE_TYPES.get(stage_id)
    if not message_type:
        logger.info("bitrix_stage_ignored stage_id=%s deal_id=%s", stage_id, deal_id)
        return {"accepted": False, "reason": "ignored_stage", "stage_id": stage_id}

    pdf_url = _str(deal.get(FIELD_PDF_URL))
    if not pdf_url:
        return {"accepted": False, "reason": "missing_pdf_url", "deal_id": deal_id}

    contact_id = _str(deal.get("CONTACT_ID"))
    try:
        contact = await bitrix.get_contact(contact_id) if contact_id else None
    except BitrixError as exc:
        logger.exception("bitrix_get_contact_failed contact_id=%s", contact_id)
        return {"accepted": False, "reason": "bitrix_error", "detail": str(exc)}

    phone_raw = first_phone(contact) if contact else None
    if not phone_raw:
        return {"accepted": False, "reason": "missing_phone", "deal_id": deal_id}

    template_payload = {
        "pdf_url": pdf_url,
        "cabinet_phone": _str(deal.get(FIELD_CABINET_PHONE)) or "",
        "invoice_number": _str(deal.get(FIELD_INVOICE_1C)) or "",
        "amount": _str(deal.get("OPPORTUNITY")) or "",
        "fop_tov": _str(contact.get(FIELD_CONTACT_FOP_TOV)) or "",
        "last_name": _str(contact.get("LAST_NAME")) or "",
        "first_name": _str(contact.get("NAME")) or "",
    }
    return await enqueue_mailing(
        phone_raw=phone_raw,
        message_type=message_type,
        stage_id=stage_id,
        deal_id=deal_id,
        payload=template_payload,
        pool=pool,
        worker=worker,
    )
