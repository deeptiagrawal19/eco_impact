"""Schemas for ``/api/reports`` ingestion / comparison APIs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SustainabilityReportItem(BaseModel):
    id: str
    provider: str
    year: int
    total_electricity_gwh: float | None = None
    total_water_gallons: float | None = None
    total_emissions_mtco2e: float | None = None
    scope1_mtco2e: float | None = None
    scope2_mtco2e: float | None = None
    scope3_mtco2e: float | None = None
    renewable_match_percentage: float | None = None
    avg_pue: float | None = None
    report_url: str | None = None


class SustainabilityListResponse(BaseModel):
    reports: list[SustainabilityReportItem]
    provider: str | None = None


class SustainabilityComparisonRow(BaseModel):
    provider: str
    year: int
    total_electricity_gwh: float | None = None
    total_water_gallons: float | None = None
    total_emissions_mtco2e: float | None = None
    renewable_match_percentage: float | None = None
    avg_pue: float | None = None


class SustainabilityComparisonResponse(BaseModel):
    rows: list[SustainabilityComparisonRow]


class TrendPoint(BaseModel):
    provider: str
    year: int
    yoy_pct: float | None = None
    value: float | None = None


class TrendsResponse(BaseModel):
    metric: str
    source: str = Field(description="yoy_metadata | computed_db")
    points: list[TrendPoint]
    metadata_updated_at: str | None = None


class HardwareItem(BaseModel):
    id: str
    gpu_name: str
    tdp_watts: int | None = None
    architecture: str | None = None
    memory_gb: int | None = None
    memory_bandwidth_tbps: float | None = None
    inference_tflops: float | None = None
    training_tflops: float | None = None
    energy_efficiency_tflops_per_watt: float | None = None
    release_year: int | None = None
    source: str | None = None


class HardwareListResponse(BaseModel):
    hardware: list[HardwareItem]
