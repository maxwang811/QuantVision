from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

StrategyName = Literal["buy_and_hold", "monthly_rebalance"]


class BacktestCreate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    strategy: StrategyName
    tickers: list[str] = Field(min_length=1, max_length=50)
    weights: list[float] = Field(min_length=1, max_length=50)
    initial_cash: float = Field(gt=0)
    start_date: date
    end_date: date
    transaction_cost_bps: int = Field(default=10, ge=0, le=1000)
    benchmark_ticker: str | None = Field(default=None, max_length=16)

    @model_validator(mode="after")
    def _check(self) -> "BacktestCreate":
        if len(self.tickers) != len(self.weights):
            raise ValueError("tickers and weights must have the same length")
        if any(w < 0 for w in self.weights):
            raise ValueError("weights must be non-negative")
        if abs(sum(self.weights) - 1.0) > 1e-6:
            raise ValueError("weights must sum to 1.0")
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        # Normalize tickers up-front so downstream comparisons are case-insensitive.
        self.tickers = [t.upper() for t in self.tickers]
        if self.benchmark_ticker:
            self.benchmark_ticker = self.benchmark_ticker.upper()
        return self


class BacktestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None
    strategy: str
    status: str
    initial_cash: float
    final_value: float | None
    total_return: float | None
    annualized_return: float | None = None
    volatility: float | None = None
    sharpe_ratio: float | None = None
    max_drawdown: float | None = None
    benchmark_total_return: float | None = None
    benchmark_annualized_return: float | None = None
    alpha: float | None = None
    beta: float | None = None
    information_ratio: float | None = None
    tracking_error: float | None = None
    start_date: date
    end_date: date
    transaction_cost_bps: int
    benchmark_ticker: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    date: date
    ticker: str
    side: str
    quantity: float
    price: float
    transaction_cost: float
    notional: float


class BacktestTradesOut(BaseModel):
    backtest_id: UUID
    trades: list[TradeOut]


class PortfolioValuePoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    cash: float
    holdings_value: float
    total_value: float


class BenchmarkPoint(BaseModel):
    date: date
    value: float


class BacktestEquityCurveOut(BaseModel):
    backtest_id: UUID
    points: list[PortfolioValuePoint]
    benchmark: list[BenchmarkPoint] | None = None
    benchmark_ticker: str | None = None
