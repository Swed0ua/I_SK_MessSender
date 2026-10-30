from __future__ import annotations

import io
import logging
import mimetypes
from typing import Any

from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})
MAX_IMAGE_BYTES = 8 * 1024 * 1024


def public_image_url(file_id: str) -> str:
    return f"https://lh3.googleusercontent.com/d/{file_id}"


def _credentials() -> Credentials:
    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET
    refresh_token = settings.GOOGLE_REFRESH_TOKEN
    if not client_id or not client_secret or not refresh_token:
        raise RuntimeError("Google Drive OAuth is not configured")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def _drive_service():
    return build("drive", "v3", credentials=_credentials(), cache_discovery=False)


def upload_public_image(*, filename: str, data: bytes, content_type: str | None) -> dict[str, Any]:
    if not data:
        raise ValueError("empty file")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError(f"file too large (max {MAX_IMAGE_BYTES // (1024 * 1024)} MB)")

    mime = (content_type or mimetypes.guess_type(filename)[0] or "").split(";")[0].strip().lower()
    if mime not in ALLOWED_IMAGE_TYPES:
        raise ValueError("only jpeg, png, webp, gif allowed")

    folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
    if not folder_id:
        raise RuntimeError("GOOGLE_DRIVE_FOLDER_ID is not configured")

    service = _drive_service()
    meta: dict[str, Any] = {"name": filename or "upload.jpg", "parents": [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime, resumable=False)
    created = (
        service.files()
        .create(body=meta, media_body=media, fields="id,name,mimeType")
        .execute()
    )
    file_id = created["id"]

    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
        fields="id",
    ).execute()

    url = public_image_url(file_id)
    logger.info("drive_uploaded id=%s name=%s", file_id, created.get("name"))
    return {"file_id": file_id, "url": url, "name": created.get("name"), "mime_type": mime}
