from __future__ import annotations

from django.core.management.base import BaseCommand

from admin_backend.api.models import AdminClient


class Command(BaseCommand):
    help = "List admin API clients (token-based, for development)."

    def handle(self, *args, **options):
        rows = list(AdminClient.objects.all().order_by("name"))
        if not rows:
            self.stdout.write("no clients")
            return
        for c in rows:
            flag = "active" if c.is_active else "inactive"
            self.stdout.write(f"{c.name}\tid={c.id}\t{flag}\tcreated={c.created_at.isoformat()}")
