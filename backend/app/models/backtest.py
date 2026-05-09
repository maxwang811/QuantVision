import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.portfolio_value import PortfolioValue
    from app.models.trade import Trade


class Backtest(Base):
    __tablename__ = "backtests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str | None] = mapped_column(String(128))
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    initial_cash: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    benchmark_ticker: Mapped[str | None] = mapped_column(String(16))
    transaction_cost_bps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    final_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    total_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    annualized_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    volatility: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    sharpe_ratio: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    max_drawdown: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    benchmark_total_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    benchmark_annualized_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    alpha: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    beta: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    information_ratio: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    tracking_error: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    error_message: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    trades: Mapped[list["Trade"]] = relationship(
        back_populates="backtest", cascade="all, delete-orphan"
    )
    portfolio_values: Mapped[list["PortfolioValue"]] = relationship(
        back_populates="backtest", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('running','completed','failed')",
            name="status_valid",
        ),
        CheckConstraint("start_date < end_date", name="dates_ordered"),
    )

    def __repr__(self) -> str:
        return f"<Backtest {self.id} {self.strategy} {self.status}>"
