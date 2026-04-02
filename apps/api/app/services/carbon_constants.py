"""Shared carbon / grid region constants for ingestion and APIs."""

from __future__ import annotations

# Electricity Maps zone keys used for MVP dashboards and ETL.
MVP_CARBON_ZONES: tuple[str, ...] = (
    "US-CAL-CISO",
    "US-NY-NYIS",
    "US-MIDA-PJM",
    "DE",
    "GB",
    "FR",
    "IE",
    "SE",
    "NL",
)
