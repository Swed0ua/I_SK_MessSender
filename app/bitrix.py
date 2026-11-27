from __future__ import annotations

import logging
from typing import Any

from fastapi import Request

from app import db
from app.bitrix_client import BitrixClient, BitrixError, first_phone
from app.bitrix_config import (
    CHANNEL_MYCHATBOT,
    FIELD_CABINET_PHONE,
    FIELD_CONTACT_FOP_TOV,
    FIELD_INVOICE_1C,
    FIELD_PDF_URL,
    MESSAGE_TYPE_LIST_MYCHATBOT,
    MYCHATBOT_LIST_CATEGORY_ID,
    get_stage_routes,
)
from app.bitrix_list import (
    ListTemplateHit,
    fill_placeholders,
    find_list_template,
    stage_name_for_id,
)
from app.config import Settings
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


def _deal_template_values(deal: dict[str, Any], contact: dict[str, Any] | None) -> dict[str, str]:
    contact = contact or {}
    return {
        "pdf_url": _str(deal.get(FIELD_PDF_URL)) or "",
        "cabinet_phone": _str(deal.get(FIELD_CABINET_PHONE)) or "",
        "invoice_number": _str(deal.get(FIELD_INVOICE_1C)) or "",
        "amount": _str(deal.get("OPPORTUNITY")) or "",
        "fop_tov": _str(contact.get(FIELD_CONTACT_FOP_TOV)) or "",
        "last_name": _str(contact.get("LAST_NAME")) or "",
        "first_name": _str(contact.get("NAME")) or "",
    }


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


async def _dispatch_list_mychatbot(
    *,
    deal: dict[str, Any],
    deal_id: str,
    stage_id: str,
    pool: Any,
    worker: NotificationWorker,
    bitrix: BitrixClient,
    settings: Settings,
) -> dict[str, Any]:
    iblock_id = settings.mychatbot_list_iblock_id
    property_code = settings.mychatbot_list_template_property
    if not iblock_id or not property_code:
        logger.info(
            "bitrix_list_skipped reason=list_not_configured stage_id=%s deal_id=%s",
            stage_id,
            deal_id,
        )
        return {"accepted": False, "reason": "ignored_stage", "stage_id": stage_id}

    category_id = _str(deal.get("CATEGORY_ID")) or ""
    if category_id != MYCHATBOT_LIST_CATEGORY_ID and not stage_id.startswith("C34:"):
        logger.info(
            "bitrix_stage_ignored stage_id=%s deal_id=%s category_id=%s",
            stage_id,
            deal_id,
            category_id,
        )
        return {"accepted": False, "reason": "ignored_stage", "stage_id": stage_id}

    try:
        stages = await bitrix.get_deal_category_stages(MYCHATBOT_LIST_CATEGORY_ID)
        stage_name = stage_name_for_id(stages, stage_id)
        if not stage_name:
            logger.info(
                "bitrix_list_stage_name_missing stage_id=%s deal_id=%s",
                stage_id,
                deal_id,
            )
            return {"accepted": False, "reason": "ignored_stage", "stage_id": stage_id}

        hit = await _resolve_list_template(
            bitrix,
            settings,
            stage_name=stage_name,
            primary_iblock_id=iblock_id,
            primary_property=property_code,
        )
        if hit is None:
            logger.info(
                "bitrix_list_template_missing stage_id=%s stage_name=%s deal_id=%s",
                stage_id,
                stage_name,
                deal_id,
            )
            return {
                "accepted": False,
                "reason": "ignored_stage",
                "stage_id": stage_id,
                "stage_name": stage_name,
            }

        contact_id = _str(deal.get("CONTACT_ID"))
        contact = await bitrix.get_contact(contact_id) if contact_id else None
    except BitrixError as exc:
        logger.exception("bitrix_list_lookup_failed deal_id=%s stage_id=%s", deal_id, stage_id)
        return {"accepted": False, "reason": "bitrix_error", "detail": str(exc)}

    phone_raw = first_phone(contact) if contact else None
    if not phone_raw:
        return {"accepted": False, "reason": "missing_phone", "deal_id": deal_id}

    values = _deal_template_values(deal, contact)
    context = fill_placeholders(hit.text, values)
    logger.info(
        "bitrix_list_template_matched stage_id=%s stage_name=%s deal_id=%s iblock_id=%s photo=%s",
        stage_id,
        stage_name,
        deal_id,
        hit.iblock_id,
        bool(hit.photo_url),
    )
    return await enqueue_mailing(
        phone_raw=phone_raw,
        message_type=MESSAGE_TYPE_LIST_MYCHATBOT,
        stage_id=stage_id,
        deal_id=deal_id,
        payload={
            **values,
            "channel": CHANNEL_MYCHATBOT,
            "context": context,
            "stage_name": stage_name,
            "list_iblock_id": hit.iblock_id,
        },
        pool=pool,
        worker=worker,
    )


async def _resolve_list_template(
    bitrix: BitrixClient,
    settings: Settings,
    *,
    stage_name: str,
    primary_iblock_id: str,
    primary_property: str,
) -> ListTemplateHit | None:
    primary_elements = await bitrix.get_list_elements(primary_iblock_id)
    hit = find_list_template(
        primary_elements,
        stage_name=stage_name,
        property_code=primary_property,
        iblock_id=primary_iblock_id,
    )
    if hit is not None:
        return hit

    fallback_iblock = settings.mychatbot_list_fallback_iblock_id
    fallback_property = settings.mychatbot_list_fallback_template_property
    if not fallback_iblock or not fallback_property:
        return None

    logger.info(
        "bitrix_list_primary_miss stage_name=%s iblock_id=%s trying_fallback=%s",
        stage_name,
        primary_iblock_id,
        fallback_iblock,
    )
    fallback_elements = await bitrix.get_list_elements(fallback_iblock)
    return find_list_template(
        fallback_elements,
        stage_name=stage_name,
        property_code=fallback_property,
        iblock_id=fallback_iblock,
        photo_property=settings.mychatbot_list_fallback_photo_property,
    )


async def dispatch_notification_mailing(
    payload: dict[str, Any],
    *,
    pool: Any,
    worker: NotificationWorker,
    bitrix: BitrixClient,
    settings: Settings,
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

    route = get_stage_routes().get(stage_id)
    if not route:
        return await _dispatch_list_mychatbot(
            deal=deal,
            deal_id=deal_id,
            stage_id=stage_id,
            pool=pool,
            worker=worker,
            bitrix=bitrix,
            settings=settings,
        )

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

    values = _deal_template_values(deal, contact)
    template_payload = {**values, "channel": route.channel}
    return await enqueue_mailing(
        phone_raw=phone_raw,
        message_type=route.message_type,
        stage_id=stage_id,
        deal_id=deal_id,
        payload=template_payload,
        pool=pool,
        worker=worker,
    )
