import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.forecast_distribution_bin import ForecastDistributionBin
    from app.models.forecast_path import ForecastPath


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str | None] = mapped_column(String(128))
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    initial_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    horizon_months: Mapped[int] = mapped_column(Integer, nullable=False)
    horizon_trading_days: Mapped[int] = mapped_column(Integer, nullable=False)
    n_simulations: Mapped[int] = mapped_column(Integer, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    lookback_start: Mapped[date] = mapped_column(Date, nullable=False)
    lookback_end: Mapped[date] = mapped_column(Date, nullable=False)
    benchmark_ticker: Mapped[str | None] = mapped_column(String(16))
    from_backtest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("backtests.id", ondelete="SET NULL"),
        nullable=True,
    )
    random_seed: Mapped[int] = mapped_column(BigInteger, nullable=False)

    expected_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    median_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    p5_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    p10_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    p25_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    p75_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    p90_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    p95_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    probability_of_loss: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    probability_beat_benchmark: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    annualized_volatility: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    expected_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    paths: Mapped[list["ForecastPath"]] = relationship(
        back_populates="forecast", cascade="all, delete-orphan"
    )
    distribution_bins: Mapped[list["ForecastDistributionBin"]] = relationship(
        back_populates="forecast", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "method IN ('monte_carlo','bootstrap','ml_drift')",
            name="ck_forecasts_method_valid",
        ),
        CheckConstraint(
            "status IN ('running','completed','failed')",
            name="ck_forecasts_status_valid",
        ),
        CheckConstraint("horizon_months > 0", name="ck_forecasts_horizon_pos"),
        CheckConstraint("n_simulations > 0", name="ck_forecasts_nsims_pos"),
    )

    def __repr__(self) -> str:
        return f"<Forecast {self.id} {self.method} {self.status}>"
