from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env: {name}")
    return value


def _optional(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    api_key: str
    database_url: str
    log_level: str
    worker_poll_seconds: float
    worker_max_retries: int
    provider_webhook_url: str
    mychatbot_mailing_webhook_url: str | None
    bitrix_webhook_url: str | None
    alphasms_api_key: str | None
    alphasms_viber_signature: str | None
    mychatbot_list_iblock_id: str | None
    mychatbot_list_template_property: str | None
    mychatbot_list_fallback_iblock_id: str | None
    mychatbot_list_fallback_template_property: str | None
    mychatbot_list_fallback_photo_property: str | None


def load_settings() -> Settings:
    return Settings(
        host=os.getenv("HOST", "127.0.0.1").strip() or "127.0.0.1",
        port=int(os.getenv("PORT", "8080")),
        api_key=_require("API_KEY"),
        database_url=_require("DATABASE_URL"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        worker_poll_seconds=float(os.getenv("WORKER_POLL_SECONDS", "2")),
        worker_max_retries=int(os.getenv("WORKER_MAX_RETRIES", "3")),
        provider_webhook_url=_require("PROVIDER_WEBHOOK_URL"),
        mychatbot_mailing_webhook_url=_optional("MYCHATBOT_MAILING_WEBHOOK_URL"),
        bitrix_webhook_url=_optional("BITRIX_WEBHOOK_URL"),
        alphasms_api_key=_optional("ALPHASMS_API_KEY"),
        alphasms_viber_signature=_optional("ALPHASMS_VIBER_SIGNATURE"),
        mychatbot_list_iblock_id=_optional("MYCHATBOT_LIST_IBLOCK_ID"),
        mychatbot_list_template_property=_optional("MYCHATBOT_LIST_TEMPLATE_PROPERTY"),
        mychatbot_list_fallback_iblock_id=_optional("MYCHATBOT_LIST_FALLBACK_IBLOCK_ID"),
        mychatbot_list_fallback_template_property=_optional(
            "MYCHATBOT_LIST_FALLBACK_TEMPLATE_PROPERTY"
        ),
        mychatbot_list_fallback_photo_property=_optional(
            "MYCHATBOT_LIST_FALLBACK_PHOTO_PROPERTY"
        ),
    )
