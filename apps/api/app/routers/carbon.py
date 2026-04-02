"""
Carbon intensity HTTP API (reads from TimescaleDB ``carbon_intensity_readings``).

Data is populated by the Prefect ETL (Electricity Maps primary, WattTime fallback).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from app.models.tables import CarbonIntensityReading
from app.schemas.carbon import (
    CarbonComparisonResponse,
    CarbonHistoryResponse,
    CarbonLatestResponse,
    CarbonReadingOut,
    CarbonRegionsResponse,
    ComparisonRow,
    RegionLatestOut,
)
from app.services.carbon_constants import MVP_CARBON_ZONES

router = APIRouter(prefix="/api/carbon", tags=["carbon"])


@router.get("/latest", response_model=CarbonLatestResponse)
async def latest_for_region(
    region: str = Query(..., description="Electricity Maps zone key"),
    session: AsyncSession = Depends(get_db_session),
) -> CarbonLatestResponse:
    """Return the newest stored reading for ``region``."""
    stmt = (
        select(CarbonIntensityReading)
        .where(CarbonIntensityReading.region == region)
        .order_by(desc(CarbonIntensityReading.time))
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return CarbonLatestResponse(
        region=region,
        reading=CarbonReadingOut.model_validate(row) if row else None,
    )


@router.get("/history", response_model=CarbonHistoryResponse)
async def history_for_region(
    region: str = Query(...),
    hours: int = Query(24, ge=1, le=168),
    session: AsyncSession = Depends(get_db_session),
) -> CarbonHistoryResponse:
    """Return readings for ``region`` within the last ``hours`` (default 24)."""
    start = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = (
        select(CarbonIntensityReading)
        .where(
            CarbonIntensityReading.region == region,
            CarbonIntensityReading.time >= start,
        )
        .order_by(CarbonIntensityReading.time.asc())
    )
    result = await session.execute(stmt)
    rows = list(result.scalars().all())
    return CarbonHistoryResponse(
        region=region,
        hours=hours,
        readings=[CarbonReadingOut.model_validate(r) for r in rows],
    )


@router.get("/regions", response_model=CarbonRegionsResponse)
async def regions_overview(
    session: AsyncSession = Depends(get_db_session),
) -> CarbonRegionsResponse:
    """MVP zones with each zone's latest stored reading (any source)."""
    out: list[RegionLatestOut] = []
    for zone in MVP_CARBON_ZONES:
        stmt = (
            select(CarbonIntensityReading)
            .where(CarbonIntensityReading.region == zone)
            .order_by(desc(CarbonIntensityReading.time))
            .limit(1)
        )
        res = await session.execute(stmt)
        row = res.scalar_one_or_none()
        out.append(
            RegionLatestOut(
                region=zone,
                reading=CarbonReadingOut.model_validate(row) if row else None,
            )
        )
    return CarbonRegionsResponse(regions=out)


@router.get("/comparison", response_model=CarbonComparisonResponse)
async def comparison(
    session: AsyncSession = Depends(get_db_session),
) -> CarbonComparisonResponse:
    """
    Compare the latest stored intensity across all MVP regions.

    Picks the newest row per region (across sources); for tie-breaking, higher ``time`` wins.
    """
    rows_out: list[ComparisonRow] = []
    for zone in MVP_CARBON_ZONES:
        stmt = (
            select(CarbonIntensityReading)
            .where(CarbonIntensityReading.region == zone)
            .order_by(desc(CarbonIntensityReading.time))
            .limit(1)
        )
        res = await session.execute(stmt)
        row = res.scalar_one_or_none()
        if row is None:
            rows_out.append(ComparisonRow(region=zone))
            continue
        rows_out.append(
            ComparisonRow(
                region=zone,
                carbon_intensity_avg=row.carbon_intensity_avg,
                carbon_intensity_marginal=row.carbon_intensity_marginal,
                source=row.source,
                time=row.time,
            )
        )
    return CarbonComparisonResponse(rows=rows_out)
