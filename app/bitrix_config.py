from __future__ import annotations

from dataclasses import dataclass

# Deal UF fields
FIELD_PDF_URL = "UF_CRM_1775969375546"
FIELD_INVOICE_1C = "UF_CRM_1683022115"
FIELD_CABINET_PHONE = "UF_CRM_1683054163"

# Contact UF fields
FIELD_CONTACT_FOP_TOV = "UF_CRM_1770028806"

CHANNEL_MYCHATBOT = "mychatbot"
CHANNEL_ALPHASMS = "alphasms"

# message_type per mailing template
MESSAGE_TYPE_CABINET_VIBER = "bitrix_cabinet_invoice_viber"
MESSAGE_TYPE_KASA_PURCHASE_VIBER = "bitrix_kasa_purchase_viber"
MESSAGE_TYPE_CABINET_ALPHASMS = "bitrix_cabinet_invoice_alphasms"
MESSAGE_TYPE_KASA_PURCHASE_ALPHASMS = "bitrix_kasa_purchase_alphasms"
MESSAGE_TYPE_LIST_MYCHATBOT = "bitrix_list_mychatbot"

MAILING_MESSAGE_TYPES = frozenset({
    MESSAGE_TYPE_CABINET_VIBER,
    MESSAGE_TYPE_KASA_PURCHASE_VIBER,
    MESSAGE_TYPE_LIST_MYCHATBOT,
})
ALPHASMS_MESSAGE_TYPES = frozenset({
    MESSAGE_TYPE_CABINET_ALPHASMS,
    MESSAGE_TYPE_KASA_PURCHASE_ALPHASMS,
})

# Bitrix list fallback (after hardcoded stage map): category 34 ↔ list by stage NAME
MYCHATBOT_LIST_CATEGORY_ID = "34"


@dataclass(frozen=True)
class StageRoute:
    message_type: str
    channel: str


# stage_id -> route (add rows to extend)
_STAGE_ROUTES: dict[str, StageRoute] = {
    # MyChatbot
    "C34:PREPARATION": StageRoute(MESSAGE_TYPE_CABINET_VIBER, CHANNEL_MYCHATBOT),
    "C34:PREPAYMENT_INVOIC": StageRoute(MESSAGE_TYPE_KASA_PURCHASE_VIBER, CHANNEL_MYCHATBOT),
    # AlphaSMS (parallel columns)
    "C30:UC_YO664C": StageRoute(MESSAGE_TYPE_CABINET_ALPHASMS, CHANNEL_ALPHASMS),
    "C30:UC_NJLT77": StageRoute(MESSAGE_TYPE_KASA_PURCHASE_ALPHASMS, CHANNEL_ALPHASMS),
}


def get_stage_routes() -> dict[str, StageRoute]:
    return dict(_STAGE_ROUTES)


# Backward-compatible alias
STAGE_MESSAGE_TYPES = {k: v.message_type for k, v in _STAGE_ROUTES.items()}
