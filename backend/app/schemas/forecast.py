from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ForecastMethod = Literal["monte_carlo", "bootstrap", "ml_drift"]


class ForecastCreate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    method: ForecastMethod

    # Form A — manual portfolio entry. All three must be set together when
    # `from_backtest_id` is null.
    tickers: list[str] | None = Field(default=None, max_length=50)
    weights: list[float] | None = Field(default=None, max_length=50)
    initial_value: float | None = Field(default=None, gt=0)

    # Form B — seed from a previous backtest's end-state portfolio. Mutually
    # exclusive with the manual fields above.
    from_backtest_id: UUID | None = None

    horizon_months: int = Field(ge=1, le=120)
    n_simulations: int = Field(default=10_000, ge=100, le=50_000)
    lookback_days: int = Field(default=1260, ge=252, le=5040)
    as_of_date: date | None = None
    benchmark_ticker: str | None = Field(default=None, max_length=16)
    random_seed: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _check(self) -> "ForecastCreate":
        manual_set = (
            self.tickers is not None
            or self.weights is not None
            or self.initial_value is not None
        )
        manual_all = (
            self.tickers is not None
            and self.weights is not None
            and self.initial_value is not None
        )
        if self.from_backtest_id is not None and manual_set:
            raise ValueError(
                "from_backtest_id is mutually exclusive with tickers/weights/initial_value"
            )
        if self.from_backtest_id is None and not manual_all:
            raise ValueError(
                "tickers, weights, and initial_value are all required when from_backtest_id is not set"
            )

        if self.tickers is not None and self.weights is not None:
            if len(self.tickers) != len(self.weights):
                raise ValueError("tickers and weights must have the same length")
            if any(w < 0 for w in self.weights):
                raise ValueError("weights must be non-negative")
            if abs(sum(self.weights) - 1.0) > 1e-6:
                raise ValueError("weights must sum to 1.0")
            normalized = [t.upper() for t in self.tickers]
            if len(set(normalized)) != len(normalized):
                raise ValueError("tickers must be unique")
            self.tickers = normalized

        if self.benchmark_ticker:
            self.benchmark_ticker = self.benchmark_ticker.upper()
        return self


class ForecastOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None
    method: str
    status: str
    initial_value: float
    horizon_months: int
    horizon_trading_days: int
    n_simulations: int
    as_of_date: date
    lookback_start: date
    lookback_end: date
    benchmark_ticker: str | None
    from_backtest_id: UUID | None
    random_seed: int

    # Reconstructed from `params` on read so the API echo always reflects the
    # actual basket the engine simulated (including the from-backtest case).
    tickers: list[str] | None = None
    weights: list[float] | None = None

    expected_value: float | None = None
    median_value: float | None = None
    p5_value: float | None = None
    p10_value: float | None = None
    p25_value: float | None = None
    p75_value: float | None = None
    p90_value: float | None = None
    p95_value: float | None = None
    probability_of_loss: float | None = None
    probability_beat_benchmark: float | None = None
    annualized_volatility: float | None = None
    expected_return: float | None = None

    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    @model_validator(mode="before")
    @classmethod
    def _populate_basket_from_params(cls, data):
        # When validating from the SQLAlchemy `Forecast` ORM object, surface the
        # tickers/weights stored in `params` JSON as top-level fields.
        if hasattr(data, "params"):
            params = data.params or {}
            tickers = params.get("tickers")
            weights = params.get("weights")
            d = {
                k: getattr(data, k)
                for k in cls.model_fields
                if hasattr(data, k) and k not in {"tickers", "weights"}
            }
            d["tickers"] = tickers
            d["weights"] = weights
            return d
        return data


class ForecastPathPoint(BaseModel):
    index: int
    rank_label: str | None = None
    values: list[float]


class ForecastPathsOut(BaseModel):
    forecast_id: UUID
    as_of_date: date
    horizon_trading_days: int
    initial_value: float
    step_dates: list[date]
    paths: list[ForecastPathPoint]


class ForecastDistributionBinOut(BaseModel):
    index: int
    lower: float
    upper: float
    count: int


class ForecastPercentiles(BaseModel):
    p5: float
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    p95: float


class ForecastDistributionOut(BaseModel):
    forecast_id: UUID
    initial_value: float
    bin_count: int
    bins: list[ForecastDistributionBinOut]
    percentiles: ForecastPercentiles
