"""Year-over-year metrics for sustainability reports (pipeline metadata JSON)."""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

METRICS = (
    "electricity_gwh",
    "water_gallons",
    "emissions_mtco2e",
    "renewable_pct",
    "pue",
)


def _pct_change(prev: float | None, cur: float | None) -> float | None:
    if prev is None or cur is None:
        return None
    if prev == 0:
        return None
    return round(100.0 * (cur - prev) / prev, 4)


def compute_yoy_metadata(
    reports_by_provider: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """
    Build YoY growth metadata per provider/year.

    ``reports_by_provider`` maps provider -> list of
    {year:int, total_electricity_gwh, total_water_gallons, ...}
    sorted by year ascending.
    """
    out: dict[str, Any] = {
        "updated_at": dt.datetime.now(dt.UTC).isoformat(),
        "by_provider": {},
    }
    key_map = {
        "electricity_gwh": "total_electricity_gwh",
        "water_gallons": "total_water_gallons",
        "emissions_mtco2e": "total_emissions_mtco2e",
        "renewable_pct": "renewable_match_percentage",
        "pue": "avg_pue",
    }
    for prov, rows in reports_by_provider.items():
        sorted_rows = sorted(rows, key=lambda r: r["year"])
        yoy_list: list[dict[str, Any]] = []
        for i, row in enumerate(sorted_rows):
            entry: dict[str, Any] = {"year": row["year"]}
            if i == 0:
                for m in METRICS:
                    entry[f"{m}_yoy_pct"] = None
            else:
                prev = sorted_rows[i - 1]
                for label, col in key_map.items():
                    pv, cv = prev.get(col), row.get(col)
                    entry[f"{label}_yoy_pct"] = _pct_change(
                        float(pv) if isinstance(pv, (int, float)) else None,
                        float(cv) if isinstance(cv, (int, float)) else None,
                    )
            yoy_list.append(entry)
        out["by_provider"][prov] = yoy_list
    logger.info("Computed YoY metadata for providers: %s", list(out["by_provider"]))
    return out


def write_yoy_metadata(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    logger.info("Wrote YoY metadata to %s", path)
