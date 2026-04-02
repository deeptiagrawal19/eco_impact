"""Energy, carbon, and water estimates from model baselines, facility PUE/WUE, and grid data."""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import AIModel, CarbonIntensityReading, ProviderDataCenter

logger = logging.getLogger(__name__)

REFERENCE_TOKEN_COUNT = 500
DEFAULT_PUE = 1.2
DEFAULT_WUE_L_PER_KWH = 1.8
THINKING_TOKEN_MULTIPLIER = 4.0

# Indirect water: gal/MWh (generation); convert to L per kWh of that fuel's share.
L_PER_GAL = 3.78541
WATER_GAL_PER_MWH_COAL = 19_185.0
WATER_GAL_PER_MWH_GAS = 2_800.0


def _gal_mwh_to_l_per_kwh(gal_per_mwh: float) -> float:
    """Convert gal/MWh (plant-level) to liters per kWh of output."""
    return (gal_per_mwh * L_PER_GAL) / 1000.0


COAL_INDIRECT_L_PER_KWH = _gal_mwh_to_l_per_kwh(WATER_GAL_PER_MWH_COAL)
GAS_INDIRECT_L_PER_KWH = _gal_mwh_to_l_per_kwh(WATER_GAL_PER_MWH_GAS)


METHODOLOGY_NOTE = (
    "Uses catalog energy-per-query (Wh), scaled to token count and workload type; "
    "PUE from facility data or 1.2 default; grid CO2 from carbon_intensity_readings; "
    "water from WUE (facility + indirect generation mix)."
)


QueryType = Literal["text", "image", "video", "multimodal"]


@dataclass
class ModelComparisonRow:
    """Single row from :meth:`AImpactCalculator.compare_models`."""

    model_id: str
    model_name: str
    provider: str
    energy_wh: float
    carbon_g: dict[str, float | None]
    water_ml: dict[str, float | None]
    eco_score: str | None
    percentage_vs_best: float


def _is_reasoning_model(model: AIModel) -> bool:
    name = (model.name or "").lower()
    if "o3" in name or "o1-preview" in name or "reasoning" in name:
        return True
    if model.model_type and "reason" in model.model_type.lower():
        return True
    return False


