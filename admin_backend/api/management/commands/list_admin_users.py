from __future__ import annotations

from django.core.management.base import BaseCommand

from admin_backend.api.models import AdminUser


class Command(BaseCommand):
    help = "List admin users (username + password)."

    def handle(self, *args, **options):
        rows = list(AdminUser.objects.all().order_by("username"))
        if not rows:
            self.stdout.write("no users")
            return
        for u in rows:
            flag = "active" if u.is_active else "inactive"
            self.stdout.write(f"{u.username}\tid={u.id}\t{flag}\tcreated={u.created_at.isoformat()}")
