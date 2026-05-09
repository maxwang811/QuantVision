"""stage 5: forecasts, forecast_paths, forecast_distribution_bins

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "forecasts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("method", sa.String(length=32), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("initial_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("horizon_months", sa.Integer(), nullable=False),
        sa.Column("horizon_trading_days", sa.Integer(), nullable=False),
        sa.Column("n_simulations", sa.Integer(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column("lookback_start", sa.Date(), nullable=False),
        sa.Column("lookback_end", sa.Date(), nullable=False),
        sa.Column("benchmark_ticker", sa.String(length=16), nullable=True),
        sa.Column("from_backtest_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("random_seed", sa.BigInteger(), nullable=False),
        sa.Column("expected_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("median_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("p5_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("p10_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("p25_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("p75_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("p90_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("p95_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("probability_of_loss", sa.Numeric(8, 6), nullable=True),
        sa.Column("probability_beat_benchmark", sa.Numeric(8, 6), nullable=True),
        sa.Column("annualized_volatility", sa.Numeric(18, 8), nullable=True),
        sa.Column("expected_return", sa.Numeric(18, 8), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'running'"),
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["from_backtest_id"],
            ["backtests.id"],
            ondelete="SET NULL",
            name="fk_forecasts_from_backtest_id_backtests",
        ),
        sa.CheckConstraint(
            "method IN ('monte_carlo','bootstrap','ml_drift')",
            name="ck_forecasts_method_valid",
        ),
        sa.CheckConstraint(
            "status IN ('running','completed','failed')",
            name="ck_forecasts_status_valid",
        ),
        sa.CheckConstraint("horizon_months > 0", name="ck_forecasts_horizon_pos"),
        sa.CheckConstraint("n_simulations > 0", name="ck_forecasts_nsims_pos"),
    )
    op.create_index("ix_forecasts_created_at", "forecasts", ["created_at"])

    op.create_table(
        "forecast_paths",
        sa.Column("forecast_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("path_index", sa.Integer(), nullable=False),
        sa.Column("rank_label", sa.String(length=16), nullable=True),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("forecast_id", "path_index", name="pk_forecast_paths"),
        sa.ForeignKeyConstraint(
            ["forecast_id"],
            ["forecasts.id"],
            ondelete="CASCADE",
            name="fk_forecast_paths_forecast_id_forecasts",
        ),
    )

    op.create_table(
        "forecast_distribution_bins",
        sa.Column("forecast_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bin_index", sa.Integer(), nullable=False),
        sa.Column("bin_lower", sa.Numeric(18, 6), nullable=False),
        sa.Column("bin_upper", sa.Numeric(18, 6), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint(
            "forecast_id", "bin_index", name="pk_forecast_distribution_bins"
        ),
        sa.ForeignKeyConstraint(
            ["forecast_id"],
            ["forecasts.id"],
            ondelete="CASCADE",
            name="fk_forecast_distribution_bins_forecast_id_forecasts",
        ),
    )


def downgrade() -> None:
    op.drop_table("forecast_distribution_bins")
    op.drop_table("forecast_paths")
    op.drop_index("ix_forecasts_created_at", table_name="forecasts")
    op.drop_table("forecasts")
