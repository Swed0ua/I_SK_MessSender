from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app import db
from app.auth import require_api_key
from app.config import Settings, load_settings
from app.phone import PhoneError, normalize_phone
from app.schemas import NotificationCreate
from app.sender import WebhookSender
from app.worker import NotificationWorker

logger = logging.getLogger(__name__)
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_pool(request: Request):
    return request.app.state.pool


def get_worker(request: Request) -> NotificationWorker:
    return request.app.state.worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    pool = await db.create_pool(settings.database_url)
    await db.apply_schema(pool, str(SCHEMA_PATH))

    sender = WebhookSender(settings.provider_webhook_url)
    worker = NotificationWorker(
        pool,
        sender,
        poll_seconds=settings.worker_poll_seconds,
        max_retries=settings.worker_max_retries,
    )
    await worker.start()

    app.state.settings = settings
    app.state.pool = pool
    app.state.worker = worker

    logger.info("service_started host=%s port=%s", settings.host, settings.port)
    try:
        yield
    finally:
        await worker.stop()
        await pool.close()
        logger.info("service_stopped")


app = FastAPI(title="Notification Service", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/notifications")
async def create_notification(
    body: NotificationCreate,
    settings: Annotated[Settings, Depends(get_settings)],
    pool: Annotated[Any, Depends(get_pool)],
    worker: Annotated[NotificationWorker, Depends(get_worker)],
    x_api_key: Annotated[str | None, Header(alias="X-Api-Key")] = None,
) -> Any:
    require_api_key(settings, x_api_key)

    message_type = body.message_type.strip()
    if message_type not in db.ALLOWED_MESSAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid message_type: {message_type}",
        )

    try:
        phone = normalize_phone(body.phone)
    except PhoneError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    idempotency_key = body.idempotency_key.strip() if body.idempotency_key else None

    try:
        row, created = await db.insert_notification(
            pool,
            phone=phone,
            message_type=message_type,
            payload=body.payload,
            idempotency_key=idempotency_key,
        )
    except Exception:
        logger.exception("insert_failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="internal error")

    if not created:
        logger.info(
            "decision=skipped id=%s phone=%s message_type=%s reason=duplicate status=%s",
            row["id"],
            row["phone"],
            row["message_type"],
            row["status"],
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"id": row["id"], "status": row["status"], "duplicate": True},
        )

    worker.enqueue(row["id"])
    logger.info(
        "decision=accepted id=%s phone=%s message_type=%s",
        row["id"],
        row["phone"],
        row["message_type"],
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "id": row["id"],
            "status": "pending",
            "phone": row["phone"],
            "message_type": row["message_type"],
        },
    )


@app.get("/v1/notifications/{notif_id}")
async def get_notification(
    notif_id: str,
    settings: Annotated[Settings, Depends(get_settings)],
    pool: Annotated[Any, Depends(get_pool)],
    x_api_key: Annotated[str | None, Header(alias="X-Api-Key")] = None,
) -> Any:
    require_api_key(settings, x_api_key)

    row = await db.get_notification(pool, notif_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

    return {
        "id": row["id"],
        "status": row["status"],
        "phone": row["phone"],
        "message_type": row["message_type"],
        "error": row.get("error"),
        "sent_at": row.get("sent_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }
