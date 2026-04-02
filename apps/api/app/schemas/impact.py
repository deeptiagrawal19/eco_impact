"""Pydantic schemas for impact estimation API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImpactEstimateRequest(BaseModel):
    """POST /api/impact/estimate body."""

    model: str = Field(..., description="Model id (UUID) or name, e.g. GPT-4o")
    query_type: str = Field(default="text", description="text | image | video | multimodal")
    token_count: int = Field(default=500, ge=1, le=2_000_000)
    region: str | None = Field(
        default=None,
        description="Electricity Maps zone for grid carbon/water proxy",
    )
    image_count: int | None = Field(
        default=None,
        ge=1,
        description="For image workloads; defaults to 1",
    )


class EquivalentsOut(BaseModel):
    smartphone_charges: float
    google_searches: float
    driving_km_equivalent: float
    water_bottles_500ml: float
    hours_led_bulb_10w: float
    tree_seconds_offset: float


class CarbonBreakdownOut(BaseModel):
    avg_g: float | None = None
    marginal_g: float | None = None
    intensity_avg_g_per_kwh: float | None = None
    intensity_marginal_g_per_kwh: float | None = None
    grid_region_used: str | None = None


class WaterBreakdownOut(BaseModel):
    direct_ml: float | None = None
    indirect_ml: float | None = None
    total_ml: float | None = None
    wue_l_per_kwh: float | None = None


class ImpactEstimateResponse(BaseModel):
    energy_wh: float
    carbon: CarbonBreakdownOut
    water: WaterBreakdownOut
    equivalents: EquivalentsOut
    methodology_note: str


class ModelComparisonOut(BaseModel):
    model_id: str
    model_name: str
    provider: str
    energy_wh: float
    carbon_g_avg: float | None = None
    carbon_g_marginal: float | None = None
    water_direct_ml: float | None = None
    water_indirect_ml: float | None = None
    water_total_ml: float | None = None
    eco_score: str | None = None
    percentage_vs_best: float


class ImpactCompareResponse(BaseModel):
    task_type: str
    region: str | None = None
    models: list[ModelComparisonOut]


class ModelCatalogOut(BaseModel):
    id: str
    name: str
    provider: str
    model_type: str | None = None
    energy_per_query_wh: float | None = None
    water_per_query_ml: float | None = None
    co2_per_query_g: float | None = None
    eco_score: str | None = None
    parameter_count: int | None = None
    source_paper: str | None = None


class ImpactModelsListResponse(BaseModel):
    models: list[ModelCatalogOut]
