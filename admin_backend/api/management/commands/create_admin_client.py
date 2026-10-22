from __future__ import annotations

import secrets

from django.core.management.base import BaseCommand

from admin_backend.api.auth import hash_token
from admin_backend.api.models import AdminClient


class Command(BaseCommand):
    help = "Create an admin API client and print its raw token once."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Client name, e.g. web-admin")
        parser.add_argument(
            "--token",
            default="",
            help="Optional raw token. Generated if omitted.",
        )

    def handle(self, *args, **options):
        name = options["name"].strip()
        raw_token = (options["token"] or "").strip() or secrets.token_urlsafe(32)
        token_hash = hash_token(raw_token)

        client, created = AdminClient.objects.update_or_create(
            name=name,
            defaults={"token_hash": token_hash, "is_active": True},
        )
        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"client {action}: {client.name} ({client.id})"))
        self.stdout.write(f"raw_token={raw_token}")
        self.stdout.write("Store this token securely; it will not be shown again.")
