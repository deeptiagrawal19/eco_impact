"""
Prefect flow: ingest curated sustainability JSON → ``sustainability_reports`` + YoY metadata.

Schedule: weekly Monday 02:00 UTC (see ``prefect.yaml``).
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from typing import Any

from prefect import flow, task
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.tables import SustainabilityReport
from pipelines.lib.paths import SUSTAINABILITY_DIR, YOY_METADATA_PATH
from pipelines.lib.sustainability_io import load_sustainability_json, normalized_report_rows
from pipelines.lib.yoy import compute_yoy_metadata, write_yoy_metadata

logger = logging.getLogger(__name__)

RETRY = dict(retries=3, retry_delay_seconds=60)


@task(name="parse_google_sustainability", **RETRY)
def parse_google_sustainability() -> list[dict[str, Any]]:
    path = SUSTAINABILITY_DIR / "google.json"
    doc = load_sustainability_json(path)
    if doc.get("provider", "").lower() != "google":
        raise ValueError("google.json provider must be google")
    rows = normalized_report_rows(doc)
    logger.info("parse_google_sustainability: %s rows", len(rows))
    return rows


@task(name="parse_microsoft_sustainability", **RETRY)
def parse_microsoft_sustainability() -> list[dict[str, Any]]:
    path = SUSTAINABILITY_DIR / "microsoft.json"
    doc = load_sustainability_json(path)
    if doc.get("provider", "").lower() != "microsoft":
        raise ValueError("microsoft.json provider must be microsoft")
    rows = normalized_report_rows(doc)
    logger.info("parse_microsoft_sustainability: %s rows", len(rows))
    return rows


@task(name="parse_meta_sustainability", **RETRY)
def parse_meta_sustainability() -> list[dict[str, Any]]:
    path = SUSTAINABILITY_DIR / "meta.json"
    doc = load_sustainability_json(path)
    if doc.get("provider", "").lower() != "meta":
        raise ValueError("meta.json provider must be meta")
    rows = normalized_report_rows(doc)
    logger.info("parse_meta_sustainability: %s rows", len(rows))
    return rows


@task(name="parse_amazon_sustainability", **RETRY)
def parse_amazon_sustainability() -> list[dict[str, Any]]:
    path = SUSTAINABILITY_DIR / "amazon.json"
    doc = load_sustainability_json(path)
    if doc.get("provider", "").lower() != "amazon":
        raise ValueError("amazon.json provider must be amazon")
    rows = normalized_report_rows(doc)
    logger.info("parse_amazon_sustainability: %s rows", len(rows))
    return rows


@task(name="load_sustainability_data", **RETRY)
async def load_sustainability_data(
    google_rows: list[dict[str, Any]],
    microsoft_rows: list[dict[str, Any]],
    meta_rows: list[dict[str, Any]],
    amazon_rows: list[dict[str, Any]],
) -> int:
    """Upsert all curated rows into PostgreSQL."""
    flat = [*google_rows, *microsoft_rows, *meta_rows, *amazon_rows]
    if not flat:
        return 0
    async with async_session_maker() as session:
        count = await _upsert_sustainability(session, flat)
        await session.commit()
    logger.info("load_sustainability_data: upserted %s rows", count)
    return count


async def _upsert_sustainability(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    n = 0
    for row in rows:
        payload = {**row, "id": uuid.uuid4()}
        insert_stmt = pg_insert(SustainabilityReport).values(**payload)
        upsert = insert_stmt.on_conflict_do_update(
            index_elements=["provider", "year"],
            set_={
                "total_electricity_gwh": insert_stmt.excluded.total_electricity_gwh,
                "total_water_gallons": insert_stmt.excluded.total_water_gallons,
                "total_emissions_mtco2e": insert_stmt.excluded.total_emissions_mtco2e,
                "scope1_mtco2e": insert_stmt.excluded.scope1_mtco2e,
                "scope2_mtco2e": insert_stmt.excluded.scope2_mtco2e,
                "scope3_mtco2e": insert_stmt.excluded.scope3_mtco2e,
                "renewable_match_percentage": insert_stmt.excluded.renewable_match_percentage,
                "avg_pue": insert_stmt.excluded.avg_pue,
                "report_url": insert_stmt.excluded.report_url,
            },
        )
        await session.execute(upsert)
        n += 1
    return n


@task(name="calculate_yoy_trends", **RETRY)
async def calculate_yoy_trends() -> str:
    """Rebuild YoY metadata JSON from the database snapshot."""
    async with async_session_maker() as session:
        res = await session.execute(
            select(SustainabilityReport).order_by(
                SustainabilityReport.provider,
                SustainabilityReport.year,
            )
        )
        db_rows = res.scalars().all()

    by_provider: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in db_rows:
        by_provider[r.provider].append(
            {
                "year": r.year,
                "total_electricity_gwh": r.total_electricity_gwh,
                "total_water_gallons": r.total_water_gallons,
                "total_emissions_mtco2e": r.total_emissions_mtco2e,
                "renewable_match_percentage": r.renewable_match_percentage,
                "avg_pue": r.avg_pue,
            }
        )

    meta = compute_yoy_metadata(dict(by_provider))
    write_yoy_metadata(YOY_METADATA_PATH, meta)
    logger.info("calculate_yoy_trends: wrote %s", YOY_METADATA_PATH)
    return str(YOY_METADATA_PATH)


@flow(name="sustainability_reports_pipeline", log_prints=True)
async def sustainability_reports_pipeline() -> dict[str, Any]:
    g = parse_google_sustainability()
    m = parse_microsoft_sustainability()
    meta = parse_meta_sustainability()
    amz = parse_amazon_sustainability()
    n = await load_sustainability_data(g, m, meta, amz)
    path = await calculate_yoy_trends()
    return {"rows_upserted": n, "yoy_metadata_path": path}


if __name__ == "__main__":
    import asyncio

    asyncio.run(sustainability_reports_pipeline())
