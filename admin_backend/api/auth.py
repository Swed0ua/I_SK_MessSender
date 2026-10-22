from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from rest_framework import authentication, exceptions

from admin_backend.api.models import AdminClient, AdminUser

KIND_CLIENT = "client"
KIND_USER = "user"


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def hash_password(raw_password: str) -> str:
    return make_password(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    return check_password(raw_password, password_hash)


def issue_jwt(*, subject_id: UUID, name: str, kind: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject_id),
        "name": name,
        "kind": kind,
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
            subject_id = UUID(str(payload.get("sub")))
        except (TypeError, ValueError) as exc:
            raise exceptions.AuthenticationFailed("invalid token subject") from exc

        kind = str(payload.get("kind") or KIND_CLIENT)
        if kind == KIND_USER:
            user = AdminUser.objects.filter(id=subject_id, is_active=True).first()
            if user is None:
                raise exceptions.AuthenticationFailed("user not found")
            return (user, payload)

        client = AdminClient.objects.filter(id=subject_id, is_active=True).first()
        if client is None:
            raise exceptions.AuthenticationFailed("client not found")
        return (client, payload)
