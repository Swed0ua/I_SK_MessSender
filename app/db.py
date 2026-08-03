from __future__ import annotations

import json
import uuid
from typing import Any

import asyncpg

from app.templates import MESSAGE_TEMPLATES

ALLOWED_MESSAGE_TYPES = frozenset(MESSAGE_TEMPLATES)


async def create_pool(database_url: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(database_url, min_size=1, max_size=5)


async def apply_schema(pool: asyncpg.Pool, schema_path: str) -> None:
    with open(schema_path, encoding="utf-8") as f:
        sql = f.read()
    async with pool.acquire() as conn:
        await conn.execute(sql)


def row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    data = dict(row)
    for key in ("id",):
        if key in data and data[key] is not None:
            data[key] = str(data[key])
    for key in ("created_at", "updated_at", "sent_at"):
        if key in data and data[key] is not None:
            data[key] = data[key].isoformat()
    if isinstance(data.get("payload"), str):
        data["payload"] = json.loads(data["payload"])
    if isinstance(data.get("provider_response"), str):
        data["provider_response"] = json.loads(data["provider_response"])
    return data


async def insert_notification(
    pool: asyncpg.Pool,
    *,
    phone: str,
    message_type: str,
    payload: dict[str, Any],
    idempotency_key: str | None,
) -> tuple[dict[str, Any], bool]:
    """Insert pending notification. Returns (row, created)."""
    notif_id = uuid.uuid4()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                """
                INSERT INTO notifications (id, phone, message_type, idempotency_key, payload, status)
                VALUES ($1, $2, $3, $4, $5::jsonb, 'pending')
                RETURNING *
                """,
                notif_id,
                phone,
                message_type,
                idempotency_key,
                json.dumps(payload, ensure_ascii=False),
            )
            return row_to_dict(row), True
        except asyncpg.UniqueViolationError:
            if idempotency_key:
                existing = await conn.fetchrow(
                    "SELECT * FROM notifications WHERE idempotency_key = $1",
                    idempotency_key,
                )
                if existing:
                    return row_to_dict(existing), False
            existing = await conn.fetchrow(
                """
                SELECT * FROM notifications
                WHERE phone = $1 AND message_type = $2
                """,
                phone,
                message_type,
            )
            if existing is None:
                raise
            return row_to_dict(existing), False


async def get_notification(pool: asyncpg.Pool, notif_id: str) -> dict[str, Any] | None:
    async with pool.acquire() as conn:
        try:
            uid = uuid.UUID(notif_id)
        except ValueError:
            return None
        row = await conn.fetchrow("SELECT * FROM notifications WHERE id = $1", uid)
        return row_to_dict(row) if row else None


async def claim_pending(pool: asyncpg.Pool, notif_id: str | None = None) -> dict[str, Any] | None:
    """Pick one pending row (single in-process worker; mark_* guards status)."""
    async with pool.acquire() as conn:
        if notif_id is not None:
            try:
                uid = uuid.UUID(notif_id)
            except ValueError:
                return None
            row = await conn.fetchrow(
                "SELECT * FROM notifications WHERE id = $1 AND status = 'pending'",
                uid,
            )
        else:
            row = await conn.fetchrow(
                """
                SELECT * FROM notifications
                WHERE status = 'pending'
                ORDER BY created_at
                LIMIT 1
                """
            )
        return row_to_dict(row) if row else None


async def mark_sent(
    pool: asyncpg.Pool,
    notif_id: str,
    provider_response: dict[str, Any] | None,
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE notifications
            SET status = 'sent',
                provider_response = $2::jsonb,
                error = NULL,
                sent_at = now(),
                updated_at = now()
            WHERE id = $1 AND status = 'pending'
            """,
            uuid.UUID(notif_id),
            json.dumps(provider_response or {}, ensure_ascii=False),
        )


async def mark_failed(pool: asyncpg.Pool, notif_id: str, error: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE notifications
            SET status = 'failed',
                error = $2,
                updated_at = now()
            WHERE id = $1 AND status = 'pending'
            """,
            uuid.UUID(notif_id),
            error[:4000],
        )
