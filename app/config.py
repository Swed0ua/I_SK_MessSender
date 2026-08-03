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
    )
