from dataclasses import dataclass
from datetime import date
from typing import Any

from app.services.backtest.portfolio import Portfolio


@dataclass(frozen=True)
class PriceBar:
    """Minimal price record exposed to strategies. adj_close only — no peeking at OHLC."""

    date: date
    adj_close: float


@dataclass
class BacktestContext:
    """Read-only view passed to a strategy on each iteration of the engine loop.

    `prices_so_far[ticker]` is sliced by the engine to dates <= `date`. This is
    the lookahead barrier — removing the slice breaks the entire correctness story.
    """

    date: date
    portfolio: Portfolio
    prices_so_far: dict[str, list[PriceBar]]
    all_trading_days: list[date]
    params: dict[str, Any]
