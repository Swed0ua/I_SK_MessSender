from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import QuerySet
from rest_framework.exceptions import ValidationError

from app.phone import PhoneError, normalize_phone

ALLOWED_STATUSES = frozenset({"pending", "sent", "failed", "skipped"})
STATUS_ALIASES = {
    "success": "sent",
    "successful": "sent",
    "ok": "sent",
    "unsuccessful": "failed",
    "error": "failed",
}


def _tz() -> ZoneInfo:
    return ZoneInfo(settings.TIME_ZONE)


def _parse_date(raw: str, field: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError({field: "use YYYY-MM-DD"}) from exc


def _parse_datetime_or_date(raw: str, field: str) -> datetime:
    """Accept YYYY-MM-DD or ISO datetime; return timezone-aware datetime."""
    tz = _tz()
    try:
        if "T" in raw or " " in raw:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            return dt
        return datetime.combine(date.fromisoformat(raw), time.min, tzinfo=tz)
    except ValueError as exc:
        raise ValidationError({field: "use YYYY-MM-DD or ISO datetime"}) from exc


def _resolve_status(raw: str) -> str:
    key = raw.strip().lower()
    status = STATUS_ALIASES.get(key, key)
    if status not in ALLOWED_STATUSES:
        raise ValidationError(
            {"status": f"must be one of: {', '.join(sorted(ALLOWED_STATUSES))}"}
        )
    return status


def apply_notification_filters(qs: QuerySet, params: Any, *, force_phone: str | None = None) -> QuerySet:
    """Apply list filters from query params. Raises ValidationError on bad input."""
    status_raw = params.get("status")
    if status_raw:
        qs = qs.filter(status=_resolve_status(str(status_raw)))

    phone_raw = force_phone if force_phone is not None else params.get("phone")
    if phone_raw:
        try:
            qs = qs.filter(phone=normalize_phone(str(phone_raw)))
        except PhoneError as exc:
            raise ValidationError({"phone": str(exc)}) from exc

    date_raw = params.get("date")
    hour_raw = params.get("hour")
    date_from = params.get("date_from")
    date_to = params.get("date_to")

    if date_raw and (date_from or date_to):
        raise ValidationError({"date": "do not combine with date_from/date_to"})

    if hour_raw is not None and hour_raw != "" and not date_raw:
        raise ValidationError({"hour": "requires date=YYYY-MM-DD"})

    if date_raw:
        day = _parse_date(str(date_raw), "date")
        tz = _tz()
        if hour_raw is not None and str(hour_raw).strip() != "":
            try:
                hour = int(str(hour_raw))
            except ValueError as exc:
                raise ValidationError({"hour": "must be 0-23"}) from exc
            if hour < 0 or hour > 23:
                raise ValidationError({"hour": "must be 0-23"})
            start = datetime.combine(day, time(hour=hour), tzinfo=tz)
            end = start + timedelta(hours=1)
        else:
            start = datetime.combine(day, time.min, tzinfo=tz)
            end = start + timedelta(days=1)
        qs = qs.filter(created_at__gte=start, created_at__lt=end)

    if date_from:
        qs = qs.filter(created_at__gte=_parse_datetime_or_date(str(date_from), "date_from"))
    if date_to:
        # Inclusive calendar day when date-only; exclusive upper bound for ISO datetime as given.
        raw = str(date_to)
        if "T" not in raw and " " not in raw:
            day = _parse_date(raw, "date_to")
            end = datetime.combine(day, time.min, tzinfo=_tz()) + timedelta(days=1)
            qs = qs.filter(created_at__lt=end)
        else:
            qs = qs.filter(created_at__lte=_parse_datetime_or_date(raw, "date_to"))

    return qs
