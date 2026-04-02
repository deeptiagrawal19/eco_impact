"""Load and normalize curated sustainability JSON files."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REQUIRED_TOP = ("provider", "years")


def load_sustainability_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Sustainability data file missing: {path}")
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    for k in REQUIRED_TOP:
        if k not in raw:
            raise ValueError(f"{path}: missing required key '{k}'")
    if not isinstance(raw["years"], dict):
        raise ValueError(f"{path}: 'years' must be an object")
    return raw


def normalized_report_rows(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten one provider document into DB row dicts (no id)."""
    provider = str(doc["provider"]).strip().lower()
    report_url = doc.get("report_url")
    rows: list[dict[str, Any]] = []
    for year_str, metrics in doc["years"].items():
        try:
            year = int(year_str)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid year key {year_str!r}") from exc
        if not isinstance(metrics, dict):
            raise ValueError(f"Year {year}: metrics must be object")
        rows.append(
            {
                "provider": provider,
                "year": year,
                "total_electricity_gwh": metrics.get("electricity_gwh"),
                "total_water_gallons": metrics.get("water_gallons"),
                "total_emissions_mtco2e": metrics.get("emissions_mtco2e"),
                "scope1_mtco2e": metrics.get("scope1_mtco2e"),
                "scope2_mtco2e": metrics.get("scope2_mtco2e"),
                "scope3_mtco2e": metrics.get("scope3_mtco2e"),
                "renewable_match_percentage": metrics.get("renewable_pct"),
                "avg_pue": metrics.get("pue"),
                "report_url": report_url if isinstance(report_url, str) else None,
            }
        )
    logger.info("Normalized %s sustainability rows for provider=%s", len(rows), provider)
    return rows
