from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from admin_backend.api.models import AdminClient


class Command(BaseCommand):
    help = "Delete an admin API client by name."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Client name")

    def handle(self, *args, **options):
        name = options["name"].strip()
        deleted, _ = AdminClient.objects.filter(name=name).delete()
        if not deleted:
            raise CommandError(f"client not found: {name}")
        self.stdout.write(self.style.SUCCESS(f"deleted client: {name}"))
