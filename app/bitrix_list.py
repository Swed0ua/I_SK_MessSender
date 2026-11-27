from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_UNICODE_ESCAPE_RE = re.compile(r"\\U([0-9A-Fa-f]{8})")
_PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")


def decode_list_template(raw: str) -> str:
    """Decode Bitrix-list style escapes: \\Uxxxxxxxx and \\n."""
    text = _UNICODE_ESCAPE_RE.sub(lambda m: chr(int(m.group(1), 16)), raw)
    return text.replace("\\n", "\n")


def property_first_value(element: dict[str, Any], property_code: str) -> str | None:
    raw = element.get(property_code)
    if raw is None:
        return None
    if isinstance(raw, dict):
        if not raw:
            return None
        value = next(iter(raw.values()))
        text = str(value).strip() if value is not None else ""
        return text or None
    text = str(raw).strip()
    return text or None


def stage_name_for_id(stages: list[dict[str, Any]], stage_id: str) -> str | None:
    wanted = stage_id.strip()
    for row in stages:
        status_id = str(row.get("STATUS_ID") or "").strip()
        if status_id == wanted:
            name = str(row.get("NAME") or "").strip()
            return name or None
    return None


def find_list_template(
    elements: list[dict[str, Any]],
    *,
    stage_name: str,
    property_code: str,
) -> str | None:
    wanted = stage_name.strip().lower()
    for element in elements:
        title = str(element.get("NAME") or "").strip()
        if title.lower() != wanted:
            continue
        raw = property_first_value(element, property_code)
        if not raw:
            logger.info(
                "bitrix_list_template_empty stage_name=%s property=%s",
                stage_name,
                property_code,
            )
            return None
        return decode_list_template(raw)
    return None


def fill_placeholders(template: str, values: dict[str, Any]) -> str:
    """Replace {name} only for known keys; unknown tokens left as-is."""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            return match.group(0)
        return str(values.get(key) or "").strip()

    return _PLACEHOLDER_RE.sub(repl, template)
