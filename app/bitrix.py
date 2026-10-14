from __future__ import annotations

import logging
from typing import Any

from fastapi import Request

from app import db
from app.bitrix_config import (
    FIELD_DEAL_ID,
    FIELD_PDF_URL,
    FIELD_PHONE,
    FIELD_STAGE_ID,
    MESSAGE_TYPE_KASA_VIBER,
    STAGE_KASA_VIBER,
)
from app.phone import PhoneError, normalize_phone
from app.worker import NotificationWorker

logger = logging.getLogger(__name__)


def _str(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


async def parse_bitrix_request(request: Request) -> dict[str, Any]:
    """Build payload from optional body + query. Query wins (Bitrix robot URL params)."""
    payload: dict[str, Any] = {}
    content_type = (request.headers.get("content-type") or "").lower()

    if "application/json" in content_type:
        body = await request.json()
        if isinstance(body, dict):
            payload.update(body)
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        payload.update({str(k): v for k, v in form.items()})

    for key, value in request.query_params.multi_items():
        if key == "api_key":
            continue
        payload[key] = value

    return payload


async def process_kasa_viber(
    payload: dict[str, Any],
    *,
    pool: Any,
    worker: NotificationWorker,
) -> dict[str, Any]:
    phone_raw = _str(payload, FIELD_PHONE)
    pdf_url = _str(payload, FIELD_PDF_URL)
    deal_id = _str(payload, FIELD_DEAL_ID)

    if not phone_raw:
        return {"accepted": False, "reason": "missing_phone"}
    if not pdf_url:
        return {"accepted": False, "reason": "missing_pdf_url"}

    try:
        phone = normalize_phone(phone_raw)
    except PhoneError as exc:
        return {"accepted": False, "reason": "invalid_phone", "detail": str(exc)}

    idempotency_key = (
        f"bitrix:{deal_id}:{STAGE_KASA_VIBER}"
        if deal_id
        else f"bitrix:{phone}:{STAGE_KASA_VIBER}:{pdf_url}"
    )

    row, created = await db.insert_notification(
        pool,
        phone=phone,
        message_type=MESSAGE_TYPE_KASA_VIBER,
        payload={"pdf_url": pdf_url, "deal_id": deal_id, "stage_id": STAGE_KASA_VIBER},
        idempotency_key=idempotency_key,
    )

    if not created:
        logger.info(
            "bitrix_kasa_viber duplicate id=%s phone=%s deal_id=%s",
            row["id"],
            phone,
            deal_id,
        )
        return {
            "accepted": True,
            "duplicate": True,
            "id": row["id"],
            "status": row["status"],
            "message_type": MESSAGE_TYPE_KASA_VIBER,
        }

    worker.enqueue(row["id"])
    logger.info(
        "bitrix_kasa_viber accepted id=%s phone=%s deal_id=%s",
        row["id"],
        phone,
        deal_id,
    )
    return {
        "accepted": True,
        "duplicate": False,
        "id": row["id"],
        "status": "pending",
        "phone": phone,
        "message_type": MESSAGE_TYPE_KASA_VIBER,
    }


async def dispatch_notification_mailing(
    payload: dict[str, Any],
    *,
    pool: Any,
    worker: NotificationWorker,
) -> dict[str, Any]:
    stage_id = _str(payload, FIELD_STAGE_ID)
    if not stage_id:
        return {"accepted": False, "reason": "missing_stage_id"}

    if stage_id == STAGE_KASA_VIBER:
        return await process_kasa_viber(payload, pool=pool, worker=worker)

    logger.info("bitrix_stage_ignored stage_id=%s", stage_id)
    return {"accepted": False, "reason": "ignored_stage", "stage_id": stage_id}
