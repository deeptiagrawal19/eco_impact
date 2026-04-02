"""SQLAlchemy 2.0 table definitions for eco-impact-dashboard."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import (
    BigInteger,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CarbonIntensityReading(Base):
    """
    Time-series carbon grid data (TimescaleDB hypertable on ``time``).

    Composite primary key (time, region, source) supports multiple ingestion sources
    per region per timestamp after hypertable creation.
    """

    __tablename__ = "carbon_intensity_readings"
    __table_args__ = (PrimaryKeyConstraint("time", "region", "source"),)

    time: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    region: Mapped[str] = mapped_column(Text, nullable=False)
    carbon_intensity_avg: Mapped[float | None] = mapped_column(Double, nullable=True)
    carbon_intensity_marginal: Mapped[float | None] = mapped_column(Double, nullable=True)
    fossil_fuel_percentage: Mapped[float | None] = mapped_column(Double, nullable=True)
    renewable_percentage: Mapped[float | None] = mapped_column(Double, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)


class AIModel(Base):
    """Catalog of AI models with sustainability-related per-query estimates."""

    __tablename__ = "ai_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    parameter_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    model_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    energy_per_query_wh: Mapped[float | None] = mapped_column(Double, nullable=True)
    water_per_query_ml: Mapped[float | None] = mapped_column(Double, nullable=True)
    co2_per_query_g: Mapped[float | None] = mapped_column(Double, nullable=True)
    eco_score: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_paper: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_updated: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=lambda: dt.datetime.now(dt.UTC),
        onupdate=lambda: dt.datetime.now(dt.UTC),
    )

    energy_estimates: Mapped[list[EnergyEstimate]] = relationship(
        back_populates="model",
        cascade="all, delete-orphan",
    )


class ProviderDataCenter(Base):
    """Hyperscaler / provider facility metadata tied to grid regions."""

    __tablename__ = "provider_data_centers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    region: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    grid_region: Mapped[str | None] = mapped_column(Text, nullable=True)
    pue: Mapped[float | None] = mapped_column(Double, nullable=True)
    wue: Mapped[float | None] = mapped_column(Double, nullable=True)
    capacity_mw: Mapped[float | None] = mapped_column(Double, nullable=True)
    renewable_percentage: Mapped[float | None] = mapped_column(Double, nullable=True)
    cooling_type: Mapped[str | None] = mapped_column(Text, nullable=True)


class SustainabilityReport(Base):
    """Aggregated annual sustainability metrics by cloud / AI provider."""

    __tablename__ = "sustainability_reports"
    __table_args__ = (UniqueConstraint("provider", "year", name="uq_sustainability_provider_year"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_electricity_gwh: Mapped[float | None] = mapped_column(Double, nullable=True)
    total_water_gallons: Mapped[float | None] = mapped_column(Double, nullable=True)
    total_emissions_mtco2e: Mapped[float | None] = mapped_column(Double, nullable=True)
    scope1_mtco2e: Mapped[float | None] = mapped_column(Double, nullable=True)
    scope2_mtco2e: Mapped[float | None] = mapped_column(Double, nullable=True)
    scope3_mtco2e: Mapped[float | None] = mapped_column(Double, nullable=True)
    renewable_match_percentage: Mapped[float | None] = mapped_column(Double, nullable=True)
    avg_pue: Mapped[float | None] = mapped_column(Double, nullable=True)
    report_url: Mapped[str | None] = mapped_column(Text, nullable=True)


class EnergyEstimate(Base):
    """
    Time-bucketed rollups of modeled energy / water / carbon (TimescaleDB hypertable).

    Composite primary key (time, model_id) after hypertable creation.
    """

    __tablename__ = "energy_estimates"
    __table_args__ = (PrimaryKeyConstraint("time", "model_id"),)

    time: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_models.id", ondelete="CASCADE"),
        nullable=False,
    )
    estimated_queries: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_energy_mwh: Mapped[float | None] = mapped_column(Double, nullable=True)
    total_water_liters: Mapped[float | None] = mapped_column(Double, nullable=True)
    total_co2_tonnes: Mapped[float | None] = mapped_column(Double, nullable=True)
    avg_carbon_intensity: Mapped[float | None] = mapped_column(Double, nullable=True)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)

    model: Mapped[AIModel] = relationship(back_populates="energy_estimates")


class GPUBenchmark(Base):
    """Accelerator hardware reference data for efficiency comparisons."""

    __tablename__ = "gpu_benchmarks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    gpu_name: Mapped[str] = mapped_column(Text, nullable=False)
    tdp_watts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    architecture: Mapped[str | None] = mapped_column(Text, nullable=True)
    memory_gb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_bandwidth_tbps: Mapped[float | None] = mapped_column(Double, nullable=True)
    inference_tflops: Mapped[float | None] = mapped_column(Double, nullable=True)
    training_tflops: Mapped[float | None] = mapped_column(Double, nullable=True)
    energy_efficiency_tflops_per_watt: Mapped[float | None] = mapped_column(Double, nullable=True)
    release_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
