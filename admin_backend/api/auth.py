from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions

from admin_backend.api.models import AdminClient


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_jwt(client: AdminClient) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(client.id),
        "name": client.name,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.ADMIN_JWT_TTL_SECONDS)).timestamp()),
    }
    return jwt.encode(payload, settings.ADMIN_JWT_SECRET, algorithm="HS256")


def decode_jwt(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.ADMIN_JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise exceptions.AuthenticationFailed("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise exceptions.AuthenticationFailed("invalid token") from exc


class JWTAuthentication(authentication.BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = authentication.get_authorization_header(request).decode("utf-8")
        if not header:
            return None

        parts = header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            raise exceptions.AuthenticationFailed("invalid authorization header")

        payload = decode_jwt(parts[1])
        try:
            client_id = UUID(str(payload.get("sub")))
        except (TypeError, ValueError) as exc:
            raise exceptions.AuthenticationFailed("invalid token subject") from exc

        client = AdminClient.objects.filter(id=client_id, is_active=True).first()
        if client is None:
            raise exceptions.AuthenticationFailed("client not found")
        return (client, payload)
