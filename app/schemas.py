from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    phone: str = Field(min_length=1)
    message_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=255)
