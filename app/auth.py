from __future__ import annotations

import hmac

from fastapi import HTTPException, status

from app.config import Settings


def require_api_key(settings: Settings, x_api_key: str | None) -> None:
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
