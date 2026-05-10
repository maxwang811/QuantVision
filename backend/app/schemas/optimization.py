from datetime import date

from pydantic import BaseModel, Field, model_validator


class OptimizationRequest(BaseModel):
    tickers: list[str] = Field(min_length=2, max_length=50)
    lookback_days: int = Field(default=1260, ge=252, le=5040)
    risk_free_rate: float = Field(default=0.0, ge=0.0, le=0.25)
    target_return: float | None = Field(default=None)
    as_of_date: date | None = None
    n_frontier_points: int = Field(default=25, ge=5, le=100)

    @model_validator(mode="after")
    def _check(self) -> "OptimizationRequest":
        normalized = [t.strip().upper() for t in self.tickers]
        if any(not t for t in normalized):
            raise ValueError("tickers must be non-empty strings")
        if len(set(normalized)) != len(normalized):
            raise ValueError("tickers must be unique")
        self.tickers = normalized
        return self


class FrontierPointOut(BaseModel):
    expected_return: float
    volatility: float
    sharpe_ratio: float
    weights: list[float]


class OptimizationResultOut(BaseModel):
    tickers: list[str]
    risk_free_rate: float
    n_observations: int
    lookback_start: date
    lookback_end: date
    min_variance: FrontierPointOut
    max_sharpe: FrontierPointOut
    target_return: FrontierPointOut | None
    frontier: list[FrontierPointOut]
