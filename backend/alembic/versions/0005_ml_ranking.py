"""stage 6: ML model runs and predictions

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("tickers", sa.JSON(), nullable=False),
        sa.Column("benchmark_ticker", sa.String(length=16), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("label_horizon_days", sa.Integer(), nullable=False),
        sa.Column("training_lookback_days", sa.Integer(), nullable=False),
        sa.Column("selected_model", sa.String(length=32), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('running','completed','failed')",
            name="ck_model_runs_status_valid",
        ),
        sa.CheckConstraint(
            "selected_model IN ('logistic_regression','xgboost')",
            name="ck_model_runs_selected_model_valid",
        ),
        sa.CheckConstraint("start_date < end_date", name="ck_model_runs_dates_ordered"),
        sa.CheckConstraint(
            "label_horizon_days > 0", name="ck_model_runs_label_horizon_pos"
        ),
        sa.CheckConstraint(
            "training_lookback_days > 0", name="ck_model_runs_training_lookback_pos"
        ),
    )
    op.create_index("ix_model_runs_created_at", "model_runs", ["created_at"])

    op.create_table(
        "model_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("model_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("model_name", sa.String(length=32), nullable=False),
        sa.Column("score", sa.Numeric(10, 8), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("label", sa.Integer(), nullable=True),
        sa.Column("forward_return", sa.Numeric(18, 8), nullable=True),
        sa.Column("benchmark_forward_return", sa.Numeric(18, 8), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            ondelete="CASCADE",
            name="fk_model_predictions_asset_id_assets",
        ),
        sa.ForeignKeyConstraint(
            ["model_run_id"],
            ["model_runs.id"],
            ondelete="CASCADE",
            name="fk_model_predictions_model_run_id_model_runs",
        ),
        sa.UniqueConstraint(
            "model_run_id",
            "date",
            "asset_id",
            "model_name",
            name="uq_model_predictions_run_date_asset_model",
        ),
        sa.CheckConstraint(
            "model_name IN ('logistic_regression','xgboost')",
            name="ck_model_predictions_model_name_valid",
        ),
        sa.CheckConstraint(
            "score >= 0 AND score <= 1", name="ck_model_predictions_score_unit"
        ),
        sa.CheckConstraint("rank > 0", name="ck_model_predictions_rank_pos"),
        sa.CheckConstraint(
            "label IS NULL OR label IN (0, 1)", name="ck_model_predictions_label"
        ),
    )
    op.create_index(
        "ix_model_predictions_run_date_model",
        "model_predictions",
        ["model_run_id", "date", "model_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_model_predictions_run_date_model", table_name="model_predictions")
    op.drop_table("model_predictions")
    op.drop_index("ix_model_runs_created_at", table_name="model_runs")
    op.drop_table("model_runs")
