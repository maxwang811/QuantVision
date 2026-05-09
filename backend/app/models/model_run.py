import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, CheckConstraint, Date, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.model_prediction import ModelPrediction


class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str | None] = mapped_column(String(128))
    tickers: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    benchmark_ticker: Mapped[str] = mapped_column(String(16), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    label_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    training_lookback_days: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_model: Mapped[str] = mapped_column(String(32), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    predictions: Mapped[list["ModelPrediction"]] = relationship(
        back_populates="model_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('running','completed','failed')",
            name="ck_model_runs_status_valid",
        ),
        CheckConstraint(
            "selected_model IN ('logistic_regression','xgboost')",
            name="ck_model_runs_selected_model_valid",
        ),
        CheckConstraint("start_date < end_date", name="ck_model_runs_dates_ordered"),
        CheckConstraint(
            "label_horizon_days > 0", name="ck_model_runs_label_horizon_pos"
        ),
        CheckConstraint(
            "training_lookback_days > 0", name="ck_model_runs_training_lookback_pos"
        ),
    )

    def __repr__(self) -> str:
        return f"<ModelRun {self.id} {self.selected_model} {self.status}>"
