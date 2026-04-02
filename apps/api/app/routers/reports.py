"""Report and pipeline-derived analytics (sustainability, hardware, YoY trends)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from app.models.tables import GPUBenchmark, SustainabilityReport
from app.schemas.reports import (
    HardwareItem,
    HardwareListResponse,
    SustainabilityComparisonResponse,
    SustainabilityComparisonRow,
    SustainabilityListResponse,
    SustainabilityReportItem,
    TrendPoint,
    TrendsResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])

# Resolved relative to apps/api (parent of app/)
_API_ROOT = Path(__file__).resolve().parent.parent.parent
_YOY_PATH = _API_ROOT / "data" / "sustainability" / "yoy_metadata.json"

MetricName = Literal["electricity", "water", "emissions", "renewable", "pue"]

_METRIC_COLUMNS: dict[str, str] = {
    "electricity": "total_electricity_gwh",
    "water": "total_water_gallons",
    "emissions": "total_emissions_mtco2e",
    "renewable": "renewable_match_percentage",
    "pue": "avg_pue",
}

_YOY_SUFFIX: dict[str, str] = {
    "electricity": "electricity_gwh_yoy_pct",
    "water": "water_gallons_yoy_pct",
    "emissions": "emissions_mtco2e_yoy_pct",
    "renewable": "renewable_pct_yoy_pct",
    "pue": "pue_yoy_pct",
}


def _load_yoy_file() -> dict[str, Any] | None:
    if not _YOY_PATH.is_file():
        return None
    try:
        return json.loads(_YOY_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read YoY metadata %s: %s", _YOY_PATH, exc)
        return None


@router.get("/sustainability", response_model=SustainabilityListResponse)
async def get_sustainability_reports(
    provider: str | None = Query(
        default=None,
        description="Filter by provider slug (e.g. google, microsoft)",
    ),
    session: AsyncSession = Depends(get_db_session),
) -> SustainabilityListResponse:
    stmt = select(SustainabilityReport).order_by(
        SustainabilityReport.provider,
        SustainabilityReport.year.desc(),
    )
    if provider:
        stmt = stmt.where(
            SustainabilityReport.provider == provider.strip().lower(),
        )
    res = await session.execute(stmt)
    rows = res.scalars().all()
    return SustainabilityListResponse(
        provider=(provider.strip().lower() if provider else None),
        reports=[
            SustainabilityReportItem(
                id=str(r.id),
                provider=r.provider,
                year=r.year,
                total_electricity_gwh=r.total_electricity_gwh,
                total_water_gallons=r.total_water_gallons,
                total_emissions_mtco2e=r.total_emissions_mtco2e,
                scope1_mtco2e=r.scope1_mtco2e,
                scope2_mtco2e=r.scope2_mtco2e,
                scope3_mtco2e=r.scope3_mtco2e,
                renewable_match_percentage=r.renewable_match_percentage,
                avg_pue=r.avg_pue,
                report_url=r.report_url,
            )
            for r in rows
        ],
    )


@router.get("/sustainability/comparison", response_model=SustainabilityComparisonResponse)
async def sustainability_comparison(
    session: AsyncSession = Depends(get_db_session),
) -> SustainabilityComparisonResponse:
    stmt = select(SustainabilityReport).order_by(
        SustainabilityReport.year,
        SustainabilityReport.provider,
    )
    res = await session.execute(stmt)
    rows = res.scalars().all()
    return SustainabilityComparisonResponse(
        rows=[
            SustainabilityComparisonRow(
                provider=r.provider,
                year=r.year,
                total_electricity_gwh=r.total_electricity_gwh,
                total_water_gallons=r.total_water_gallons,
                total_emissions_mtco2e=r.total_emissions_mtco2e,
                renewable_match_percentage=r.renewable_match_percentage,
                avg_pue=r.avg_pue,
            )
            for r in rows
        ],
    )


def _trends_from_yoy(metric: MetricName, ydoc: dict[str, Any]) -> TrendsResponse:
    suffix = _YOY_SUFFIX[metric]
    points: list[TrendPoint] = []
    byp = ydoc.get("by_provider") or {}
    if not isinstance(byp, dict):
        raise HTTPException(status_code=500, detail="Invalid YoY metadata shape")
    for prov, entries in byp.items():
        if not isinstance(entries, list):
            continue
        for ent in entries:
            if not isinstance(ent, dict) or "year" not in ent:
                continue
            yoy = ent.get(suffix)
            points.append(
                TrendPoint(
                    provider=str(prov),
                    year=int(ent["year"]),
                    yoy_pct=float(yoy) if yoy is not None else None,
                    value=None,
                )
            )
    return TrendsResponse(
        metric=metric,
        source="yoy_metadata",
        points=points,
        metadata_updated_at=str(ydoc.get("updated_at")),
    )


def _trends_computed_db_rows(
    metric: MetricName,
    rows: list[SustainabilityReport],
) -> TrendsResponse:
    col = _METRIC_COLUMNS[metric]
    by_provider: dict[str, list[SustainabilityReport]] = {}
    for r in rows:
        by_provider.setdefault(r.provider, []).append(r)
    points: list[TrendPoint] = []
    for prov, series in by_provider.items():
        series_sorted = sorted(series, key=lambda x: x.year)
        for i, r in enumerate(series_sorted):
            raw = getattr(r, col, None)
            val = float(raw) if raw is not None else None
            yoy: float | None = None
            if i > 0:
                prev_raw = getattr(series_sorted[i - 1], col, None)
                if (
                    prev_raw is not None
                    and val is not None
                    and float(prev_raw) != 0
                ):
                    yoy = round(
                        100.0 * (val - float(prev_raw)) / float(prev_raw),
                        4,
                    )
            points.append(TrendPoint(provider=prov, year=r.year, yoy_pct=yoy, value=val))
    return TrendsResponse(metric=metric, source="computed_db", points=points, metadata_updated_at=None)


@router.get("/trends", response_model=TrendsResponse)
async def report_trends(
    metric: MetricName = Query(description="Metric for YoY exposure"),
    session: AsyncSession = Depends(get_db_session),
) -> TrendsResponse:
    ydoc = _load_yoy_file()
    if ydoc and isinstance(ydoc.get("by_provider"), dict):
        try:
            return _trends_from_yoy(metric, ydoc)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falling back to DB trends: %s", exc)

    res = await session.execute(
        select(SustainabilityReport).order_by(
            SustainabilityReport.provider,
            SustainabilityReport.year,
        )
    )
    db_rows = list(res.scalars().all())
    return _trends_computed_db_rows(metric, db_rows)


@router.get("/hardware", response_model=HardwareListResponse)
async def reports_hardware(
    session: AsyncSession = Depends(get_db_session),
) -> HardwareListResponse:
    res = await session.execute(select(GPUBenchmark).order_by(GPUBenchmark.gpu_name))
    rows = res.scalars().all()
    return HardwareListResponse(
        hardware=[
            HardwareItem(
                id=str(r.id),
                gpu_name=r.gpu_name,
                tdp_watts=r.tdp_watts,
                architecture=r.architecture,
                memory_gb=r.memory_gb,
                memory_bandwidth_tbps=r.memory_bandwidth_tbps,
                inference_tflops=r.inference_tflops,
                training_tflops=r.training_tflops,
                energy_efficiency_tflops_per_watt=r.energy_efficiency_tflops_per_watt,
                release_year=r.release_year,
                source=r.source,
            )
            for r in rows
        ],
    )
