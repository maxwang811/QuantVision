"""stage 3: risk metrics columns on backtests

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-09

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_NEW_COLUMNS = (
    "annualized_return",
    "volatility",
    "sharpe_ratio",
    "max_drawdown",
    "benchmark_total_return",
    "benchmark_annualized_return",
    "alpha",
    "beta",
    "information_ratio",
    "tracking_error",
)


def upgrade() -> None:
    for col in _NEW_COLUMNS:
        op.add_column("backtests", sa.Column(col, sa.Numeric(18, 8), nullable=True))


def downgrade() -> None:
    for col in reversed(_NEW_COLUMNS):
        op.drop_column("backtests", col)
