"""
Electricity Maps HTTP client (latest carbon intensity, power breakdown, history).

Uses ``auth-token`` header authentication. Responses are cached in Redis (5 minutes).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.services.carbon_constants import MVP_CARBON_ZONES
from app.services.http_retry import with_http_retries
from app.services.redis_cache import cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

CACHE_TTL_SEC = 300


class ElectricityMapsClient:
    """
    Async client for Electricity Maps public API.

    Base URL defaults to free tier or paid ``/v3`` host based on settings.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_sec: float = 45.0,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.electricity_maps_api_key
        self._root = (base_url or settings.electricity_maps_api_root).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._root + "/",
            timeout=timeout_sec,
            headers=self._auth_headers(),
        )

    def _auth_headers(self) -> dict[str, str]:
        if not self._api_key:
            logger.warning("Electricity Maps API key is empty; requests may fail.")
        return {"auth-token": self._api_key}

    async def aclose(self) -> None:
        await self._client.aclose()

    def mvp_zones(self) -> tuple[str, ...]:
        """Configured target balancing zones for MVP ingestion."""
        return MVP_CARBON_ZONES

    async def get_carbon_intensity(self, zone: str) -> dict[str, Any]:
        """
        GET ``carbon-intensity/latest`` for ``zone``.

        Returns a normalized dict: ``carbonIntensity`` (gCO2eq/kWh), ``datetime``, ``zone``,
        plus raw ``_raw`` for debugging.
        """
        cache_key = f"em:ci:latest:{zone}"
        cached = await cache_get_json(cache_key)
        if cached is not None:
            return cached

        async def _do() -> httpx.Response:
            return await self._client.get(
                "carbon-intensity/latest",
                params={"zone": zone},
            )

        resp = await with_http_retries(
            _do,
            f"electricity_maps.get_carbon_intensity({zone})",
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        normalized = self._normalize_latest(data, zone)
        normalized["_raw"] = data
        await cache_set_json(cache_key, normalized, CACHE_TTL_SEC)
        return normalized

    async def get_power_breakdown(self, zone: str) -> dict[str, Any]:
        """
        GET ``power-breakdown/latest`` for ``zone``.

        Returns JSON including ``powerConsumptionBreakdown`` keyed by source
        (e.g. wind, solar, gas, coal).
        """
        cache_key = f"em:pb:latest:{zone}"
        cached = await cache_get_json(cache_key)
        if cached is not None:
            return cached

        async def _do() -> httpx.Response:
            return await self._client.get(
                "power-breakdown/latest",
                params={"zone": zone},
            )

        resp = await with_http_retries(
            _do,
            f"electricity_maps.get_power_breakdown({zone})",
        )
        resp.raise_for_status()
        data = resp.json()
        await cache_set_json(cache_key, data, CACHE_TTL_SEC)
        return data

    async def get_carbon_intensity_history(
        self,
        zone: str,
        start: datetime,
        end: datetime,
    ) -> list[dict[str, Any]]:
        """
        Historical carbon intensity between ``start`` and ``end`` (timezone-aware).

        Uses ``carbon-intensity/past-range`` (v3-compatible path). Free tier may not expose
        this endpoint; callers should handle ``HTTPStatusError``.
        """
        start_s = start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        end_s = end.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        cache_key = f"em:ci:hist:{zone}:{start_s}:{end_s}"
        cached = await cache_get_json(cache_key)
        if isinstance(cached, list):
            return cached

        async def _do() -> httpx.Response:
            return await self._client.get(
                "carbon-intensity/past-range",
                params={"zone": zone, "start": start_s, "end": end_s},
            )

        resp = await with_http_retries(
            _do,
            f"electricity_maps.get_carbon_intensity_history({zone})",
        )
        resp.raise_for_status()
        payload = resp.json()
        history = self._extract_history_list(payload)
        await cache_set_json(cache_key, history, CACHE_TTL_SEC)
        return history

    @staticmethod
    def _normalize_latest(payload: dict[str, Any], zone: str) -> dict[str, Any]:
        """Map heterogeneous Electricity Maps payloads to a stable shape."""
        ci = payload.get("carbonIntensity")
        if ci is None and isinstance(payload.get("carbonIntensityUnit"), str):
            ci = payload.get("value")
        if isinstance(ci, dict):
            carbon = ci.get("carbonIntensity") or ci.get("value")
            dt_raw = ci.get("datetime") or ci.get("date")
        else:
            carbon = ci
            dt_raw = payload.get("datetime") or payload.get("updatedAt")
        out: dict[str, Any] = {
            "carbonIntensity": carbon,
            "datetime": dt_raw,
            "zone": payload.get("zone") or zone,
        }
        return out

    @staticmethod
    def _extract_history_list(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("data", "carbonIntensity", "history"):
                block = payload.get(key)
                if isinstance(block, list):
                    return block
            zones = payload.get("zones")
            if isinstance(zones, dict):
                nested = next(iter(zones.values()), None)
                if isinstance(nested, list):
                    return nested
        return []
