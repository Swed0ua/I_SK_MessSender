from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env: {name}")
    return value


def _database_from_url(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RuntimeError("DATABASE_URL must be postgresql://...")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": (parsed.path or "/").lstrip("/") or "notifications",
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "127.0.0.1",
        "PORT": str(parsed.port or 5432),
    }


SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "").strip() or _require("API_KEY")
DEBUG = os.getenv("ADMIN_DEBUG", "false").lower() in {"1", "true", "yes"}
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ADMIN_ALLOWED_HOSTS", "*").split(",") if h.strip()]

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "rest_framework",
    "admin_backend.api.apps.ApiConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "admin_backend.urls"
WSGI_APPLICATION = "admin_backend.wsgi.application"

DATABASES = {"default": _database_from_url(_require("DATABASE_URL"))}

LANGUAGE_CODE = "uk"
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ADMIN_JWT_SECRET = os.getenv("ADMIN_JWT_SECRET", "").strip() or SECRET_KEY
ADMIN_JWT_TTL_SECONDS = int(os.getenv("ADMIN_JWT_TTL_SECONDS", "86400"))
ADMIN_HOST = os.getenv("ADMIN_HOST", "127.0.0.1").strip() or "127.0.0.1"
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "8081"))
MYCHATBOT_MAILING_WEBHOOK_URL = os.getenv("MYCHATBOT_MAILING_WEBHOOK_URL", "").strip()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "admin_backend.api.auth.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "UNAUTHENTICATED_USER": None,
}
