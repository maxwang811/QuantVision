import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.forecast import Forecast


class ForecastDistributionBin(Base):
    __tablename__ = "forecast_distribution_bins"

    forecast_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("forecasts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    bin_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    bin_lower: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    bin_upper: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)

    forecast: Mapped["Forecast"] = relationship(back_populates="distribution_bins")

    def __repr__(self) -> str:
        return f"<ForecastDistributionBin {self.forecast_id} bin={self.bin_index} count={self.count}>"
