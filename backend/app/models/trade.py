import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.backtest import Backtest


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    backtest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("backtests.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    transaction_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    notional: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)

    backtest: Mapped["Backtest"] = relationship(back_populates="trades")
    asset: Mapped["Asset"] = relationship()

    __table_args__ = (
        Index("ix_trades_backtest_id_date", "backtest_id", "date"),
        CheckConstraint("side IN ('buy','sell')", name="side_valid"),
    )

    def __repr__(self) -> str:
        return f"<Trade {self.date} {self.side} {self.quantity}@{self.price}>"
