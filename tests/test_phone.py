from __future__ import annotations

from app.phone import PhoneError, normalize_phone


def test_normalize_ua_local() -> None:
    assert normalize_phone("0501234567") == "+380501234567"
    assert normalize_phone("+38 (050) 123-45-67") == "+380501234567"
    assert normalize_phone("380501234567") == "+380501234567"


def test_normalize_invalid() -> None:
    try:
        normalize_phone("12345")
        assert False, "expected PhoneError"
    except PhoneError:
        pass


if __name__ == "__main__":
    test_normalize_ua_local()
    test_normalize_invalid()
    print("ok")
