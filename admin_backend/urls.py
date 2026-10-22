from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.urls import include, path


def admin_ui(_request):
    html = (Path(settings.BASE_DIR) / "web_admin" / "index.html").read_text(encoding="utf-8")
    return HttpResponse(html, content_type="text/html; charset=utf-8")


urlpatterns = [
    path("", admin_ui, name="admin-ui"),
    path("api/v1/", include("admin_backend.api.urls")),
]
