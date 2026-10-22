from __future__ import annotations

import secrets

from django.core.management.base import BaseCommand

from admin_backend.api.auth import hash_password
from admin_backend.api.models import AdminUser


class Command(BaseCommand):
    help = "Create or update an admin user (username + password) for the web UI."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Login username")
        parser.add_argument(
            "--password",
            default="",
            help="Optional password. Generated if omitted.",
        )

    def handle(self, *args, **options):
        username = options["username"].strip()
        raw_password = (options["password"] or "").strip() or secrets.token_urlsafe(16)
        if len(raw_password) < 8:
            self.stderr.write(self.style.ERROR("password must be at least 8 characters"))
            return

        user, created = AdminUser.objects.update_or_create(
            username=username,
            defaults={"password_hash": hash_password(raw_password), "is_active": True},
        )
        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"user {action}: {user.username} ({user.id})"))
        self.stdout.write(f"password={raw_password}")
        self.stdout.write("Store this password securely; it will not be shown again.")
