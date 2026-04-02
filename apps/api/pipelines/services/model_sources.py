"""
Optional external benchmarks: ML.Energy-style leaderboard and Hugging Face signals.

Network calls are best-effort; failures are logged and the model update flow continues
with catalog-only DEA grading.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_ML_ENERGY_URL = os.environ.get("ML_ENERGY_API_URL", "https://ml.energy")
DEFAULT_HTTP_TIMEOUT = 25.0


async def fetch_ml_energy_leaderboard() -> dict[str, Any]:
    """
    Try to fetch JSON from ML.Energy (or override via ``ML_ENERGY_API_URL``).

    Configure ``ML_ENERGY_JSON_PATH`` to a local file for offline ingestion.
    """
    path = os.environ.get("ML_ENERGY_JSON_PATH")
    if path and os.path.isfile(path):
        import json
        from pathlib import Path

        data = json.loads(Path(path).read_text(encoding="utf-8"))
        logger.info("Loaded ML.Energy payload from %s", path)
        return data if isinstance(data, dict) else {"items": data}

    base = DEFAULT_ML_ENERGY_URL.rstrip("/")
    candidates = (
        f"{base}/api/leaderboard.json",
        f"{base}/leaderboard.json",
        f"{base}/api/v1/models",
    )
    async with httpx.AsyncClient(timeout=DEFAULT_HTTP_TIMEOUT) as client:
        for url in candidates:
            try:
                r = await client.get(
                    url,
                    headers={"Accept": "application/json"},
                )
                if r.status_code == 200:
                    data = r.json()
                    logger.info("ML.Energy fetch OK url=%s", url)
                    return data if isinstance(data, dict) else {"items": data}
            except Exception as exc:  # noqa: BLE001
                logger.warning("ML.Energy candidate failed url=%s: %s", url, exc)
    logger.warning("ML.Energy: no JSON source available; skipping external energy merge")
    return {}


async def fetch_hf_ai_energy_scores() -> dict[str, Any]:
    """
    Hugging Face dataset / API probes (best-effort).

    Set ``HF_AI_ENERGY_DATASET`` to ``org/name`` plus optional ``HF_TOKEN`` for private sets.
    Falls back to curated ``data/models/hf_energy_hints.json`` when present.
    """
    from pathlib import Path

    from pipelines.lib.paths import MODELS_EXTERNAL_DIR

    hints = MODELS_EXTERNAL_DIR / "hf_energy_hints.json"
    if hints.is_file():
        import json

        data = json.loads(hints.read_text(encoding="utf-8"))
        logger.info("Loaded HF energy hints from %s", hints)
        return data if isinstance(data, dict) else {}

    ds = os.environ.get("HF_AI_ENERGY_DATASET")
    if not ds:
        logger.warning("HF_AI_ENERGY_DATASET not set; skipping HF dataset fetch")
        return {}

    token = os.environ.get("HF_TOKEN")
    headers: dict[str, str] = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://datasets-server.huggingface.co/info?dataset={ds}"
    async with httpx.AsyncClient(timeout=DEFAULT_HTTP_TIMEOUT) as client:
        try:
            r = await client.get(url, headers=headers)
            if r.status_code != 200:
                logger.warning("HF datasets-server info status=%s", r.status_code)
                return {}
            info = r.json()
            logger.info("HF dataset info fetched for %s", ds)
            return {"dataset": ds, "info": info}
        except Exception as exc:  # noqa: BLE001
            logger.warning("HF dataset fetch failed: %s", exc)
            return {}


def extract_energy_adjustments(
    ml_payload: dict[str, Any],
    hf_payload: dict[str, Any],
    *,
    reference_tokens: int,
) -> dict[str, float]:
    """
    Map model name -> energy_per_query_wh adjustments from ML payload if recognizable.

    Supports shapes::
      {"models": [{"name": "...", "energy_joules_per_token": 0.002}, ...]}
      {"items": [{"model": "...", "joules_per_token": 0.001}]}

    ``hf_payload`` reserved for future HF-derived merges (ratings file, etc.).
    """
    _ = hf_payload
    out: dict[str, float] = {}
    rows = (
        ml_payload.get("models")
        or ml_payload.get("items")
        or ml_payload.get("leaderboard")
        or []
    )
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name") or row.get("model") or row.get("model_name")
        jpt = (
            row.get("energy_joules_per_token")
            or row.get("joules_per_token")
            or row.get("joulesPerToken")
        )
        if not name or jpt is None:
            continue
        try:
            j = float(jpt)
        except (TypeError, ValueError):
            continue
        wh_per_query = (j * reference_tokens) / 3600.0
        key = str(name).strip().lower()
        out[key] = wh_per_query
    if out:
        logger.info("Extracted %s ML.Energy energy adjustments", len(out))
    return out
