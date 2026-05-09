"""Backtest engine: deterministic time loop, no I/O.

The engine consumes pre-loaded price series and a strategy, and produces a list
of daily portfolio snapshots and a list of executed fills. The runner persists
both to the database.

Lookahead barrier: `BacktestContext.prices_so_far[ticker]` is sliced via
`bisect_right` to dates <= ctx.date on every iteration. The strategy literally
never holds a reference to the master price list. See `engine.run` below.
"""

from __future__ import annotations

import logging
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date

from app.core.time import trading_days
from app.services.backtest.context import BacktestContext, PriceBar
from app.services.backtest.order import Fill, TargetWeightOrder
from app.services.backtest.portfolio import Portfolio
from app.services.backtest.strategies.base import Strategy

log = logging.getLogger(__name__)

_QUANTITY_EPSILON = 1e-9


@dataclass(frozen=True)
class DailyValue:
    date: date
    cash: float
    holdings_value: float
    total_value: float


@dataclass(frozen=True)
class EngineResult:
    daily_values: list[DailyValue]
    fills: list[Fill]


def _forward_fill_prices(
    prices_master: dict[str, list[PriceBar]], today: date
) -> dict[str, float]:
    """Return {ticker: most recent adj_close on or before today}.

    Raises KeyError if a ticker has no price on or before today — the runner is
    responsible for ensuring sufficient pre-buffer coverage.
    """
    out: dict[str, float] = {}
    for ticker, bars in prices_master.items():
        idx = bisect_right([b.date for b in bars], today)
        if idx == 0:
            raise KeyError(f"no price for {ticker} on or before {today}")
        out[ticker] = bars[idx - 1].adj_close
    return out


def _slice_through(
    prices_master: dict[str, list[PriceBar]], today: date
) -> dict[str, list[PriceBar]]:
    """Slice each ticker's bars to dates <= today. The lookahead barrier."""
    out: dict[str, list[PriceBar]] = {}
    for ticker, bars in prices_master.items():
        idx = bisect_right([b.date for b in bars], today)
        out[ticker] = bars[:idx]
    return out


def _execute_orders(
    portfolio: Portfolio,
    orders: list[TargetWeightOrder],
    fill_prices: dict[str, float],
    today: date,
    transaction_cost_bps: int,
) -> list[Fill]:
    """Convert target-weight orders to fills and apply them. Sells execute first
    so the portfolio never goes transiently cash-negative on a rebalance.
    """
    if not orders:
        return []

    equity = portfolio.equity(fill_prices)
    deltas: list[tuple[TargetWeightOrder, float]] = []
    for order in orders:
        price = fill_prices[order.ticker]
        target_value = equity * order.target_weight
        current_value = portfolio.position_value(order.ticker, price)
        delta_value = target_value - current_value
        deltas.append((order, delta_value))

    # Sells (negative delta) before buys.
    deltas.sort(key=lambda od: od[1])

    fills: list[Fill] = []
    for order, delta_value in deltas:
        price = fill_prices[order.ticker]
        signed_qty = delta_value / price
        if abs(signed_qty) < _QUANTITY_EPSILON:
            continue
        side = "buy" if signed_qty > 0 else "sell"
        quantity = abs(signed_qty)
        notional = quantity * price
        tx_cost = notional * transaction_cost_bps / 10_000.0
        fill = Fill(
            date=today,
            ticker=order.ticker,
            side=side,
            quantity=quantity,
            price=price,
            transaction_cost=tx_cost,
            notional=notional,
        )
        portfolio.apply_fill(fill)
        fills.append(fill)
    return fills


def run(
    *,
    start_date: date,
    end_date: date,
    prices_master: dict[str, list[PriceBar]],
    strategy: Strategy,
    initial_cash: float,
    transaction_cost_bps: int,
    params: dict | None = None,
) -> EngineResult:
    """Deterministic time loop. T+1 close-fill convention.

    On day T, the strategy sees prices through close[T] and emits orders that
    fill at close[T+1]. Orders pending on the final trading day are dropped
    with a warning.
    """
    portfolio = Portfolio(cash=initial_cash)
    all_days = trading_days(start_date, end_date)
    daily_values: list[DailyValue] = []
    fills: list[Fill] = []
    pending: list[TargetWeightOrder] = []

    for i, today in enumerate(all_days):
        fill_prices = _forward_fill_prices(prices_master, today)

        # Execute orders queued at close[T-1] at close[T].
        if pending:
            day_fills = _execute_orders(
                portfolio, pending, fill_prices, today, transaction_cost_bps
            )
            fills.extend(day_fills)
            pending = []

        cash, holdings_value, total = portfolio.snapshot(fill_prices)
        daily_values.append(DailyValue(today, cash, holdings_value, total))

        ctx = BacktestContext(
            date=today,
            portfolio=portfolio,
            prices_so_far=_slice_through(prices_master, today),
            all_trading_days=all_days,
            params=params or {},
        )
        new_orders = strategy.on_day(ctx)
        if new_orders:
            if i == len(all_days) - 1:
                log.warning(
                    "dropping %d order(s) emitted on final trading day %s",
                    len(new_orders),
                    today,
                )
            else:
                pending = list(new_orders)

    return EngineResult(daily_values=daily_values, fills=fills)
