import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.experiment_sweep_run import ExperimentSweepRun


class ExperimentSweep(Base):
    __tablename__ = "experiment_sweeps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str | None] = mapped_column(String(128))
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    base_request: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    sweep_parameters: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    total_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    runs: Mapped[list["ExperimentSweepRun"]] = relationship(
        back_populates="sweep", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "kind IN ('backtest','forecast')",
            name="ck_experiment_sweeps_kind_valid",
        ),
        CheckConstraint(
            "status IN ('queued','running','completed','partial','failed')",
            name="ck_experiment_sweeps_status_valid",
        ),
        CheckConstraint("total_runs >= 0", name="ck_experiment_sweeps_total_runs_nonneg"),
        CheckConstraint(
            "completed_runs >= 0", name="ck_experiment_sweeps_completed_runs_nonneg"
        ),
        CheckConstraint("failed_runs >= 0", name="ck_experiment_sweeps_failed_runs_nonneg"),
    )

    def __repr__(self) -> str:
        return f"<ExperimentSweep {self.id} {self.kind} {self.status}>"