class AImpactCalculator:
    """
    Estimate Wh, gCO₂, and ml H₂O for AI inference given model, workload shape,
    and (optional) grid region for marginal/average carbon and water mix proxy.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        default_pue: float = DEFAULT_PUE,
        default_wue_l_per_kwh: float = DEFAULT_WUE_L_PER_KWH,
        thinking_multiplier: float = THINKING_TOKEN_MULTIPLIER,
        image_count: int = 1,
    ) -> None:
        self._session = session
        self._default_pue = default_pue
        self._default_wue = default_wue_l_per_kwh
        self._thinking_multiplier = thinking_multiplier
        self._default_image_count = max(1, image_count)

    async def _resolve_pue_wue(self, provider: str | None) -> tuple[float, float]:
        """Best-effort PUE/WUE from a provider data center row; else defaults."""
        if not provider:
            return self._default_pue, self._default_wue
        stmt = (
            select(ProviderDataCenter)
            .where(func.lower(ProviderDataCenter.provider) == provider.lower())
            .limit(5)
        )
        res = await self._session.execute(stmt)
        rows = list(res.scalars().all())
        if not rows:
            return self._default_pue, self._default_wue
        # Prefer explicitly set PUE/WUE averages across sample DCs
        pues = [r.pue for r in rows if r.pue is not None]
        wues = [r.wue for r in rows if r.wue is not None]
        pue = float(sum(pues) / len(pues)) if pues else self._default_pue
        wue = float(sum(wues) / len(wues)) if wues else self._default_wue
        return pue, wue

    async def _latest_grid_row(self, region: str | None) -> CarbonIntensityReading | None:
        if region:
            stmt = (
                select(CarbonIntensityReading)
                .where(CarbonIntensityReading.region == region)
                .order_by(desc(CarbonIntensityReading.time))
                .limit(1)
            )
        else:
            stmt = (
                select(CarbonIntensityReading)
                .order_by(desc(CarbonIntensityReading.time))
                .limit(1)
            )
        res = await self._session.execute(stmt)
        return res.scalar_one_or_none()

    def estimate_core_energy_wh(
        self,
        model: AIModel,
        *,
        query_type: QueryType = "text",
        token_count: int = REFERENCE_TOKEN_COUNT,
        image_count: int | None = None,
    ) -> float:
        """
        IT-load electricity before PUE (Wh): baseline × token scale × reasoning × image count.
        """
        base = model.energy_per_query_wh
        if base is None or base <= 0:
            base = 0.1
        token_scale = max(0.1, token_count) / float(REFERENCE_TOKEN_COUNT)
        energy = float(base * token_scale)

        if _is_reasoning_model(model):
            energy *= self._thinking_multiplier

        n_img = self._default_image_count if image_count is None else max(1, image_count)
        if query_type == "image":
            energy *= n_img

        return energy

    def estimate_energy(
        self,
        model: AIModel,
        *,
        query_type: QueryType = "text",
        token_count: int = REFERENCE_TOKEN_COUNT,
        image_count: int | None = None,
    ) -> float:
        """Total Wh using default PUE when an async session PUE lookup is not available."""
        return float(
            self.estimate_core_energy_wh(
                model,
                query_type=query_type,
                token_count=token_count,
                image_count=image_count,
            )
            * self._default_pue
        )

    async def estimate_energy_with_pue(
        self,
        model: AIModel,
        *,
        query_type: QueryType = "text",
        token_count: int = REFERENCE_TOKEN_COUNT,
        image_count: int | None = None,
    ) -> float:
        """Total facility Wh (IT × provider PUE if known, else default)."""
        core = self.estimate_core_energy_wh(
            model,
            query_type=query_type,
            token_count=token_count,
            image_count=image_count,
        )
        pue, _ = await self._resolve_pue_wue(model.provider)
        return float(core * pue)

    def _carbon_from_wh(self, wh: float, g_per_kwh: float | None) -> float | None:
        if g_per_kwh is None:
            return None
        kwh = wh / 1000.0
        return float(kwh * g_per_kwh)

    async def estimate_carbon(
        self,
        model: AIModel,
        *,
        region: str | None = None,
        energy_wh: float | None = None,
        query_type: QueryType = "text",
        token_count: int = REFERENCE_TOKEN_COUNT,
        image_count: int | None = None,
    ) -> dict[str, float | None]:
        """
        gCO₂eq for average and marginal intensities (``carbon_intensity_*`` from DB).

        Falls back to 420 g/kWh if no grid row / missing fields.
        """
        wh = energy_wh
        if wh is None:
            wh = await self.estimate_energy_with_pue(
                model,
                query_type=query_type,
                token_count=token_count,
                image_count=image_count,
            )
        row = await self._latest_grid_row(region)
        avg_g = row.carbon_intensity_avg if row else None
        marg_g = row.carbon_intensity_marginal if row else None
        fallback = 420.0
        avg_eff = avg_g if avg_g is not None else fallback
        marg_eff = marg_g if marg_g is not None else avg_eff
        return {
            "energy_wh": float(wh),
            "carbon_g_avg": self._carbon_from_wh(wh, avg_eff),
            "carbon_g_marginal": self._carbon_from_wh(wh, marg_eff),
            "carbon_intensity_avg_g_per_kwh": float(avg_eff),
            "carbon_intensity_marginal_g_per_kwh": float(marg_eff),
            "grid_region_used": region or (row.region if row else None),
        }

    async def estimate_water(
        self,
        model: AIModel,
        *,
        region: str | None = None,
        energy_wh: float | None = None,
        query_type: QueryType = "text",
        token_count: int = REFERENCE_TOKEN_COUNT,
        image_count: int | None = None,
    ) -> dict[str, float | None]:
        """
        Direct (datacenter WUE) and indirect (thermal mix water intensity) in ml.
        """
        wh = energy_wh
        if wh is None:
            wh = await self.estimate_energy_with_pue(
                model,
                query_type=query_type,
                token_count=token_count,
                image_count=image_count,
            )
        kwh = wh / 1000.0
        _, wue = await self._resolve_pue_wue(model.provider)
        direct_l = kwh * wue

        row = await self._latest_grid_row(region)
        fossil_pct = row.fossil_fuel_percentage if row and row.fossil_fuel_percentage is not None else 50.0
        ren_pct = row.renewable_percentage if row and row.renewable_percentage is not None else 30.0
        fossil = max(0.0, min(100.0, fossil_pct)) / 100.0
        # Split fossil between coal and gas for weighting indirect water.
        coal_share_fossil = 0.35
        gas_share_fossil = 0.65
        indirect_l_per_kwh = fossil * (
            coal_share_fossil * COAL_INDIRECT_L_PER_KWH + gas_share_fossil * GAS_INDIRECT_L_PER_KWH
        )
        # Ren et al.: renewables ~0 for operational water intensity of PV/w-ind.
        _ = ren_pct

        indirect_l = kwh * indirect_l_per_kwh
        total_l = direct_l + indirect_l
        return {
            "energy_wh": float(wh),
            "direct_ml": float(direct_l * 1000.0),
            "indirect_ml": float(indirect_l * 1000.0),
            "total_ml": float(total_l * 1000.0),
            "wue_l_per_kwh": float(wue),
        }

    @staticmethod
    def get_equivalents(
        energy_wh: float,
        carbon_g: float,
        water_ml: float,
    ) -> dict[str, float]:
        """Real-world comparison metrics (22 kg CO₂/tree/year per user spec)."""
        tree_g_per_sec = 22_000.0 / (365.0 * 24.0 * 3600.0)  # ~22 kg CO₂/tree/year → g/s
        return {
            "smartphone_charges": energy_wh / 12.0,
            "google_searches": energy_wh / 0.3,
            "driving_km_equivalent": carbon_g / 120.0 if carbon_g else 0.0,
            "water_bottles_500ml": water_ml / 500.0,
            "hours_led_bulb_10w": energy_wh / 10.0,
            "tree_seconds_offset": carbon_g / tree_g_per_sec if tree_g_per_sec and carbon_g else 0.0,
        }

    def _matches_task(self, model: AIModel, task_type: str) -> bool:
        m = (model.model_type or "text").lower()
        t = task_type.lower()
        if t == "text":
            return m in ("text", "multimodal", "")
        if t == "image":
            return m in ("image", "multimodal")
        if t == "video":
            return m in ("video", "multimodal")
        if t == "multimodal":
            return True
        return True

    @staticmethod
    def _query_type_from_task(task_type: str) -> QueryType:
        t = task_type.lower()
        if t == "image":
            return "image"
        if t == "video":
            return "video"
        if t == "multimodal":
            return "multimodal"
        return "text"

    async def compare_models(
        self,
        *,
        task_type: str = "text",
        region: str | None = None,
        token_count: int = REFERENCE_TOKEN_COUNT,
    ) -> list[ModelComparisonRow]:
        """All models matching ``task_type``, sorted by total energy (most efficient first)."""
        stmt = select(AIModel).order_by(AIModel.name)
        res = await self._session.execute(stmt)
        models = [m for m in res.scalars().all() if self._matches_task(m, task_type)]
        qt = self._query_type_from_task(task_type)

        rows: list[ModelComparisonRow] = []
        for m in models:
            try:
                wh = await self.estimate_energy_with_pue(
                    m,
                    query_type=qt,
                    token_count=token_count,
                )
                carbon = await self.estimate_carbon(
                    m,
                    region=region,
                    energy_wh=wh,
                    query_type=qt,
                    token_count=token_count,
                )
                water = await self.estimate_water(
                    m,
                    region=region,
                    energy_wh=wh,
                    query_type=qt,
                    token_count=token_count,
                )
                carbon_avg = carbon.get("carbon_g_avg") or 0.0
                water_total = water.get("total_ml") or 0.0
                rows.append(
                    ModelComparisonRow(
                        model_id=str(m.id),
                        model_name=m.name,
                        provider=m.provider,
                        energy_wh=wh,
                        carbon_g={
                            "avg": carbon.get("carbon_g_avg"),
                            "marginal": carbon.get("carbon_g_marginal"),
                        },
                        water_ml={
                            "direct": water.get("direct_ml"),
                            "indirect": water.get("indirect_ml"),
                            "total": water.get("total_ml"),
                        },
                        eco_score=m.eco_score,
                        percentage_vs_best=0.0,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("compare_models skip %s: %s", m.name, exc)

        rows.sort(key=lambda r: r.energy_wh)
        if not rows:
            return []
        best = rows[0].energy_wh
        for r in rows:
            if best > 0:
                r.percentage_vs_best = max(0.0, (r.energy_wh - best) / best * 100.0)
            else:
                r.percentage_vs_best = 0.0
        return rows


async def get_model_by_identifier(
    session: AsyncSession,
    model: str,
) -> AIModel | None:
    """Resolve ``model`` as UUID or case-insensitive name."""
    model = model.strip()
    try:
        mid = uuid.UUID(model)
        res = await session.execute(select(AIModel).where(AIModel.id == mid))
        row = res.scalar_one_or_none()
        if row:
            return row
    except ValueError:
        pass
    stmt = select(AIModel).where(func.lower(AIModel.name) == model.lower())
    res = await session.execute(stmt)
    return res.scalars().first()
