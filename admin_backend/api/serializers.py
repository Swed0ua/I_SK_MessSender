from __future__ import annotations

from rest_framework import serializers

from admin_backend.api.models import Notification


class AuthTokenSerializer(serializers.Serializer):
    """Either username+password (users) or name+token (dev API clients)."""

    username = serializers.CharField(max_length=128, required=False, allow_blank=True)
    password = serializers.CharField(min_length=8, max_length=255, required=False, allow_blank=True)
    name = serializers.CharField(max_length=128, required=False, allow_blank=True)
    token = serializers.CharField(min_length=8, max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        username = (attrs.get("username") or "").strip()
        password = attrs.get("password") or ""
        name = (attrs.get("name") or "").strip()
        token = attrs.get("token") or ""

        has_user = bool(username and password)
        has_client = bool(name and token)
        if has_user and has_client:
            raise serializers.ValidationError("use either username/password or name/token")
        if not has_user and not has_client:
            raise serializers.ValidationError("provide username+password or name+token")

        attrs["username"] = username
        attrs["name"] = name
        attrs["mode"] = "user" if has_user else "client"
        return attrs


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
    text = serializers.CharField(required=False, allow_blank=True, max_length=4000, default="")
    image_url = serializers.URLField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        text = (attrs.get("text") or "").strip()
        image_url = (attrs.get("image_url") or "").strip()
        if not text and not image_url:
            raise serializers.ValidationError("text or image_url is required")
        attrs["text"] = text
        attrs["image_url"] = image_url
        return attrs
