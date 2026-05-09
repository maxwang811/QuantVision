import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.backtest import Backtest
    from app.models.experiment_sweep import ExperimentSweep
    from app.models.forecast import Forecast


class ExperimentSweepRun(Base):
    __tablename__ = "experiment_sweep_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sweep_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experiment_sweeps.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_index: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    backtest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("backtests.id", ondelete="SET NULL"),
        nullable=True,
    )
    forecast_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("forecasts.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sweep: Mapped["ExperimentSweep"] = relationship(back_populates="runs")
    backtest: Mapped["Backtest | None"] = relationship()
    forecast: Mapped["Forecast | None"] = relationship()

    __table_args__ = (
        UniqueConstraint("sweep_id", "run_index", name="uq_sweep_runs_sweep_index"),
        Index("ix_sweep_runs_sweep_id", "sweep_id"),
        Index("ix_sweep_runs_backtest_id", "backtest_id"),
        Index("ix_sweep_runs_forecast_id", "forecast_id"),
        CheckConstraint(
            "kind IN ('backtest','forecast')",
            name="ck_experiment_sweep_runs_kind_valid",
        ),
        CheckConstraint(
            "status IN ('queued','running','completed','failed')",
            name="ck_experiment_sweep_runs_status_valid",
        ),
        CheckConstraint("run_index >= 0", name="ck_experiment_sweep_runs_index_nonneg"),
    )

    def __repr__(self) -> str:
        return f"<ExperimentSweepRun {self.sweep_id} idx={self.run_index} {self.status}>"
