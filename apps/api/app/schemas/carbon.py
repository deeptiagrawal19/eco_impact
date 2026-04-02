"""Pydantic models for carbon intensity HTTP responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CarbonReadingOut(BaseModel):
    """Single row from ``carbon_intensity_readings``."""

    model_config = ConfigDict(from_attributes=True)

    time: datetime
    region: str
    carbon_intensity_avg: float | None = None
    carbon_intensity_marginal: float | None = None
    fossil_fuel_percentage: float | None = None
    renewable_percentage: float | None = None
    source: str


class CarbonLatestResponse(BaseModel):
    """Latest stored reading for a region (most recent timestamp)."""

    region: str
    reading: CarbonReadingOut | None = None


class CarbonHistoryResponse(BaseModel):
    """Time-ordered readings for a region."""

    region: str
    hours: int
    readings: list[CarbonReadingOut] = Field(default_factory=list)


class RegionLatestOut(BaseModel):
    """Region key with optional latest sample."""

    region: str
    reading: CarbonReadingOut | None = None


class CarbonRegionsResponse(BaseModel):
    """All MVP regions with their latest stored readings."""

    regions: list[RegionLatestOut]


class ComparisonRow(BaseModel):
    """One region in a cross-region comparison."""

    region: str
    carbon_intensity_avg: float | None = None
    carbon_intensity_marginal: float | None = None
    source: str | None = None
    time: datetime | None = None


class CarbonComparisonResponse(BaseModel):
    """Side-by-side snapshot for dashboard compare view."""

    rows: list[ComparisonRow]
