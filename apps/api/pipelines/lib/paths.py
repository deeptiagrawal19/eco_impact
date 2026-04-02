"""Resolved paths for pipeline data relative to ``apps/api``."""

from __future__ import annotations

from pathlib import Path

PIPELINES_DIR = Path(__file__).resolve().parent.parent
API_ROOT = PIPELINES_DIR.parent
DATA_DIR = API_ROOT / "data"
SUSTAINABILITY_DIR = DATA_DIR / "sustainability"
HARDWARE_DIR = DATA_DIR / "hardware"
MODELS_EXTERNAL_DIR = DATA_DIR / "models"

YOY_METADATA_PATH = SUSTAINABILITY_DIR / "yoy_metadata.json"
