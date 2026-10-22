from __future__ import annotations

from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "admin_backend.api"
    label = "admin_api"
