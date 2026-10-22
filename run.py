from __future__ import annotations

import logging
import threading

import uvicorn

from app.config import load_settings

logger = logging.getLogger(__name__)


def _start_admin_in_background() -> None:
    """MessSender + Admin: admin runs in a daemon thread; MessSender stays on the main thread."""
    from run_admin import bootstrap_admin, serve_admin

    bootstrap_admin()

    thread = threading.Thread(target=serve_admin, name="admin-api", daemon=True)
    thread.start()
    logger.info("admin API starting in background thread")


def main() -> None:
    settings = load_settings()
    _start_admin_in_background()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
