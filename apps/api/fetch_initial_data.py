"""
Fetch latest carbon intensity from Electricity Maps (zones: US-CAL-CISO, US-NY-NYIS, DE, GB, FR)
and store rows in the database.

Needs ELECTRICITY_MAPS_API_KEY; if unset, logs a warning and skips (seed data may still exist).

Run from apps/api: ``uv run python fetch_initial_data.py`` or ``python fetch_initial_data.py``.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.tables import CarbonIntensityReading
from app.services.electricity_maps import ElectricityMapsClient

ZONES = ("US-CAL-CISO", "US-NY-NYIS", "DE", "GB", "FR")

logger = logging.getLogger(__name__)


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    s = str(value).replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def fetch_and_store() -> int:
    if not settings.electricity_maps_api_key.strip():
        logger.warning(
            "ELECTRICITY_MAPS_API_KEY is unset; skipping live fetch. "
            "Seed data still provides grid history via source=seed.",
        )
        return 0

    client = ElectricityMapsClient()
    saved = 0
    try:
        async with async_session_maker() as session:
            for zone in ZONES:
                try:
                    ci = await client.get_carbon_intensity(zone)
                    ts_raw = ci.get("datetime")
                    if not ts_raw:
                        logger.warning("No datetime in EM response for %s", zone)
                        continue
                    t = _parse_ts(ts_raw)
                    carbon = ci.get("carbonIntensity")
                    avg = float(carbon) if carbon is not None else None
                    row = CarbonIntensityReading(
                        time=t,
                        region=zone,
                        carbon_intensity_avg=avg,
                        carbon_intensity_marginal=None,
                        fossil_fuel_percentage=None,
                        renewable_percentage=None,
                        source="electricity_maps",
                    )
                    session.add(row)
                    saved += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Electricity Maps fetch failed for %s: %s", zone, exc)
            await session.commit()
    finally:
        await client.aclose()
    return saved


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    n = asyncio.run(fetch_and_store())
    logger.info("Saved %s Electricity Maps reading(s).", n)


if __name__ == "__main__":
    main()
