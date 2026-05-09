"""stage 2: backtests, trades, portfolio_values

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-09

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "backtests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("strategy", sa.String(length=64), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("initial_cash", sa.Numeric(18, 6), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("benchmark_ticker", sa.String(length=16), nullable=True),
        sa.Column(
            "transaction_cost_bps", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("final_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("total_return", sa.Numeric(18, 8), nullable=True),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default=sa.text("'running'")
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
            "status IN ('running','completed','failed')", name="ck_backtests_status_valid"
        ),
        sa.CheckConstraint("start_date < end_date", name="ck_backtests_dates_ordered"),
    )

    op.create_table(
        "trades",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("backtest_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("side", sa.String(length=4), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("price", sa.Numeric(18, 6), nullable=False),
        sa.Column(
            "transaction_cost", sa.Numeric(18, 6), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("notional", sa.Numeric(18, 6), nullable=False),
        sa.ForeignKeyConstraint(
            ["backtest_id"],
            ["backtests.id"],
            ondelete="CASCADE",
            name="fk_trades_backtest_id_backtests",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            ondelete="RESTRICT",
            name="fk_trades_asset_id_assets",
        ),
        sa.CheckConstraint("side IN ('buy','sell')", name="ck_trades_side_valid"),
    )
    op.create_index("ix_trades_backtest_id_date", "trades", ["backtest_id", "date"])

    op.create_table(
        "portfolio_values",
        sa.Column("backtest_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("cash", sa.Numeric(18, 6), nullable=False),
        sa.Column("holdings_value", sa.Numeric(18, 6), nullable=False),
        sa.Column("total_value", sa.Numeric(18, 6), nullable=False),
        sa.PrimaryKeyConstraint("backtest_id", "date", name="pk_portfolio_values"),
        sa.ForeignKeyConstraint(
            ["backtest_id"],
            ["backtests.id"],
            ondelete="CASCADE",
            name="fk_portfolio_values_backtest_id_backtests",
        ),
    )


def downgrade() -> None:
    op.drop_table("portfolio_values")
    op.drop_index("ix_trades_backtest_id_date", table_name="trades")
    op.drop_table("trades")
    op.drop_table("backtests")
