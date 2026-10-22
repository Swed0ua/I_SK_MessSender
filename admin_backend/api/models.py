from __future__ import annotations

import uuid

from django.db import models


class AdminClient(models.Model):
    """Dev/API clients: exchange a secret token for a JWT."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128, unique=True)
    token_hash = models.CharField(max_length=64, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "admin_api_clients"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @property
    def is_authenticated(self) -> bool:
        return True


class AdminUser(models.Model):
    """Human operators: username + password → JWT (web UI)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=128, unique=True)
    password_hash = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "admin_api_users"
        ordering = ["username"]

    def __str__(self) -> str:
        return self.username

    @property
    def name(self) -> str:
        return self.username

    @property
    def is_authenticated(self) -> bool:
        return True


class Notification(models.Model):
    """Read/write mapping to shared MessSender notifications table."""

    id = models.UUIDField(primary_key=True)
    phone = models.CharField(max_length=32)
    message_type = models.CharField(max_length=128)
    idempotency_key = models.CharField(max_length=255, null=True, blank=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, default="pending")
    provider_response = models.JSONField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "notifications"
        ordering = ["-created_at"]
