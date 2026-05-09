import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.forecast import Forecast


class ForecastPath(Base):
    __tablename__ = "forecast_paths"

    forecast_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("forecasts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    path_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    rank_label: Mapped[str | None] = mapped_column(String(16))
    values: Mapped[list[float]] = mapped_column(JSON, nullable=False)

    forecast: Mapped["Forecast"] = relationship(back_populates="paths")

    def __repr__(self) -> str:
        return f"<ForecastPath {self.forecast_id} idx={self.path_index} label={self.rank_label}>"
