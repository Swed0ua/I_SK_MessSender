from __future__ import annotations

from django.urls import path

from admin_backend.api.views import AuthTokenView, ManualSendView, NotificationListView

urlpatterns = [
    path("auth/token", AuthTokenView.as_view(), name="auth-token"),
    path("notifications", NotificationListView.as_view(), name="notifications-list"),
    path("notifications/send", ManualSendView.as_view(), name="notifications-send"),
]
