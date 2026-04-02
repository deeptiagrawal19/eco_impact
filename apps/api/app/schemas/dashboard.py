"""Dashboard aggregate API schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MetricSparklinePoint(BaseModel):
    t: datetime
    value: float


class DashboardMetricsResponse(BaseModel):
    energy_mwh_today: float
    energy_trend_pct: float | None
    carbon_avg_g_per_kwh: float | None
    carbon_trend_pct: float | None
    water_million_liters_today: float
    water_trend_pct: float | None
    queries_billions_today: float
    queries_trend_pct: float | None
    energy_sparkline_24h: list[MetricSparklinePoint] = Field(default_factory=list)
    carbon_sparkline_24h: list[MetricSparklinePoint] = Field(default_factory=list)
    water_sparkline_24h: list[MetricSparklinePoint] = Field(default_factory=list)
    queries_sparkline_24h: list[MetricSparklinePoint] = Field(default_factory=list)


class EnergyTimelinePoint(BaseModel):
    t: datetime
    provider: str
    mwh: float


class EnergyTimelineResponse(BaseModel):
    range: str
    points: list[EnergyTimelinePoint]


class TrainingInferenceSplit(BaseModel):
    inference_share: float
    training_share: float
    inference_mwh: float
    training_mwh: float


class EnergyDeepDiveResponse(BaseModel):
    training_inference: TrainingInferenceSplit
    timeline_by_provider: list[EnergyTimelinePoint]


class DataCenterOut(BaseModel):
    id: str
    provider: str
    name: str | None
    region: str
    country: str
    latitude: float | None
    longitude: float | None
    grid_region: str | None
    pue: float | None
    wue: float | None
    capacity_mw: float | None
    renewable_percentage: float | None
    cooling_type: str | None
    water_stress_level: int | None = Field(None, description="0–4 WRI-style bucket (mock if unset)")


class DataCentersResponse(BaseModel):
    data_centers: list[DataCenterOut]


class SustainabilityReportOut(BaseModel):
    id: str
    provider: str
    year: int
    total_electricity_gwh: float | None
    total_water_gallons: float | None
    total_emissions_mtco2e: float | None
    scope1_mtco2e: float | None
    scope2_mtco2e: float | None
    scope3_mtco2e: float | None
    renewable_match_percentage: float | None
    avg_pue: float | None
    report_url: str | None


class SustainabilityListResponse(BaseModel):
    reports: list[SustainabilityReportOut]


class GPUBenchmarkOut(BaseModel):
    id: str
    gpu_name: str
    tdp_watts: int | None
    architecture: str | None
    memory_gb: int | None
    memory_bandwidth_tbps: float | None
    inference_tflops: float | None
    training_tflops: float | None
    energy_efficiency_tflops_per_watt: float | None
    release_year: int | None
    source: str | None


class GPUListResponse(BaseModel):
    gpus: list[GPUBenchmarkOut]


class CarbonHistoryPoint(BaseModel):
    t: datetime
    region: str
    carbon_avg: float | None
    carbon_marginal: float | None


class CarbonHistoryResponse(BaseModel):
    points: list[CarbonHistoryPoint]


class BestTimeRegion(BaseModel):
    region: str
    hour_utc_lowest_avg: int | None
    avg_intensity_g_per_kwh: float | None


class CarbonInsightsResponse(BaseModel):
    history: list[CarbonHistoryPoint]
    best_times: list[BestTimeRegion]
