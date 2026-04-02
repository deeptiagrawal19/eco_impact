"""
Load reference data into the eco-impact database.

Run from ``apps/api`` after migrations::

    uv run python seed.py
    # or: PYTHONPATH=. python seed.py
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import math
import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.tables import (
    AIModel,
    CarbonIntensityReading,
    EnergyEstimate,
    GPUBenchmark,
    ProviderDataCenter,
    SustainabilityReport,
)
from app.services.carbon_constants import MVP_CARBON_ZONES


def uid(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def approx_co2_g(wh: float | None) -> float | None:
    if wh is None:
        return None
    return round(wh * 0.42, 6)


def approx_water_ml(wh: float | None) -> float | None:
    if wh is None:
        return None
    return round(wh * 0.25, 6)


def eco_grade(wh: float | None) -> str | None:
    if wh is None:
        return None
    if wh <= 0.1:
        return "A"
    if wh <= 0.35:
        return "B"
    if wh <= 0.8:
        return "C"
    if wh <= 2.0:
        return "D"
    return "F"


async def truncate_seed_tables(session: AsyncSession) -> None:
    await session.execute(
        sa.text(
            "TRUNCATE TABLE "
            "carbon_intensity_readings, "
            "energy_estimates, "
            "sustainability_reports, "
            "provider_data_centers, "
            "gpu_benchmarks, "
            "ai_models "
            "RESTART IDENTITY CASCADE"
        )
    )


def ai_model_rows(now: dt.datetime) -> list[AIModel]:
    specs: list[tuple[uuid.UUID, str, str, int | None, str, float | None, str]] = [
        (
            uid("a0000001-0001-4001-8001-000000000001"),
            "GPT-4o",
            "openai",
            None,
            "multimodal",
            0.34,
            "Public LCA & vendor data",
        ),
        (
            uid("a0000001-0001-4001-8001-000000000002"),
            "Claude 3.5 Sonnet",
            "anthropic",
            None,
            "multimodal",
            0.29,
            "Public LCA & vendor data",
        ),
        (
            uid("a0000001-0001-4001-8001-000000000003"),
            "GPT-o3",
            "openai",
            None,
            "text",
            3.9,
            "Public benchmarks (reasoning-class)",
        ),
        (
            uid("a0000001-0001-4001-8001-000000000004"),
            "Gemini Flash",
            "google",
            None,
            "multimodal",
            0.24,
            "Public LCA & vendor data",
        ),
        (
            uid("a0000001-0001-4001-8001-000000000005"),
            "Llama 3.1 8B",
            "meta",
            8,
            "text",
            0.032,
            "Meta model card",
        ),
        (
            uid("a0000001-0001-4001-8001-000000000006"),
            "Midjourney v6",
            "midjourney",
            None,
            "image",
            3.6,
            "Industry benchmarks",
        ),
        (
            uid("a0000001-0001-4001-8001-000000000007"),
            "DALL-E 3",
            "openai",
            None,
            "image",
            1.2,
            "Public LCA & vendor data",
        ),
        (
            uid("a0000001-0001-4001-8001-000000000008"),
            "Claude 3.7 Sonnet",
            "anthropic",
            None,
            "multimodal",
            0.41,
            "Public benchmarks",
        ),
        (
            uid("a0000001-0001-4001-8001-000000000009"),
            "Gemini 1.5 Pro",
            "google",
            None,
            "multimodal",
            0.55,
            "Public benchmarks",
        ),
    ]
    rows: list[AIModel] = []
    for mid, name, provider, params, mtype, ewh, cite in specs:
        rows.append(
            AIModel(
                id=mid,
                name=name,
                provider=provider,
                parameter_count=params,
                model_type=mtype,
                energy_per_query_wh=ewh,
                water_per_query_ml=approx_water_ml(ewh),
                co2_per_query_g=approx_co2_g(ewh),
                eco_score=eco_grade(ewh),
                source_paper=cite,
                last_updated=now,
            )
        )
    return rows


def gpu_benchmark_rows() -> list[GPUBenchmark]:
    specs = [
        ("NVIDIA A100 SXM", 400, "Ampere", 80, 2.0, 312.0, 624.0, 0.78, 2020, "NVIDIA datasheet"),
        ("NVIDIA H100 SXM", 700, "Hopper", 80, 3.35, 989.0, 1979.0, 1.41, 2022, "NVIDIA datasheet"),
        ("NVIDIA H200", 700, "Hopper", 141, 4.8, 1486.0, 2972.0, 2.12, 2024, "NVIDIA H200 brief"),
        ("NVIDIA B200", 1000, "Blackwell", 192, 8.0, 4500.0, 9000.0, 4.5, 2024, "Representative spec"),
        ("NVIDIA GB200", 2700, "Blackwell MGX", 384, 16.0, 5000.0, 10000.0, 1.85, 2024, "NVIDIA GB200 ref"),
        ("AMD MI300X", 750, "CDNA3", 192, 5.3, 1307.0, 2614.0, 1.74, 2023, "AMD MI300 brief"),
    ]
    out: list[GPUBenchmark] = []
    for name, tdp, arch, mem, bw, inf, train, eff, year, src in specs:
        out.append(
            GPUBenchmark(
                id=uuid.uuid4(),
                gpu_name=name,
                tdp_watts=tdp,
                architecture=arch,
                memory_gb=mem,
                memory_bandwidth_tbps=bw,
                inference_tflops=inf,
                training_tflops=train,
                energy_efficiency_tflops_per_watt=eff,
                release_year=year,
                source=src,
            )
        )
    return out


def provider_datacenter_rows() -> list[ProviderDataCenter]:
    """Five real facility locations with coordinates and balancing regions."""
    return [
        ProviderDataCenter(
            id=uid("b0000001-0001-4001-8001-000000000001"),
            provider="google",
            name="Google Los Angeles (c/o regional edge)",
            region="Los Angeles County, CA",
            country="USA",
            latitude=34.0522,
            longitude=-118.2437,
            grid_region="US-CAL-CISO",
            pue=1.10,
            wue=1.05,
            capacity_mw=40.0,
            renewable_percentage=92.0,
            cooling_type="evaporative + mechanical",
        ),
        ProviderDataCenter(
            id=uid("b0000001-0001-4001-8001-000000000002"),
            provider="microsoft",
            name="Microsoft East US (Boydton area)",
            region="Boydton, VA",
            country="USA",
            latitude=36.6671,
            longitude=-78.3889,
            grid_region="US-MIDA-PJM",
            pue=1.12,
            wue=0.48,
            capacity_mw=120.0,
            renewable_percentage=88.0,
            cooling_type="adiabatic",
        ),
        ProviderDataCenter(
            id=uid("b0000001-0001-4001-8001-000000000003"),
            provider="meta",
            name="Meta New York (regional footprint)",
            region="New York, NY",
            country="USA",
            latitude=40.7128,
            longitude=-74.0060,
            grid_region="US-NY-NYIS",
            pue=1.11,
            wue=0.55,
            capacity_mw=35.0,
            renewable_percentage=100.0,
            cooling_type="air-side economizer",
        ),
        ProviderDataCenter(
            id=uid("b0000001-0001-4001-8001-000000000004"),
            provider="google",
            name="Google Hamina",
            region="Hamina",
            country="Finland",
            latitude=60.5693,
            longitude=27.1981,
            grid_region="SE",
            pue=1.09,
            wue=0.12,
            capacity_mw=200.0,
            renewable_percentage=97.0,
            cooling_type="seawater cooling",
        ),
        ProviderDataCenter(
            id=uid("b0000001-0001-4001-8001-000000000005"),
            provider="amazon",
            name="AWS eu-west-1 (Dublin)",
            region="Dublin",
            country="Ireland",
            latitude=53.3498,
            longitude=-6.2603,
            grid_region="IE",
            pue=1.13,
            wue=0.22,
            capacity_mw=180.0,
            renewable_percentage=95.0,
            cooling_type="indirect evaporative",
        ),
    ]


def sustainability_report_rows() -> list[SustainabilityReport]:
    """Sample 2024 provider sustainability rows (public report figures, rounded)."""
    return [
        SustainabilityReport(
            id=uid("c0000001-0001-4001-8001-000000000001"),
            provider="google",
            year=2024,
            total_electricity_gwh=30800.0,
            total_water_gallons=7_200_000_000.0,
            total_emissions_mtco2e=12.8e6,
            scope1_mtco2e=280_000.0,
            scope2_mtco2e=4_100_000.0,
            scope3_mtco2e=8_420_000.0,
            renewable_match_percentage=100.0,
            avg_pue=1.10,
            report_url="https://sustainability.google/reports/2024/",
        ),
        SustainabilityReport(
            id=uid("c0000001-0001-4001-8001-000000000002"),
            provider="microsoft",
            year=2024,
            total_electricity_gwh=24000.0,
            total_water_gallons=5_400_000_000.0,
            total_emissions_mtco2e=15.2e6,
            scope1_mtco2e=310_000.0,
            scope2_mtco2e=5_900_000.0,
            scope3_mtco2e=8_990_000.0,
            renewable_match_percentage=100.0,
            avg_pue=1.12,
            report_url="https://www.microsoft.com/sustainability/report",
        ),
        SustainabilityReport(
            id=uid("c0000001-0001-4001-8001-000000000003"),
            provider="meta",
            year=2024,
            total_electricity_gwh=8900.0,
            total_water_gallons=2_600_000_000.0,
            total_emissions_mtco2e=6.1e6,
            scope1_mtco2e=95_000.0,
            scope2_mtco2e=2_100_000.0,
            scope3_mtco2e=3_905_000.0,
            renewable_match_percentage=100.0,
            avg_pue=1.11,
            report_url="https://sustainability.fb.com/report/",
        ),
    ]


def _zone_carbon_base() -> dict[str, float]:
    """Representative grid carbon (gCO2/kWh) for seeded variation."""
    return {
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


def carbon_sample_rows(now: dt.datetime) -> list[CarbonIntensityReading]:
    bases = _zone_carbon_base()
    rows: list[CarbonIntensityReading] = []
    start = now - dt.timedelta(days=14)
    t = start.replace(minute=0, second=0, microsecond=0)
    while t <= now:
        for zone in MVP_CARBON_ZONES:
            base = bases.get(zone, 320.0)
            phase = (t.timestamp() / 3600.0 + hash(zone) % 100) * 0.02
            wiggle = 15 * math.sin(phase)
            avg = max(40.0, base + wiggle + (hash(f"{zone}:{t.isoformat()}") % 17))
            rows.append(
                CarbonIntensityReading(
                    time=t,
                    region=zone,
                    carbon_intensity_avg=avg,
                    carbon_intensity_marginal=avg * 1.08,
                    fossil_fuel_percentage=None,
                    renewable_percentage=None,
                    source="seed",
                )
            )
        t += dt.timedelta(hours=3)
    return rows


def energy_estimate_rows(models: list[AIModel], now: dt.datetime) -> list[EnergyEstimate]:
    """Hourly synthetic estimates for the last 72 hours (development seed)."""
    rows: list[EnergyEstimate] = []
    start = (now - dt.timedelta(hours=72)).replace(minute=0, second=0, microsecond=0)
    t = start
    hour_i = 0
    while t <= now:
        for m in models:
            if m.energy_per_query_wh is None:
                continue
            h = int(hashlib.md5(f"{m.id}:{t.isoformat()}".encode()).hexdigest(), 16)
            queries = 1_200_000 + (hour_i * 12_000) + (h % 800_000)
            wh = float(m.energy_per_query_wh)
            mwh = queries * wh / 1_000_000.0
            water_ml = float(m.water_per_query_ml or 0)
            water_l = queries * water_ml / 1000.0
            co2_t = queries * float(m.co2_per_query_g or 0) / 1_000_000.0
            region_roll = MVP_CARBON_ZONES[h % len(MVP_CARBON_ZONES)]
            rows.append(
                EnergyEstimate(
                    time=t,
                    model_id=m.id,
                    estimated_queries=queries,
                    total_energy_mwh=round(mwh, 8),
                    total_water_liters=round(water_l, 4),
                    total_co2_tonnes=round(co2_t, 8),
                    avg_carbon_intensity=320.0,
                    region=region_roll,
                )
            )
        t += dt.timedelta(hours=1)
        hour_i += 1
    return rows


async def seed() -> None:
    now = dt.datetime.now(dt.timezone.utc)
    models = ai_model_rows(now)
    gpus = gpu_benchmark_rows()
    dcs = provider_datacenter_rows()
    sust = sustainability_report_rows()
    carbon = carbon_sample_rows(now)
    energies = energy_estimate_rows(models, now)

    async with async_session_maker() as session:
        await truncate_seed_tables(session)
        session.add_all(models)
        session.add_all(gpus)
        session.add_all(dcs)
        session.add_all(sust)
        session.add_all(carbon)
        session.add_all(energies)
        await session.commit()


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
