from __future__ import annotations

# Deal UF fields
FIELD_PDF_URL = "UF_CRM_1775969375546"
FIELD_INVOICE_1C = "UF_CRM_1683022115"
FIELD_CABINET_PHONE = "UF_CRM_1683054163"

# Contact UF fields
FIELD_CONTACT_FOP_TOV = "UF_CRM_1770028806"

# message_type per mailing template
MESSAGE_TYPE_CABINET_VIBER = "bitrix_cabinet_invoice_viber"
MESSAGE_TYPE_KASA_PURCHASE_VIBER = "bitrix_kasa_purchase_viber"

# stage_id -> message_type (add rows to extend)
STAGE_MESSAGE_TYPES: dict[str, str] = {
    "C34:PREPARATION": MESSAGE_TYPE_CABINET_VIBER,
    "C34:PREPAYMENT_INVOIC": MESSAGE_TYPE_KASA_PURCHASE_VIBER,
}

MAILING_MESSAGE_TYPES = frozenset(STAGE_MESSAGE_TYPES.values())
