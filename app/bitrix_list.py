from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_UNICODE_ESCAPE_RE = re.compile(r"\\U([0-9A-Fa-f]{8})")
_PLACEHOLDER_RE = re.compile(r"\{([a-z_]+)\}")


@dataclass(frozen=True)
class ListTemplateHit:
    text: str
    iblock_id: str
    photo_url: str | None = None


def decode_list_template(raw: str) -> str:
    """Decode Bitrix-list style escapes: \\Uxxxxxxxx and \\n / \\r."""
    text = _UNICODE_ESCAPE_RE.sub(lambda m: chr(int(m.group(1), 16)), raw)
    text = (
        text.replace("\\r\\n", "\n")
        .replace("\\n\\r", "\n")
        .replace("\\n", "\n")
        .replace("\\r", "\n")
    )
    return text


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


def find_element_by_name(
    elements: list[dict[str, Any]],
    stage_name: str,
) -> dict[str, Any] | None:
    wanted = stage_name.strip().lower()
    for element in elements:
        title = str(element.get("NAME") or "").strip()
        if title.lower() == wanted:
            return element
    return None


def template_from_element(
    element: dict[str, Any],
    *,
    template_property: str,
    photo_property: str | None = None,
) -> tuple[str, str | None] | None:
    raw = property_first_value(element, template_property)
    if not raw:
        return None
    text = decode_list_template(raw)
    photo_url = None
    if photo_property:
        photo_url = property_first_value(element, photo_property)
        if photo_url:
            text = f"{text.rstrip()}\n\n{photo_url}"
    return text, photo_url


def find_list_template(
    elements: list[dict[str, Any]],
    *,
    stage_name: str,
    property_code: str,
    iblock_id: str,
    photo_property: str | None = None,
) -> ListTemplateHit | None:
    element = find_element_by_name(elements, stage_name)
    if element is None:
        return None
    built = template_from_element(
        element,
        template_property=property_code,
        photo_property=photo_property,
    )
    if built is None:
        logger.info(
            "bitrix_list_template_empty stage_name=%s property=%s iblock_id=%s",
            stage_name,
            property_code,
            iblock_id,
        )
        return None
    text, photo_url = built
    return ListTemplateHit(text=text, iblock_id=iblock_id, photo_url=photo_url)


def fill_placeholders(template: str, values: dict[str, Any]) -> str:
    """Replace {name} only for known keys; unknown tokens left as-is."""

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            return match.group(0)
        return str(values.get(key) or "").strip()

    return _PLACEHOLDER_RE.sub(repl, template)
