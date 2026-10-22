from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.urls import include, path

_WEB_ADMIN = Path(settings.BASE_DIR) / "web_admin"
_STATIC_FILES = {
    "logo-background.svg": "image/svg+xml",
}


def admin_ui(_request):
    html = (_WEB_ADMIN / "index.html").read_text(encoding="utf-8")
    return HttpResponse(html, content_type="text/html; charset=utf-8")


def admin_asset(_request, name: str):
    content_type = _STATIC_FILES.get(name)
    if content_type is None:
        raise Http404()
    path = _WEB_ADMIN / name
    if not path.is_file():
        raise Http404()
    return FileResponse(path.open("rb"), content_type=content_type)


urlpatterns = [
    path("", admin_ui, name="admin-ui"),
    path("assets/<str:name>", admin_asset, name="admin-asset"),
    path("api/v1/", include("admin_backend.api.urls")),
]
