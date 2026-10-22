from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    load_dotenv(ROOT / ".env")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin_backend.settings")

    import django

    django.setup()

    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection

    # Shared notifications table: drop legacy unique(phone, message_type).
    with connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_phone_type_uq"
        )
        cursor.execute("DROP INDEX IF EXISTS notifications_phone_type_uq")
        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS notifications_phone_type_welcome_uq
                ON notifications (phone, message_type)
                WHERE message_type = 'welcome_new_contractor'
            """
        )

    call_command("migrate", "admin_api", interactive=False, verbosity=1)
    call_command(
        "runserver",
        f"{settings.ADMIN_HOST}:{settings.ADMIN_PORT}",
        use_reloader=False,
        verbosity=1,
    )


if __name__ == "__main__":
    main()
