"""Initial schema: relational tables and TimescaleDB hypertables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20250330_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE"))

    op.create_table(
        "ai_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("parameter_count", sa.BigInteger(), nullable=True),
        sa.Column("model_type", sa.Text(), nullable=True),
        sa.Column("energy_per_query_wh", sa.Double(), nullable=True),
        sa.Column("water_per_query_ml", sa.Double(), nullable=True),
        sa.Column("co2_per_query_g", sa.Double(), nullable=True),
        sa.Column("eco_score", sa.Text(), nullable=True),
        sa.Column("source_paper", sa.Text(), nullable=True),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "gpu_benchmarks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("gpu_name", sa.Text(), nullable=False),
        sa.Column("tdp_watts", sa.Integer(), nullable=True),
        sa.Column("architecture", sa.Text(), nullable=True),
        sa.Column("memory_gb", sa.Integer(), nullable=True),
        sa.Column("memory_bandwidth_tbps", sa.Double(), nullable=True),
        sa.Column("inference_tflops", sa.Double(), nullable=True),
        sa.Column("training_tflops", sa.Double(), nullable=True),
        sa.Column("energy_efficiency_tflops_per_watt", sa.Double(), nullable=True),
        sa.Column("release_year", sa.Integer(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
    )

    op.create_table(
        "provider_data_centers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("region", sa.Text(), nullable=False),
        sa.Column("country", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Double(), nullable=True),
        sa.Column("longitude", sa.Double(), nullable=True),
        sa.Column("grid_region", sa.Text(), nullable=True),
        sa.Column("pue", sa.Double(), nullable=True),
        sa.Column("wue", sa.Double(), nullable=True),
        sa.Column("capacity_mw", sa.Double(), nullable=True),
        sa.Column("renewable_percentage", sa.Double(), nullable=True),
        sa.Column("cooling_type", sa.Text(), nullable=True),
    )

    op.create_table(
        "sustainability_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("total_electricity_gwh", sa.Double(), nullable=True),
        sa.Column("total_water_gallons", sa.Double(), nullable=True),
        sa.Column("total_emissions_mtco2e", sa.Double(), nullable=True),
        sa.Column("scope1_mtco2e", sa.Double(), nullable=True),
        sa.Column("scope2_mtco2e", sa.Double(), nullable=True),
        sa.Column("scope3_mtco2e", sa.Double(), nullable=True),
        sa.Column("renewable_match_percentage", sa.Double(), nullable=True),
        sa.Column("avg_pue", sa.Double(), nullable=True),
        sa.Column("report_url", sa.Text(), nullable=True),
        sa.UniqueConstraint("provider", "year", name="uq_sustainability_provider_year"),
    )

    op.create_table(
        "carbon_intensity_readings",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("region", sa.Text(), nullable=False),
        sa.Column("carbon_intensity_avg", sa.Double(), nullable=True),
        sa.Column("carbon_intensity_marginal", sa.Double(), nullable=True),
        sa.Column("fossil_fuel_percentage", sa.Double(), nullable=True),
        sa.Column("renewable_percentage", sa.Double(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("time", "region", "source"),
    )

    op.execute(
        sa.text(
            "SELECT create_hypertable('carbon_intensity_readings', 'time', if_not_exists => TRUE)"
        )
    )

    op.create_table(
        "energy_estimates",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "model_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_models.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("estimated_queries", sa.BigInteger(), nullable=True),
        sa.Column("total_energy_mwh", sa.Double(), nullable=True),
        sa.Column("total_water_liters", sa.Double(), nullable=True),
        sa.Column("total_co2_tonnes", sa.Double(), nullable=True),
        sa.Column("avg_carbon_intensity", sa.Double(), nullable=True),
        sa.Column("region", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("time", "model_id"),
    )

    op.execute(
        sa.text("SELECT create_hypertable('energy_estimates', 'time', if_not_exists => TRUE)")
    )


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS energy_estimates CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS carbon_intensity_readings CASCADE"))
    op.drop_table("sustainability_reports")
    op.drop_table("provider_data_centers")
    op.drop_table("gpu_benchmarks")
    op.drop_table("ai_models")
    op.execute(sa.text("DROP EXTENSION IF EXISTS timescaledb CASCADE"))
