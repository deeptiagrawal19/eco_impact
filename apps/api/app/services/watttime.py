"""
WattTime v3 API client: login (Basic) → Bearer token, MOER signals, history, forecast.

Tokens are cached in-process with an expiry buffer; HTTP responses are cached in Redis (2 minutes).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.services.http_retry import with_http_retries
from app.services.redis_cache import cache_get_json, cache_set_json

CACHE_TTL_SEC = 120

# Map Electricity Maps zones to WattTime ``region`` query values (best-effort).
ELECTRICITY_MAPS_TO_WATTTIME: dict[str, str] = {
    "US-CAL-CISO": "CAISO",
    "US-NY-NYIS": "NYISO",
    "US-MIDA-PJM": "PJM",
    "DE": "DE",
    "GB": "UK",
    "FR": "FR",
    "IE": "IE",
    "SE": "SE",
    "NL": "NL",
}


def map_em_zone_to_watttime(electricity_maps_zone: str) -> str | None:
    """Return WattTime ``region`` slug for an Electricity Maps ``zone``, if known."""
    return ELECTRICITY_MAPS_TO_WATTTIME.get(electricity_maps_zone)


class WattTimeClient:
    """Async WattTime API v3 client with automatic token refresh."""

    def __init__(
        self,
        *,
        username: str | None = None,
        password: str | None = None,
        base_url: str | None = None,
        timeout_sec: float = 45.0,
    ) -> None:
        self._username = username if username is not None else settings.watttime_username
        self._password = password if password is not None else settings.watttime_password
        self._base = (base_url or settings.watttime_base_url).rstrip("/")
        self._token: str | None = None
        self._token_valid_until: datetime | None = None
        self._client = httpx.AsyncClient(timeout=timeout_sec)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _ensure_token(self) -> str:
        """Return a non-expired Bearer token, re-authenticating when needed."""
        now = datetime.now(timezone.utc)
        if (
            self._token
            and self._token_valid_until
            and now < self._token_valid_until - timedelta(minutes=2)
        ):
            return self._token

        if not settings.is_watttime_configured:
            raise RuntimeError("WattTime is not configured (optional fallback disabled).")
        if not self._username or not self._password:
            raise RuntimeError("WATTTIME_USERNAME and WATTTIME_PASSWORD must be set for WattTime.")

        async def _login() -> httpx.Response:
            return await self._client.post(
                f"{self._base}/login",
                auth=httpx.BasicAuth(self._username, self._password),
            )

        resp = await with_http_retries(_login, "watttime.login")
        resp.raise_for_status()
        body = resp.json()
        token = body.get("token")
        if not token:
            raise RuntimeError(f"WattTime login returned no token: {body}")
        self._token = token
        self._token_valid_until = now + timedelta(minutes=25)
        return self._token

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    async def get_realtime_emissions(self, region: str) -> dict[str, Any]:
        """
        GET ``/v3/signal-index`` with ``signal_type=co2_moer``.

        Returns parsed JSON; typical ``data`` entries include ``value`` (gCO2eq/MWh) and
        ``point_time``.
        """
        cache_key = f"wt:rt:{region}"
        cached = await cache_get_json(cache_key)
        if cached is not None:
            return cached

        token = await self._ensure_token()

        async def _call() -> httpx.Response:
            return await self._client.get(
                f"{self._base}/v3/signal-index",
                headers=self._auth_headers(token),
                params={"region": region, "signal_type": "co2_moer"},
            )

        resp = await with_http_retries(_call, f"watttime.signal_index({region})")
        if resp.status_code == 401:
            self._token = None
            token = await self._ensure_token()

            async def _retry() -> httpx.Response:
                return await self._client.get(
                    f"{self._base}/v3/signal-index",
                    headers=self._auth_headers(token),
                    params={"region": region, "signal_type": "co2_moer"},
                )

            resp = await with_http_retries(_retry, f"watttime.signal_index_retry({region})")
        resp.raise_for_status()
        data = resp.json()
        await cache_set_json(cache_key, data, CACHE_TTL_SEC)
        return data

    async def get_historical_emissions(self, region: str, start: str, end: str) -> list[dict[str, Any]]:
        """
        GET ``/v3/historical`` with ISO8601 ``start`` / ``end`` strings.

        Normalizes payload to a list of points when the API wraps series under ``data``.
        """
        cache_key = f"wt:hist:{region}:{start}:{end}"
        cached = await cache_get_json(cache_key)
        if isinstance(cached, list):
            return cached

        token = await self._ensure_token()

        async def _call() -> httpx.Response:
            return await self._client.get(
                f"{self._base}/v3/historical",
                headers=self._auth_headers(token),
                params={
                    "region": region,
                    "start": start,
                    "end": end,
                    "signal_type": "co2_moer",
                },
            )

        resp = await with_http_retries(_call, f"watttime.historical({region})")
        if resp.status_code == 401:
            self._token = None
            token = await self._ensure_token()

            async def _retry() -> httpx.Response:
                return await self._client.get(
                    f"{self._base}/v3/historical",
                    headers=self._auth_headers(token),
                    params={
                        "region": region,
                        "start": start,
                        "end": end,
                        "signal_type": "co2_moer",
                    },
                )

            resp = await with_http_retries(_retry, f"watttime.historical_retry({region})")
        resp.raise_for_status()
        series = self._extract_series(resp.json())
        await cache_set_json(cache_key, series, CACHE_TTL_SEC)
        return series

    async def get_forecast(self, region: str) -> list[dict[str, Any]]:
        """GET ``/v3/forecast`` for ``co2_moer``."""
        cache_key = f"wt:fc:{region}"
        cached = await cache_get_json(cache_key)
        if isinstance(cached, list):
            return cached

        token = await self._ensure_token()

        async def _call() -> httpx.Response:
            return await self._client.get(
                f"{self._base}/v3/forecast",
                headers=self._auth_headers(token),
                params={"region": region, "signal_type": "co2_moer"},
            )

        resp = await with_http_retries(_call, f"watttime.forecast({region})")
        if resp.status_code == 401:
            self._token = None
            token = await self._ensure_token()

            async def _retry() -> httpx.Response:
                return await self._client.get(
                    f"{self._base}/v3/forecast",
                    headers=self._auth_headers(token),
                    params={"region": region, "signal_type": "co2_moer"},
                )

            resp = await with_http_retries(_retry, f"watttime.forecast_retry({region})")
        resp.raise_for_status()
        series = self._extract_series(resp.json())
        await cache_set_json(cache_key, series, CACHE_TTL_SEC)
        return series

    @staticmethod
    def _extract_series(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            data = payload.get("data")
            if isinstance(data, list):
                return data
        return []
