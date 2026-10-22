from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("admin_api", "0002_notification"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminUser",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("username", models.CharField(max_length=128, unique=True)),
                ("password_hash", models.CharField(max_length=128)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "admin_api_users",
                "ordering": ["username"],
            },
        ),
    ]
