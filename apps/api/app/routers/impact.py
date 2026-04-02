"""
Impact estimation API (energy, carbon, water) for AI inference workloads.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db_session
from app.models.tables import AIModel
from app.schemas.impact import (
    ImpactCompareResponse,
    ImpactEstimateRequest,
    ImpactEstimateResponse,
    ImpactModelsListResponse,
    ModelCatalogOut,
    ModelComparisonOut,
    EquivalentsOut,
    CarbonBreakdownOut,
    WaterBreakdownOut,
)
from app.services.impact_calculator import (
    AImpactCalculator,
    METHODOLOGY_NOTE,
    REFERENCE_TOKEN_COUNT,
    QueryType,
    get_model_by_identifier,
)

router = APIRouter(prefix="/api/impact", tags=["impact"])


def _cast_query_type(q: str) -> QueryType:
    s = q.lower().strip()
    if s in ("text", "image", "video", "multimodal"):
        return s  # type: ignore[return-value]
    return "text"


@router.post("/estimate", response_model=ImpactEstimateResponse)
async def estimate_impact(
    body: ImpactEstimateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ImpactEstimateResponse:
    """Estimate Wh, grid-adjusted CO₂, and water (direct + indirect) for one query."""
    mrow = await get_model_by_identifier(session, body.model)
    if mrow is None:
        raise HTTPException(status_code=404, detail=f"Unknown model: {body.model}")

    qt = _cast_query_type(body.query_type)
    calc = AImpactCalculator(session)
    energy_wh = await calc.estimate_energy_with_pue(
        mrow,
        query_type=qt,
        token_count=body.token_count,
        image_count=body.image_count,
    )
    carbon = await calc.estimate_carbon(
        mrow,
        region=body.region,
        energy_wh=energy_wh,
        query_type=qt,
        token_count=body.token_count,
        image_count=body.image_count,
    )
    water = await calc.estimate_water(
        mrow,
        region=body.region,
        energy_wh=energy_wh,
        query_type=qt,
        token_count=body.token_count,
        image_count=body.image_count,
    )

    carbon_avg = carbon.get("carbon_g_avg") or 0.0
    water_total = water.get("total_ml") or 0.0
    equiv = AImpactCalculator.get_equivalents(energy_wh, carbon_avg, water_total)

    return ImpactEstimateResponse(
        energy_wh=energy_wh,
        carbon=CarbonBreakdownOut(
            avg_g=carbon.get("carbon_g_avg"),
            marginal_g=carbon.get("carbon_g_marginal"),
            intensity_avg_g_per_kwh=carbon.get("carbon_intensity_avg_g_per_kwh"),
            intensity_marginal_g_per_kwh=carbon.get("carbon_intensity_marginal_g_per_kwh"),
            grid_region_used=carbon.get("grid_region_used"),
        ),
        water=WaterBreakdownOut(
            direct_ml=water.get("direct_ml"),
            indirect_ml=water.get("indirect_ml"),
            total_ml=water.get("total_ml"),
            wue_l_per_kwh=water.get("wue_l_per_kwh"),
        ),
        equivalents=EquivalentsOut.model_validate(equiv),
        methodology_note=METHODOLOGY_NOTE,
    )


@router.get("/compare", response_model=ImpactCompareResponse)
async def compare_models(
    task_type: str = Query("text", description="text | image | video | multimodal"),
    region: str | None = Query(None),
    token_count: int = Query(REFERENCE_TOKEN_COUNT, ge=1, le=2_000_000),
    session: AsyncSession = Depends(get_db_session),
) -> ImpactCompareResponse:
    """Rank catalog models by estimated facility energy for the workload shape."""
    calc = AImpactCalculator(session)
    rows = await calc.compare_models(
        task_type=task_type,
        region=region,
        token_count=token_count,
    )
    out: list[ModelComparisonOut] = []
    for r in rows:
        c = r.carbon_g
        w = r.water_ml
        out.append(
            ModelComparisonOut(
                model_id=r.model_id,
                model_name=r.model_name,
                provider=r.provider,
                energy_wh=r.energy_wh,
                carbon_g_avg=c.get("avg"),
                carbon_g_marginal=c.get("marginal"),
                water_direct_ml=w.get("direct"),
                water_indirect_ml=w.get("indirect"),
                water_total_ml=w.get("total"),
                eco_score=r.eco_score,
                percentage_vs_best=r.percentage_vs_best,
            )
        )
    return ImpactCompareResponse(task_type=task_type, region=region, models=out)


@router.get("/models", response_model=ImpactModelsListResponse)
async def list_models(
    session: AsyncSession = Depends(get_db_session),
) -> ImpactModelsListResponse:
    """Return all rows from ``ai_models`` with baseline sustainability fields."""
    res = await session.execute(select(AIModel).order_by(AIModel.provider, AIModel.name))
    rows = res.scalars().all()
    return ImpactModelsListResponse(
        models=[
            ModelCatalogOut(
                id=str(m.id),
                name=m.name,
                provider=m.provider,
                model_type=m.model_type,
                energy_per_query_wh=m.energy_per_query_wh,
                water_per_query_ml=m.water_per_query_ml,
                co2_per_query_g=m.co2_per_query_g,
                eco_score=m.eco_score,
                parameter_count=int(m.parameter_count) if m.parameter_count is not None else None,
                source_paper=m.source_paper,
            )
            for m in rows
        ]
    )
