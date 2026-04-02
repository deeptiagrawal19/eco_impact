"""
Prefect flow: ingest ``data/hardware/gpus.json`` → ``gpu_benchmarks`` (upsert by name).

Schedule: monthly day 1 03:00 UTC (see ``prefect.yaml``).
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from prefect import flow, task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.tables import GPUBenchmark
from pipelines.lib.paths import HARDWARE_DIR

logger = logging.getLogger(__name__)
RETRY = dict(retries=3, retry_delay_seconds=60)


@task(name="load_gpu_json", **RETRY)
def load_gpu_json() -> list[dict[str, Any]]:
    path = HARDWARE_DIR / "gpus.json"
    if not path.is_file():
        raise FileNotFoundError(f"GPU data missing: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows = raw.get("gpus")
    if not isinstance(rows, list) or not rows:
        raise ValueError("gpus.json must contain a non-empty 'gpus' array")
    for r in rows:
        if "gpu_name" not in r or "tdp_watts" not in r:
            raise ValueError("Each GPU entry requires gpu_name and tdp_watts")
    logger.info("load_gpu_json: %s SKUs", len(rows))
    return rows


@task(name="upsert_gpu_benchmarks", **RETRY)
async def upsert_gpu_benchmarks(rows: list[dict[str, Any]]) -> int:
    async with async_session_maker() as session:
        n = await _merge_gpus(session, rows)
        await session.commit()
    logger.info("upsert_gpu_benchmarks: merged %s rows", n)
    return n


async def _merge_gpus(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    n = 0
    for row in rows:
        name = str(row["gpu_name"])
        stmt = select(GPUBenchmark).where(GPUBenchmark.gpu_name == name)
        res = await session.execute(stmt)
        existing = res.scalar_one_or_none()
        fields = {
            "tdp_watts": row.get("tdp_watts"),
            "architecture": row.get("architecture"),
            "memory_gb": row.get("memory_gb"),
            "memory_bandwidth_tbps": row.get("memory_bandwidth_tbps"),
            "inference_tflops": row.get("inference_tflops"),
            "training_tflops": row.get("training_tflops"),
            "energy_efficiency_tflops_per_watt": row.get("energy_efficiency_tflops_per_watt"),
            "release_year": row.get("release_year"),
            "source": row.get("source"),
        }
        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
        else:
            session.add(
                GPUBenchmark(
                    id=uuid.uuid4(),
                    gpu_name=name,
                    **fields,
                )
            )
        n += 1
    return n


@flow(name="gpu_benchmarks_pipeline", log_prints=True)
async def gpu_benchmarks_pipeline() -> dict[str, Any]:
    rows = load_gpu_json()
    n = await upsert_gpu_benchmarks(rows)
    return {"gpus_upserted": n}


if __name__ == "__main__":
    import asyncio

    asyncio.run(gpu_benchmarks_pipeline())
