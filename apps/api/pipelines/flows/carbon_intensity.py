"""
Prefect flow: fetch grid carbon for MVP regions (Electricity Maps, then WattTime fallback)
and upsert into ``carbon_intensity_readings``. Typical schedule: every 15 minutes UTC.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from prefect import flow, task
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.tables import CarbonIntensityReading
from app.services.carbon_constants import MVP_CARBON_ZONES
from app.services.electricity_maps import ElectricityMapsClient
from app.services.watttime import WattTimeClient, map_em_zone_to_watttime

logger = logging.getLogger(__name__)


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    s = str(value).replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _normalize_breakdown_percentages(
    breakdown: dict[str, Any] | None,
) -> tuple[float | None, float | None]:
    """
    Estimate fossil / renewable shares from Electricity Maps power breakdown.

    Values may be ratios (0–1) or already percent (0–100).
    """
    if not breakdown or not isinstance(breakdown, dict):
        return None, None
    pb = breakdown.get("powerConsumptionBreakdown")
    if not isinstance(pb, dict):
        return None, None

    renewable_keys = frozenset({"wind", "solar", "hydro", "biomass", "geothermal"})
    fossil_keys = frozenset({"coal", "gas", "oil", "fossil", "unknown"})

    def _get(name: str) -> float:
        v = pb.get(name)
        if v is None:
            return 0.0
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    ren = sum(_get(k) for k in renewable_keys if k in pb)
    fos = sum(_get(k) for k in fossil_keys if k in pb)
    total = ren + fos
    if total <= 0:
        return None, None
    if total <= 1.05:
        ren *= 100.0
        fos *= 100.0
    return fos, ren


@task(name="fetch_carbon_zone", retries=3, retry_delay_seconds=60)
async def fetch_carbon_zone(zone: str) -> dict[str, Any]:
    """
    Fetch latest carbon for one Electricity Maps ``zone``.

    Returns a dict with ``ok: bool``; on success includes either Electricity Maps or
    WattTime payloads.
    """
    em = ElectricityMapsClient()
    wt: WattTimeClient | None = None
    try:
        try:
            ci = await em.get_carbon_intensity(zone)
            breakdown: dict[str, Any] | None = None
            try:
                breakdown = await em.get_power_breakdown(zone)
            except Exception as br_exc:  # noqa: BLE001
                logger.warning("Power breakdown failed zone=%s: %s", zone, br_exc)
            return {
                "ok": True,
                "zone": zone,
                "vendor": "electricity_maps",
                "ci": ci,
                "breakdown": breakdown,
            }
        except Exception as em_exc:  # noqa: BLE001
            logger.warning("Electricity Maps failed zone=%s: %s", zone, em_exc)
            if not settings.is_watttime_configured:
                logger.debug(
                    "WattTime skipped for zone=%s (placeholder or missing credentials)",
                    zone,
                )
                return {"ok": False, "zone": zone, "error": str(em_exc)}
            wt_region = map_em_zone_to_watttime(zone)
            if not wt_region:
                return {
                    "ok": False,
                    "zone": zone,
                    "error": f"no WattTime mapping after EM error: {em_exc}",
                }
            wt = WattTimeClient()
            try:
                sig = await wt.get_realtime_emissions(wt_region)
                return {
                    "ok": True,
                    "zone": zone,
                    "vendor": "watttime",
                    "wt_region": wt_region,
                    "sig": sig,
                }
            except Exception as wt_exc:  # noqa: BLE001
                logger.warning(
                    "WattTime fallback failed zone=%s (using no data for this run): %s",
                    zone,
                    wt_exc,
                )
                return {"ok": False, "zone": zone, "error": str(wt_exc)}
    finally:
        await em.aclose()
        if wt is not None:
            await wt.aclose()


@task(name="transform_carbon_rows", retries=3, retry_delay_seconds=30)
def transform_carbon_rows(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert vendor payloads into row dicts for ``carbon_intensity_readings``."""
    rows: list[dict[str, Any]] = []
    for item in raw:
        if not item.get("ok"):
            continue
        zone = item["zone"]
        vendor = item.get("vendor")
        if vendor == "electricity_maps":
            ci = item["ci"]
            ts_raw = ci.get("datetime")
            if not ts_raw:
                logger.warning("Skipping EM row without datetime zone=%s", zone)
                continue
            try:
                t = _parse_ts(ts_raw)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Bad EM datetime zone=%s: %s", zone, exc)
                continue
            avg = ci.get("carbonIntensity")
            avg_f = float(avg) if avg is not None else None
            fos_pct, ren_pct = _normalize_breakdown_percentages(item.get("breakdown"))
            rows.append(
                {
                    "time": t,
                    "region": zone,
                    "carbon_intensity_avg": avg_f,
                    "carbon_intensity_marginal": None,
                    "fossil_fuel_percentage": fos_pct,
                    "renewable_percentage": ren_pct,
                    "source": "electricity_maps",
                }
            )
        elif vendor == "watttime":
            sig = item["sig"]
            data = sig.get("data") if isinstance(sig, dict) else None
            if not isinstance(data, list) or not data:
                logger.warning("WattTime payload missing data list zone=%s", zone)
                continue
            point = max(data, key=lambda p: str(p.get("point_time") or ""))
            t_raw = point.get("point_time")
            val = point.get("value")
            if t_raw is None or val is None:
                continue
            try:
                t = _parse_ts(t_raw)
                moer = float(val)
            except Exception as exc:  # noqa: BLE001
                logger.warning("WattTime parse error zone=%s: %s", zone, exc)
                continue
            rows.append(
                {
                    "time": t,
                    "region": zone,
                    "carbon_intensity_avg": moer,
                    "carbon_intensity_marginal": moer,
                    "fossil_fuel_percentage": None,
                    "renewable_percentage": None,
                    "source": "watttime",
                }
            )
    return rows


@task(name="load_carbon_rows", retries=3, retry_delay_seconds=60)
async def load_carbon_rows(row_dicts: list[dict[str, Any]]) -> int:
    """Insert transformed rows with ``ON CONFLICT DO NOTHING`` on the hypertable PK."""
    if not row_dicts:
        return 0
    async with async_session_maker() as session:
        for row in row_dicts:
            stmt = (
                pg_insert(CarbonIntensityReading)
                .values(**row)
                .on_conflict_do_nothing(
                    index_elements=["time", "region", "source"],
                )
            )
            await session.execute(stmt)
        await session.commit()
    return len(row_dicts)


@flow(name="fetch_carbon_intensity_all_regions", log_prints=True)
async def fetch_carbon_intensity_all_regions() -> dict[str, Any]:
    """
    ETL all MVP regions: fetch → transform → load.

    Per-region fetch errors are logged; the flow continues and returns aggregate counts.
    """
    raw: list[dict[str, Any]] = []
    for zone in MVP_CARBON_ZONES:
        raw.append(await fetch_carbon_zone(zone))

    successes = sum(1 for r in raw if r.get("ok"))
    failures = sum(1 for r in raw if not r.get("ok"))
    logger.info("carbon fetch complete successes=%s failures=%s", successes, failures)

    row_dicts = transform_carbon_rows(raw)
    inserted = await load_carbon_rows(row_dicts)
    logger.info("carbon load rows=%s (attempted inserts)", inserted)

    return {
        "zones_total": len(MVP_CARBON_ZONES),
        "fetch_success": successes,
        "fetch_failed": failures,
        "rows_insert_attempted": inserted,
    }


if __name__ == "__main__":
    import asyncio

    asyncio.run(fetch_carbon_intensity_all_regions())
