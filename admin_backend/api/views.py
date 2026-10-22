from __future__ import annotations

from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_backend.api.auth import (
    KIND_CLIENT,
    KIND_USER,
    hash_token,
    issue_jwt,
    verify_password,
)
from admin_backend.api.filters import apply_notification_filters
from admin_backend.api.models import AdminClient, AdminUser, Notification
from admin_backend.api.serializers import (
    AuthTokenSerializer,
    ManualSendSerializer,
    NotificationSerializer,
)
from admin_backend.api.services import send_manual_message
from app.phone import PhoneError, normalize_phone


class AuthTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data["mode"] == "user":
            user = AdminUser.objects.filter(username=data["username"], is_active=True).first()
            if user is None or not verify_password(data["password"], user.password_hash):
                return Response({"detail": "invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
            token = issue_jwt(subject_id=user.id, name=user.username, kind=KIND_USER)
            return Response({"access_token": token, "token_type": "Bearer", "kind": KIND_USER})

        token_hash = hash_token(data["token"])
        client = AdminClient.objects.filter(
            name=data["name"],
            token_hash=token_hash,
            is_active=True,
        ).first()
        if client is None:
            return Response({"detail": "invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        token = issue_jwt(subject_id=client.id, name=client.name, kind=KIND_CLIENT)
        return Response({"access_token": token, "token_type": "Bearer", "kind": KIND_CLIENT})


class NotificationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return apply_notification_filters(
            Notification.objects.all().order_by("-created_at"),
            self.request.query_params,
        )


class NotificationByPhoneView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        try:
            phone = normalize_phone(self.kwargs["phone"])
        except PhoneError as exc:
            raise ValidationError({"phone": str(exc)}) from exc
        return apply_notification_filters(
            Notification.objects.all().order_by("-created_at"),
            self.request.query_params,
            force_phone=phone,
        )


class ManualSendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ManualSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            notif = send_manual_message(
                phone_raw=serializer.validated_data["phone"],
                text=serializer.validated_data["text"],
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(
            NotificationSerializer(notif).data,
            status=status.HTTP_202_ACCEPTED if notif.status == "pending" else status.HTTP_200_OK,
        )
