"""stage 7: experiment sweeps

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "experiment_sweeps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'queued'"),
        ),
        sa.Column("base_request", sa.JSON(), nullable=False),
        sa.Column("sweep_parameters", sa.JSON(), nullable=False),
        sa.Column("total_runs", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "completed_runs", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("failed_runs", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('backtest','forecast')",
            name="ck_experiment_sweeps_kind_valid",
        ),
        sa.CheckConstraint(
            "status IN ('queued','running','completed','partial','failed')",
            name="ck_experiment_sweeps_status_valid",
        ),
        sa.CheckConstraint(
            "total_runs >= 0", name="ck_experiment_sweeps_total_runs_nonneg"
        ),
        sa.CheckConstraint(
            "completed_runs >= 0",
            name="ck_experiment_sweeps_completed_runs_nonneg",
        ),
        sa.CheckConstraint(
            "failed_runs >= 0", name="ck_experiment_sweeps_failed_runs_nonneg"
        ),
    )
    op.create_index("ix_experiment_sweeps_created_at", "experiment_sweeps", ["created_at"])

    op.create_table(
        "experiment_sweep_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sweep_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_index", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("backtest_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("forecast_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'queued'"),
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
            ["sweep_id"],
            ["experiment_sweeps.id"],
            ondelete="CASCADE",
            name="fk_sweep_runs_sweep_id_experiment_sweeps",
        ),
        sa.ForeignKeyConstraint(
            ["backtest_id"],
            ["backtests.id"],
            ondelete="SET NULL",
            name="fk_sweep_runs_backtest_id_backtests",
        ),
        sa.ForeignKeyConstraint(
            ["forecast_id"],
            ["forecasts.id"],
            ondelete="SET NULL",
            name="fk_sweep_runs_forecast_id_forecasts",
        ),
        sa.UniqueConstraint("sweep_id", "run_index", name="uq_sweep_runs_sweep_index"),
        sa.CheckConstraint(
            "kind IN ('backtest','forecast')",
            name="ck_experiment_sweep_runs_kind_valid",
        ),
        sa.CheckConstraint(
            "status IN ('queued','running','completed','failed')",
            name="ck_experiment_sweep_runs_status_valid",
        ),
        sa.CheckConstraint(
            "run_index >= 0", name="ck_experiment_sweep_runs_index_nonneg"
        ),
    )
    op.create_index("ix_sweep_runs_sweep_id", "experiment_sweep_runs", ["sweep_id"])
    op.create_index("ix_sweep_runs_backtest_id", "experiment_sweep_runs", ["backtest_id"])
    op.create_index("ix_sweep_runs_forecast_id", "experiment_sweep_runs", ["forecast_id"])


def downgrade() -> None:
    op.drop_index("ix_sweep_runs_forecast_id", table_name="experiment_sweep_runs")
    op.drop_index("ix_sweep_runs_backtest_id", table_name="experiment_sweep_runs")
    op.drop_index("ix_sweep_runs_sweep_id", table_name="experiment_sweep_runs")
    op.drop_table("experiment_sweep_runs")
    op.drop_index("ix_experiment_sweeps_created_at", table_name="experiment_sweeps")
    op.drop_table("experiment_sweeps")
