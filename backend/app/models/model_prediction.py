import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.model_run import ModelRun


class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    model_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("model_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    model_name: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(10, 8), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[int | None] = mapped_column(Integer)
    forward_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    benchmark_forward_return: Mapped[Decimal | None] = mapped_column(Numeric(18, 8))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    model_run: Mapped["ModelRun"] = relationship(back_populates="predictions")
    asset: Mapped["Asset"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "model_run_id",
            "date",
            "asset_id",
            "model_name",
            name="uq_model_predictions_run_date_asset_model",
        ),
        CheckConstraint(
            "model_name IN ('logistic_regression','xgboost')",
            name="ck_model_predictions_model_name_valid",
        ),
        CheckConstraint("score >= 0 AND score <= 1", name="ck_model_predictions_score_unit"),
        CheckConstraint("rank > 0", name="ck_model_predictions_rank_pos"),
        CheckConstraint("label IS NULL OR label IN (0, 1)", name="ck_model_predictions_label"),
        Index("ix_model_predictions_run_date_model", "model_run_id", "date", "model_name"),
    )

    def __repr__(self) -> str:
        return f"<ModelPrediction {self.model_run_id} {self.date} {self.model_name} rank={self.rank}>"
