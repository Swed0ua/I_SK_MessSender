from __future__ import annotations

import asyncio
import logging
from typing import Any

from app import db
from app.sender import MessageSender

logger = logging.getLogger(__name__)


class NotificationWorker:
    def __init__(
        self,
        pool: Any,
        sender: MessageSender,
        *,
        poll_seconds: float = 2.0,
        max_retries: int = 3,
    ) -> None:
        self._pool = pool
        self._sender = sender
        self._poll_seconds = poll_seconds
        self._max_retries = max(1, max_retries)
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()

    def enqueue(self, notif_id: str) -> None:
        self._queue.put_nowait(notif_id)

    async def start(self) -> None:
        self._stopped.clear()
        self._task = asyncio.create_task(self._run(), name="notification-worker")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        logger.info("worker_started poll_seconds=%s max_retries=%s", self._poll_seconds, self._max_retries)
        while not self._stopped.is_set():
            notif_id: str | None = None
            try:
                notif_id = await asyncio.wait_for(self._queue.get(), timeout=self._poll_seconds)
            except (TimeoutError, asyncio.TimeoutError):
                # Py3.10: asyncio.TimeoutError is not builtin TimeoutError — must catch both
                # or the worker task dies after the first idle poll.
                pass
            except asyncio.CancelledError:
                raise

            try:
                if notif_id:
                    await self.process(notif_id)
                else:
                    await self.process(None)
            except Exception:
                logger.exception("worker_tick_failed notif_id=%s", notif_id)

    async def process(self, notif_id: str | None) -> None:
        row = await db.claim_pending(self._pool, notif_id)
        if row is None:
            return

        nid = row["id"]
        phone = row["phone"]
        message_type = row["message_type"]
        payload = row.get("payload") or {}

        last_error = "unknown error"
        for attempt in range(1, self._max_retries + 1):
            try:
                result = await self._sender.send(phone, message_type, payload)
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "decision=retry id=%s attempt=%s/%s error=%s",
                    nid,
                    attempt,
                    self._max_retries,
                    last_error,
                )
            else:
                if result.ok:
                    await db.mark_sent(self._pool, nid, result.provider_response)
                    logger.info(
                        "decision=sent id=%s phone=%s message_type=%s",
                        nid,
                        phone,
                        message_type,
                    )
                    return
                last_error = result.error or "provider rejected"

            if attempt < self._max_retries:
                await asyncio.sleep(min(2 ** (attempt - 1), 8))

        await db.mark_failed(self._pool, nid, last_error)
        logger.error(
            "decision=failed id=%s phone=%s message_type=%s error=%s",
            nid,
            phone,
            message_type,
            last_error,
        )
