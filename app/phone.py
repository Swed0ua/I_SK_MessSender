from __future__ import annotations

import re

_NON_DIGIT = re.compile(r"\D+")


class PhoneError(ValueError):
    pass


def normalize_phone(raw: str) -> str:
    """Normalize UA phone to E.164 (+380XXXXXXXXX)."""
    if raw is None or not str(raw).strip():
        raise PhoneError("phone is required")

    digits = _NON_DIGIT.sub("", str(raw).strip())

    if digits.startswith("380") and len(digits) == 12:
        return f"+{digits}"

    if digits.startswith("0") and len(digits) == 10:
        return f"+380{digits[1:]}"

    if len(digits) == 9 and digits[0] in "345679":
        return f"+380{digits}"

    raise PhoneError(f"cannot normalize phone: {raw!r}")
