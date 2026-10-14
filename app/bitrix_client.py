from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BitrixError(RuntimeError):
    pass


class BitrixClient:
    """Inbound Bitrix REST webhook client (…/rest/1/xxx/)."""

    def __init__(self, webhook_url: str) -> None:
        self._base = webhook_url.rstrip("/") + "/"

    async def _call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base}{method}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=params or {})
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise BitrixError(f"bitrix request failed: {exc}") from exc

        if not isinstance(data, dict):
            raise BitrixError("bitrix invalid response")
        if data.get("error"):
            raise BitrixError(
                f"{data.get('error')}: {data.get('error_description') or data.get('error')}"
            )
        return data.get("result")

    async def get_deal(self, deal_id: str) -> dict[str, Any]:
        result = await self._call("crm.deal.get", {"ID": deal_id})
        if not isinstance(result, dict):
            raise BitrixError(f"deal not found: {deal_id}")
        return result

    async def get_contact_phone(self, contact_id: str) -> str | None:
        if not contact_id or contact_id in {"0", "None"}:
            return None
        result = await self._call("crm.contact.get", {"ID": contact_id})
        if not isinstance(result, dict):
            return None

        phones = result.get("PHONE") or []
        if not isinstance(phones, list) or not phones:
            return None

        for item in phones:
            if isinstance(item, dict) and item.get("VALUE_TYPE") == "MOBILE" and item.get("VALUE"):
                return str(item["VALUE"]).strip()

        first = phones[0]
        if isinstance(first, dict) and first.get("VALUE"):
            return str(first["VALUE"]).strip()
        return None
