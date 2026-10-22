from __future__ import annotations

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from admin_backend.api.auth import hash_token, issue_jwt
from admin_backend.api.models import AdminClient, Notification
from admin_backend.api.serializers import (
    AuthTokenSerializer,
    ManualSendSerializer,
    NotificationSerializer,
)
from admin_backend.api.services import send_manual_message


class AuthTokenView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data["name"]
        raw_token = serializer.validated_data["token"]
        token_hash = hash_token(raw_token)

        client = AdminClient.objects.filter(
            name=name,
            token_hash=token_hash,
            is_active=True,
        ).first()
        if client is None:
            return Response({"detail": "invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({"access_token": issue_jwt(client), "token_type": "Bearer"})


class NotificationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    queryset = Notification.objects.all().order_by("-created_at")


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
