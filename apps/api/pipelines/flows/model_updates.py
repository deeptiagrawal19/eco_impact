"""
Prefect flow: refresh ``ai_models`` from optional external benchmarks + DEA eco grades.

Schedule: daily 04:00 UTC (see ``prefect.yaml``).
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from prefect import flow, task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.tables import AIModel
from app.services.impact_calculator import REFERENCE_TOKEN_COUNT
from pipelines.lib.dea_scores import compute_eco_grades
from pipelines.services.model_sources import (
    extract_energy_adjustments,
    fetch_hf_ai_energy_scores,
    fetch_ml_energy_leaderboard,
)

logger = logging.getLogger(__name__)
RETRY = dict(retries=3, retry_delay_seconds=60)


@task(name="fetch_ml_energy_task", **RETRY)
async def fetch_ml_energy_task() -> dict[str, Any]:
    return await fetch_ml_energy_leaderboard()


@task(name="fetch_hf_energy_task", **RETRY)
async def fetch_hf_energy_task() -> dict[str, Any]:
    return await fetch_hf_ai_energy_scores()


@task(name="apply_model_updates", **RETRY)
async def apply_model_updates(ml_payload: dict[str, Any], hf_payload: dict[str, Any]) -> dict[str, Any]:
    adjustments = extract_energy_adjustments(
        ml_payload,
        hf_payload,
        reference_tokens=REFERENCE_TOKEN_COUNT,
    )

    async with async_session_maker() as session:
        res = await session.execute(select(AIModel).order_by(AIModel.provider, AIModel.name))
        models = list(res.scalars().all())
        if not models:
            logger.warning("apply_model_updates: no ai_models rows")
            return {"updated": 0, "grades_assigned": 0}

        dict_rows: list[dict[str, Any]] = []
        for m in models:
            d = {
                "id": str(m.id),
                "name": m.name,
                "provider": m.provider,
                "parameter_count": m.parameter_count,
                "model_type": m.model_type,
                "energy_per_query_wh": m.energy_per_query_wh,
                "water_per_query_ml": m.water_per_query_ml,
                "co2_per_query_g": m.co2_per_query_g,
                "eco_score": m.eco_score,
                "source_paper": m.source_paper,
            }
            key = m.name.strip().lower()
            if key in adjustments:
                d["energy_per_query_wh"] = adjustments[key]
                logger.info("ML.Energy override for model=%s Wh/query=%.6f", m.name, adjustments[key])
            dict_rows.append(d)

        graded = compute_eco_grades(dict_rows)
        now = dt.datetime.now(dt.UTC)
        updated = 0
        for d, m in zip(graded, models, strict=True):
            m.energy_per_query_wh = d.get("energy_per_query_wh")
            m.eco_score = d.get("eco_score")
            m.last_updated = now
            updated += 1

        await session.commit()

    logger.info("apply_model_updates: refreshed %s models", updated)
    return {
        "updated": updated,
        "grades_assigned": updated,
        "ml_energy_keys": len(adjustments),
    }


@flow(name="model_updates_pipeline", log_prints=True)
async def model_updates_pipeline() -> dict[str, Any]:
    ml = await fetch_ml_energy_task()
    hf = await fetch_hf_energy_task()
    stats = await apply_model_updates(ml, hf)
    stats["hf_dataset_seen"] = bool(hf)
    return stats


if __name__ == "__main__":
    import asyncio

    asyncio.run(model_updates_pipeline())
