import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.backtest import Backtest


class PortfolioValue(Base):
    __tablename__ = "portfolio_values"

    backtest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("backtests.id", ondelete="CASCADE"),
        primary_key=True,
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    cash: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    holdings_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)

    backtest: Mapped["Backtest"] = relationship(back_populates="portfolio_values")

    def __repr__(self) -> str:
        return f"<PortfolioValue {self.backtest_id} {self.date} total={self.total_value}>"
