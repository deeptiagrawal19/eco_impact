"""Dashboard metrics, timelines, and catalog endpoints."""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from app.models.tables import (
    AIModel,
    CarbonIntensityReading,
    EnergyEstimate,
    GPUBenchmark,
    ProviderDataCenter,
    SustainabilityReport,
)
from app.schemas.dashboard import (
    BestTimeRegion,
    CarbonHistoryPoint,
    CarbonHistoryResponse,
    DashboardMetricsResponse,
    DataCenterOut,
    DataCentersResponse,
    EnergyDeepDiveResponse,
    EnergyTimelinePoint,
    EnergyTimelineResponse,
    GPUBenchmarkOut,
    GPUListResponse,
    MetricSparklinePoint,
    SustainabilityListResponse,
    SustainabilityReportOut,
    TrainingInferenceSplit,
)
from app.services.carbon_constants import MVP_CARBON_ZONES

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
catalog_router = APIRouter(prefix="/api", tags=["catalog"])

# Fallback gCO2/kWh when no recent reading exists for a zone.
DEMO_CARBON_G_PER_KWH: dict[str, float] = {
    "US-CAL-CISO": 255.0,
    "US-NY-NYIS": 305.0,
    "US-MIDA-PJM": 385.0,
    "DE": 375.0,
    "GB": 175.0,
    "FR": 65.0,
    "IE": 340.0,
    "SE": 28.0,
    "NL": 335.0,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _range_delta(r: str) -> timedelta:
    r = r.lower().strip()
    if r in ("7d", "7"):
        return timedelta(days=7)
    if r in ("30d", "30"):
        return timedelta(days=30)
    return timedelta(hours=24)


def _trend_pct(curr: float, prev: float) -> float | None:
    if prev == 0:
        return None if curr == 0 else 100.0
    return round((curr - prev) / prev * 100.0, 2)


async def _synthetic_energy_timeline(
    session: AsyncSession,
    start: datetime,
    range_label: str,
) -> EnergyTimelineResponse:
    """Synthetic hourly rollups from the model catalog if estimates are missing."""
    res = await session.execute(select(AIModel).where(AIModel.energy_per_query_wh.isnot(None)))
    models = res.scalars().all()
    if not models:
        return EnergyTimelineResponse(range=range_label, points=[])
    now = _now()
    points: list[EnergyTimelinePoint] = []
    t = start.replace(minute=0, second=0, microsecond=0)
    hi = 0
    while t <= now:
        by_prov: dict[str, float] = {}
        for m in models:
            ewh = float(m.energy_per_query_wh or 0.1)
            h = int(hashlib.md5(f"{m.id}:{t.isoformat()}".encode()).hexdigest(), 16)
            q = 1_200_000 + (hi * 12_000) + (h % 800_000)
            mwh = q * ewh / 1e6
            p = (m.provider or "unknown").lower()
            by_prov[p] = by_prov.get(p, 0.0) + mwh
        for prov, mwh in sorted(by_prov.items()):
            points.append(EnergyTimelinePoint(t=t, provider=prov, mwh=round(mwh, 6)))
        t += timedelta(hours=1)
        hi += 1
    return EnergyTimelineResponse(range=range_label, points=points)


def _demo_sparkline(now: datetime, base: float, *, n: int = 24) -> list[MetricSparklinePoint]:
    return [
        MetricSparklinePoint(
            t=now - timedelta(hours=n - 1 - i),
            value=max(0.0, base * (1 + 0.08 * math.sin(i / 3.5))),
        )
        for i in range(n)
    ]


async def _scalar(session: AsyncSession, stmt) -> float:
    res = await session.execute(stmt)
    val = res.scalar_one()
    return float(val or 0.0)


@router.get("/metrics", response_model=DashboardMetricsResponse)
async def dashboard_metrics(session: AsyncSession = Depends(get_db_session)):
    """Today's rollups, trends vs prior window, and 24h sparklines."""
    now = _now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    prev_day_start = day_start - timedelta(days=1)
    hours_24 = now - timedelta(hours=24)
    hours_48 = now - timedelta(hours=48)

    # Today's totals
    q_energy_today = select(func.coalesce(func.sum(EnergyEstimate.total_energy_mwh), 0.0)).where(
        EnergyEstimate.time >= day_start
    )
    q_water_today = select(func.coalesce(func.sum(EnergyEstimate.total_water_liters), 0.0)).where(
        EnergyEstimate.time >= day_start
    )
    q_queries_today = select(func.coalesce(func.sum(EnergyEstimate.estimated_queries), 0)).where(
        EnergyEstimate.time >= day_start
    )

    energy_mwh_today = await _scalar(session, q_energy_today)
    water_liters_today = await _scalar(session, q_water_today)
    queries_raw = await _scalar(session, q_queries_today)
    queries_billions_today = float(queries_raw) / 1e9

    prev_energy = await _scalar(
        session,
        select(func.coalesce(func.sum(EnergyEstimate.total_energy_mwh), 0.0)).where(
            EnergyEstimate.time >= prev_day_start,
            EnergyEstimate.time < day_start,
        ),
    )
    prev_water = await _scalar(
        session,
        select(func.coalesce(func.sum(EnergyEstimate.total_water_liters), 0.0)).where(
            EnergyEstimate.time >= prev_day_start,
            EnergyEstimate.time < day_start,
        ),
    )
    prev_queries = await _scalar(
        session,
        select(func.coalesce(func.sum(EnergyEstimate.estimated_queries), 0)).where(
            EnergyEstimate.time >= prev_day_start,
            EnergyEstimate.time < day_start,
        ),
    )

    win_curr_e = await _scalar(
        session,
        select(func.coalesce(func.sum(EnergyEstimate.total_energy_mwh), 0.0)).where(
            EnergyEstimate.time >= hours_24
        ),
    )
    win_prev_e = await _scalar(
        session,
        select(func.coalesce(func.sum(EnergyEstimate.total_energy_mwh), 0.0)).where(
            EnergyEstimate.time >= hours_48,
            EnergyEstimate.time < hours_24,
        ),
    )

    # Carbon average across MVP regions (latest row each)
    carbon_vals: list[float] = []
    for z in MVP_CARBON_ZONES:
        stmt = (
            select(CarbonIntensityReading.carbon_intensity_avg)
            .where(CarbonIntensityReading.region == z)
            .order_by(CarbonIntensityReading.time.desc())
            .limit(1)
        )
        res = await session.execute(stmt)
        v = res.scalar_one_or_none()
        if v is not None:
            carbon_vals.append(float(v))
    carbon_avg = sum(carbon_vals) / len(carbon_vals) if carbon_vals else None

    # Sparklines (hourly buckets); fall back to demo curves if empty totals
    async def hourly_energy_series() -> list[MetricSparklinePoint]:
        stmt = (
            select(
                func.date_trunc("hour", EnergyEstimate.time).label("b"),
                func.coalesce(func.sum(EnergyEstimate.total_energy_mwh), 0.0),
            )
            .where(EnergyEstimate.time >= hours_24)
            .group_by(func.date_trunc("hour", EnergyEstimate.time))
            .order_by(func.date_trunc("hour", EnergyEstimate.time))
        )
        res = await session.execute(stmt)
        rows = list(res.all())
        if not rows:
            return _demo_sparkline(now, max(0.5, energy_mwh_today / 24 or 0.5))
        return [MetricSparklinePoint(t=r[0], value=float(r[1])) for r in rows]

    async def hourly_carbon_series() -> list[MetricSparklinePoint]:
        stmt = (
            select(
                func.date_trunc("hour", CarbonIntensityReading.time).label("b"),
                func.avg(CarbonIntensityReading.carbon_intensity_avg),
            )
            .where(
                CarbonIntensityReading.time >= hours_24,
                CarbonIntensityReading.region.in_(MVP_CARBON_ZONES),
            )
            .group_by(func.date_trunc("hour", CarbonIntensityReading.time))
            .order_by(func.date_trunc("hour", CarbonIntensityReading.time))
        )
        res = await session.execute(stmt)
        rows = list(res.all())
        if not rows:
            base = carbon_avg or 350.0
            return _demo_sparkline(now, base)
        return [MetricSparklinePoint(t=r[0], value=float(r[1] or 0)) for r in rows]

    async def hourly_water_series() -> list[MetricSparklinePoint]:
        stmt = (
            select(
                func.date_trunc("hour", EnergyEstimate.time).label("b"),
                func.coalesce(func.sum(EnergyEstimate.total_water_liters), 0.0),
            )
            .where(EnergyEstimate.time >= hours_24)
            .group_by(func.date_trunc("hour", EnergyEstimate.time))
            .order_by(func.date_trunc("hour", EnergyEstimate.time))
        )
        res = await session.execute(stmt)
        rows = list(res.all())
        if not rows:
            return _demo_sparkline(now, max(1e3, water_liters_today / 24 or 1e3))
        return [MetricSparklinePoint(t=r[0], value=float(r[1])) for r in rows]

    async def hourly_queries_series() -> list[MetricSparklinePoint]:
        stmt = (
            select(
                func.date_trunc("hour", EnergyEstimate.time).label("b"),
                func.coalesce(func.sum(EnergyEstimate.estimated_queries), 0.0),
            )
            .where(EnergyEstimate.time >= hours_24)
            .group_by(func.date_trunc("hour", EnergyEstimate.time))
            .order_by(func.date_trunc("hour", EnergyEstimate.time))
        )
        res = await session.execute(stmt)
        rows = list(res.all())
        if not rows:
            return _demo_sparkline(now, max(1e6, queries_raw / 24 or 1e6))
        return [MetricSparklinePoint(t=r[0], value=float(r[1])) for r in rows]

    e_spark = await hourly_energy_series()
    c_spark = await hourly_carbon_series()
    w_spark = await hourly_water_series()
    q_spark = await hourly_queries_series()

    return DashboardMetricsResponse(
        energy_mwh_today=energy_mwh_today,
        energy_trend_pct=_trend_pct(win_curr_e, win_prev_e),
        carbon_avg_g_per_kwh=carbon_avg,
        carbon_trend_pct=None,
        water_million_liters_today=water_liters_today / 1e6,
        water_trend_pct=_trend_pct(water_liters_today, prev_water),
        queries_billions_today=queries_billions_today,
        queries_trend_pct=_trend_pct(float(queries_raw), float(prev_queries)),
        energy_sparkline_24h=e_spark,
        carbon_sparkline_24h=c_spark,
        water_sparkline_24h=w_spark,
        queries_sparkline_24h=q_spark,
    )


@router.get("/energy-timeline", response_model=EnergyTimelineResponse)
async def energy_timeline(
    range: str = Query("24h", alias="range"),
    session: AsyncSession = Depends(get_db_session),
):
    now = _now()
    delta = _range_delta(range)
    start = now - delta

    stmt = (
        select(
            func.date_trunc("hour", EnergyEstimate.time).label("b"),
            AIModel.provider,
            func.coalesce(func.sum(EnergyEstimate.total_energy_mwh), 0.0),
        )
        .join(AIModel, EnergyEstimate.model_id == AIModel.id)
        .where(EnergyEstimate.time >= start)
        .group_by(func.date_trunc("hour", EnergyEstimate.time), AIModel.provider)
        .order_by(func.date_trunc("hour", EnergyEstimate.time), AIModel.provider)
    )
    res = await session.execute(stmt)
    rows = res.all()
    points = [
        EnergyTimelinePoint(t=r[0], provider=r[1], mwh=float(r[2])) for r in rows
    ]
    if not points:
        return await _synthetic_energy_timeline(session, start, range)
    return EnergyTimelineResponse(range=range, points=points)


@router.get("/training-inference", response_model=EnergyDeepDiveResponse)
async def training_inference(
    range: str = Query("24h"),
    session: AsyncSession = Depends(get_db_session),
):
    """Heuristic training vs inference split (no explicit training signal in DB)."""
    now = _now()
    start = now - _range_delta(range)
    total = await _scalar(
        session,
        select(func.coalesce(func.sum(EnergyEstimate.total_energy_mwh), 0.0)).where(
            EnergyEstimate.time >= start
        ),
    )
    # Default split when training is not modeled separately (~78% inference / 22% training).
    inf_share, tr_share = 0.78, 0.22
    timeline_stmt = (
        select(
            func.date_trunc("hour", EnergyEstimate.time).label("b"),
            AIModel.provider,
            func.coalesce(func.sum(EnergyEstimate.total_energy_mwh), 0.0),
        )
        .join(AIModel, EnergyEstimate.model_id == AIModel.id)
        .where(EnergyEstimate.time >= start)
        .group_by(func.date_trunc("hour", EnergyEstimate.time), AIModel.provider)
        .order_by(func.date_trunc("hour", EnergyEstimate.time))
    )
    res = await session.execute(timeline_stmt)
    tpoints = [
        EnergyTimelinePoint(t=r[0], provider=r[1], mwh=float(r[2])) for r in res.all()
    ]
    if total < 1e-12 and not tpoints:
        synth = await _synthetic_energy_timeline(session, start, range)
        tpoints = synth.points
        total = sum(p.mwh for p in tpoints)
    return EnergyDeepDiveResponse(
        training_inference=TrainingInferenceSplit(
            inference_share=inf_share,
            training_share=tr_share,
            inference_mwh=total * inf_share,
            training_mwh=total * tr_share,
        ),
        timeline_by_provider=tpoints,
    )


@router.get("/carbon-history", response_model=CarbonHistoryResponse)
async def carbon_history(
    hours: int = Query(168, ge=1, le=720),
    session: AsyncSession = Depends(get_db_session),
):
    now = _now()
    start = now - timedelta(hours=hours)
    stmt = (
        select(CarbonIntensityReading)
        .where(
            CarbonIntensityReading.time >= start,
            CarbonIntensityReading.region.in_(MVP_CARBON_ZONES),
        )
        .order_by(CarbonIntensityReading.time.asc())
    )
    res = await session.execute(stmt)
    rows = res.scalars().all()
    pts = [
        CarbonHistoryPoint(
            t=r.time,
            region=r.region,
            carbon_avg=r.carbon_intensity_avg,
            carbon_marginal=r.carbon_intensity_marginal,
        )
        for r in rows
    ]
    return CarbonHistoryResponse(points=pts)


@router.get("/best-carbon-times")
async def best_carbon_times(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Best UTC hour (0–23) with lowest average intensity per region (last 7d)."""
    now = _now()
    start = now - timedelta(days=7)
    out: list[BestTimeRegion] = []
    for z in MVP_CARBON_ZONES:
        stmt = (
            select(
                extract("hour", CarbonIntensityReading.time).label("hr"),
                func.avg(CarbonIntensityReading.carbon_intensity_avg).label("avg_i"),
            )
            .where(
                CarbonIntensityReading.region == z,
                CarbonIntensityReading.time >= start,
            )
            .group_by(extract("hour", CarbonIntensityReading.time))
        )
        res = await session.execute(stmt)
        rows = [(int(r[0]), float(r[1] or 0)) for r in res.all()]
        if not rows:
            out.append(BestTimeRegion(region=z, hour_utc_lowest_avg=None, avg_intensity_g_per_kwh=None))
            continue
        best = min(rows, key=lambda x: x[1])
        out.append(
            BestTimeRegion(
                region=z,
                hour_utc_lowest_avg=best[0],
                avg_intensity_g_per_kwh=round(best[1], 2),
            )
        )
    return {"regions": [r.model_dump() for r in out]}


@catalog_router.get("/datacenters", response_model=DataCentersResponse)
async def list_datacenters(session: AsyncSession = Depends(get_db_session)):
    res = await session.execute(select(ProviderDataCenter))
    rows = res.scalars().all()
    dc_out: list[DataCenterOut] = []
    for r in rows:
        key = f"{r.provider}:{r.region}"
        stress = abs(hash(key)) % 5
        dc_out.append(
            DataCenterOut(
                id=str(r.id),
                provider=r.provider,
                name=r.name,
                region=r.region,
                country=r.country,
                latitude=r.latitude,
                longitude=r.longitude,
                grid_region=r.grid_region,
                pue=r.pue,
                wue=r.wue,
                capacity_mw=r.capacity_mw,
                renewable_percentage=r.renewable_percentage,
                cooling_type=r.cooling_type,
                water_stress_level=stress,
            )
        )
    return DataCentersResponse(data_centers=dc_out)


@catalog_router.get("/sustainability/reports", response_model=SustainabilityListResponse)
async def sustainability_reports(session: AsyncSession = Depends(get_db_session)):
    stmt = select(SustainabilityReport).order_by(
        SustainabilityReport.provider,
        SustainabilityReport.year.desc(),
    )
    res = await session.execute(stmt)
    rows = res.scalars().all()
    reports = [
        SustainabilityReportOut(
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
    ]
    return SustainabilityListResponse(reports=reports)


@catalog_router.get("/gpu/benchmarks", response_model=GPUListResponse)
async def gpu_benchmarks(session: AsyncSession = Depends(get_db_session)):
    res = await session.execute(select(GPUBenchmark).order_by(GPUBenchmark.gpu_name))
    rows = res.scalars().all()
    gpus = [
        GPUBenchmarkOut(
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
    ]
    return GPUListResponse(gpus=gpus)


@router.get("/carbon-by-region")
async def carbon_by_region(session: AsyncSession = Depends(get_db_session)):
    """Latest carbon intensity per MVP region for bar chart."""
    now = _now()
    out: list[dict[str, Any]] = []
    for z in MVP_CARBON_ZONES:
        stmt = (
            select(CarbonIntensityReading)
            .where(CarbonIntensityReading.region == z)
            .order_by(CarbonIntensityReading.time.desc())
            .limit(1)
        )
        res = await session.execute(stmt)
        r = res.scalar_one_or_none()
        if r is not None and r.carbon_intensity_avg is not None:
            out.append(
                {
                    "region": z,
                    "carbon_avg": r.carbon_intensity_avg,
                    "carbon_marginal": r.carbon_intensity_marginal,
                    "time": r.time.isoformat(),
                }
            )
        elif (demo := DEMO_CARBON_G_PER_KWH.get(z)) is not None:
            out.append(
                {
                    "region": z,
                    "carbon_avg": demo,
                    "carbon_marginal": demo * 1.05,
                    "time": now.isoformat(),
                }
            )
        else:
            out.append({"region": z, "carbon_avg": None, "carbon_marginal": None, "time": None})
    return {"regions": out}
