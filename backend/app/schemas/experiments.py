from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ExperimentKind = Literal["backtest", "forecast", "model_run", "sweep"]
SweepKind = Literal["backtest", "forecast"]
SweepStatus = Literal["queued", "running", "completed", "partial", "failed"]


class ExperimentSummary(BaseModel):
    id: UUID
    kind: ExperimentKind
    name: str | None
    status: str
    created_at: datetime
    completed_at: datetime | None
    label: str
    primary_metric_label: str | None = None
    primary_metric_value: float | None = None
    secondary_metric_label: str | None = None
    secondary_metric_value: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ExperimentListOut(BaseModel):
    items: list[ExperimentSummary]
    total: int
    limit: int
    offset: int


class ExperimentCompareRequest(BaseModel):
    backtest_ids: list[UUID] = Field(default_factory=list, max_length=8)
    forecast_ids: list[UUID] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def _check(self) -> "ExperimentCompareRequest":
        if not self.backtest_ids and not self.forecast_ids:
            raise ValueError("select at least one backtest or forecast")
        if len(set(self.backtest_ids)) != len(self.backtest_ids):
            raise ValueError("backtest_ids must be unique")
        if len(set(self.forecast_ids)) != len(self.forecast_ids):
            raise ValueError("forecast_ids must be unique")
        return self


class NormalizedCurvePoint(BaseModel):
    date: date
    value: float


class BacktestComparisonItem(BaseModel):
    id: UUID
    name: str | None
    strategy: str
    status: str
    start_date: date
    end_date: date
    initial_cash: float
    final_value: float | None
    total_return: float | None
    annualized_return: float | None
    volatility: float | None
    sharpe_ratio: float | None
    max_drawdown: float | None
    benchmark_ticker: str | None
    benchmark_total_return: float | None
    created_at: datetime
    normalized_curve: list[NormalizedCurvePoint]


class ForecastDistributionCompareBin(BaseModel):
    index: int
    lower: float
    upper: float
    count: int


class ForecastComparisonItem(BaseModel):
    id: UUID
    name: str | None
    method: str
    status: str
    initial_value: float
    horizon_months: int
    n_simulations: int
    expected_value: float | None
    median_value: float | None
    p10_value: float | None
    p90_value: float | None
    probability_of_loss: float | None
    probability_beat_benchmark: float | None
    benchmark_ticker: str | None
    created_at: datetime
    distribution_bins: list[ForecastDistributionCompareBin]


class ExperimentCompareOut(BaseModel):
    backtests: list[BacktestComparisonItem]
    forecasts: list[ForecastComparisonItem]


class ExperimentSweepCreate(BaseModel):
    kind: SweepKind
    name: str | None = Field(default=None, max_length=128)
    base_request: dict[str, Any]
    sweep_parameters: dict[str, list[Any]] = Field(min_length=1)
    max_runs: int = Field(default=50, ge=1, le=50)

    @model_validator(mode="after")
    def _check(self) -> "ExperimentSweepCreate":
        for key, values in self.sweep_parameters.items():
            if not values:
                raise ValueError(f"sweep parameter {key} must have at least one value")
        return self


class ExperimentSweepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None
    kind: str
    status: str
    base_request: dict[str, Any]
    sweep_parameters: dict[str, Any]
    total_runs: int
    completed_runs: int
    failed_runs: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class ExperimentSweepRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sweep_id: UUID
    run_index: int
    kind: str
    params: dict[str, Any]
    backtest_id: UUID | None
    forecast_id: UUID | None
    status: str
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class ExperimentSweepRunsOut(BaseModel):
    sweep_id: UUID
    runs: list[ExperimentSweepRunOut]
