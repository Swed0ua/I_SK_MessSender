from __future__ import annotations

from rest_framework import serializers

from admin_backend.api.models import Notification


class AuthTokenSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128)
    token = serializers.CharField(min_length=8, max_length=255)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = (
            "id",
            "phone",
            "message_type",
            "status",
            "payload",
            "error",
            "sent_at",
            "created_at",
            "updated_at",
        )


class ManualSendSerializer(serializers.Serializer):
    phone = serializers.CharField(min_length=1, max_length=32)
    text = serializers.CharField(min_length=1, max_length=4000)
