from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from admin_backend.api.models import AdminUser


class Command(BaseCommand):
    help = "Delete an admin user by username."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Username")

    def handle(self, *args, **options):
        username = options["username"].strip()
        deleted, _ = AdminUser.objects.filter(username=username).delete()
        if not deleted:
            raise CommandError(f"user not found: {username}")
        self.stdout.write(self.style.SUCCESS(f"deleted user: {username}"))
