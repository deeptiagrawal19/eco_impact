"""
DEA-inspired composite efficiency grading for ``ai_models``.

Weights: energy efficiency 40%, water 30%, carbon 30%.
Higher resource use => lower efficiency. Grades by cohort quintiles on composite score:
A = top 20%, B = 20–40%, …, F = bottom 20%.
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

W_ENERGY = 0.40
W_WATER = 0.30
W_CARBON = 0.30


def _invert_normalize(values: list[float]) -> list[float]:
    """Map raw inputs (lower is better) to [0,1] scores (higher is better)."""
    if not values:
        return []
    inv = [1.0 / max(v, 1e-12) for v in values]
    lo, hi = min(inv), max(inv)
    if math.isclose(lo, hi):
        return [0.5] * len(values)
    return [(x - lo) / (hi - lo) for x in inv]


def _quantile_grade(score: float, qs: list[float]) -> str:
    """qs = [q20, q40, q60, q80] on composite distribution (higher better)."""
    if score >= qs[3]:
        return "A"
    if score >= qs[2]:
        return "B"
    if score >= qs[1]:
        return "C"
    if score >= qs[0]:
        return "D"
    return "F"


def compute_eco_grades(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    For each row dict with optional energy_per_query_wh, water_per_query_ml, co2_per_query_g,
    add keys ``composite_efficiency`` and ``eco_score`` (A–F).

    Rows must include ``id`` (uuid str) for traceability; returns same list mutated + copies.
    """
    n = len(rows)
    if n == 0:
        return rows

    energies = [float(r.get("energy_per_query_wh") or 0.0) for r in rows]
    waters = [float(r.get("water_per_query_ml") or 0.0) for r in rows]
    carbons = [float(r.get("co2_per_query_g") or 0.0) for r in rows]

    se = _invert_normalize(energies)
    sw = _invert_normalize(waters)
    sc = _invert_normalize(carbons)

    composites: list[float] = []
    for i in range(n):
        comp = W_ENERGY * se[i] + W_WATER * sw[i] + W_CARBON * sc[i]
        composites.append(comp)

    def _linear_quantiles(vals: list[float], probs: tuple[float, ...]) -> list[float]:
        s = sorted(vals)
        n = len(s)
        if n == 0:
            return [0.0] * len(probs)
        out: list[float] = []
        for p in probs:
            if n == 1:
                out.append(s[0])
                continue
            idx = p * (n - 1)
            lo = int(math.floor(idx))
            hi = int(math.ceil(idx))
            if lo == hi:
                out.append(s[lo])
            else:
                frac = idx - lo
                out.append(s[lo] * (1 - frac) + s[hi] * frac)
        return out

    qs = _linear_quantiles(composites, (0.2, 0.4, 0.6, 0.8))

    for i, r in enumerate(rows):
        r["composite_efficiency"] = round(composites[i], 6)
        r["eco_score"] = _quantile_grade(composites[i], qs)
    logger.info("Assigned DEA-style eco grades for %s models", n)
    return rows
