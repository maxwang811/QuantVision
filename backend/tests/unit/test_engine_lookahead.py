"""Lookahead-prevention canary.

The engine's correctness hinges on `BacktestContext.prices_so_far` being
sliced to dates <= ctx.date on every iteration. This test installs a strategy
that asserts that invariant on every call. If a future change leaks future
prices, this test fails immediately.
"""

from datetime import date, timedelta

from app.core.time import trading_days
from app.services.backtest.context import BacktestContext, PriceBar
from app.services.backtest.engine import run


class PeekingStrategy:
    """Asserts ctx never exposes prices past today."""

    def __init__(self):
        self.calls = 0
        self.violations: list[tuple[date, str, date]] = []

    def on_day(self, ctx: BacktestContext):
        self.calls += 1
        for ticker, bars in ctx.prices_so_far.items():
            if not bars:
                continue
            latest = max(b.date for b in bars)
            if latest > ctx.date:
                self.violations.append((ctx.date, ticker, latest))
        return []


def test_strategy_never_sees_future_prices():
    start, end = date(2024, 1, 2), date(2024, 2, 29)
    days = trading_days(start, end)
    prices = {
        "AAPL": [PriceBar(d, 100.0 + i) for i, d in enumerate(days)],
        "MSFT": [PriceBar(d, 200.0 - i * 0.1) for i, d in enumerate(days)],
    }
    spy = PeekingStrategy()
    run(
        start_date=start,
        end_date=end,
        prices_master=prices,
        strategy=spy,
        initial_cash=10_000.0,
        transaction_cost_bps=0,
    )
    assert spy.calls == len(days)
    assert spy.violations == [], (
        f"strategy saw future prices: {spy.violations[:5]}"
    )


def test_pre_buffer_visible_but_capped_at_today():
    """Pre-start bars are visible to strategies but never beyond ctx.date."""
    start, end = date(2024, 1, 8), date(2024, 1, 12)
    days_with_buffer = trading_days(start - timedelta(days=14), end)
    prices = {"AAPL": [PriceBar(d, 100.0) for d in days_with_buffer]}

    captured: list[tuple[date, int]] = []

    class CaptureStrategy:
        def on_day(self, ctx):
            captured.append((ctx.date, len(ctx.prices_so_far["AAPL"])))
            assert all(b.date <= ctx.date for b in ctx.prices_so_far["AAPL"])
            return []

    run(
        start_date=start,
        end_date=end,
        prices_master=prices,
        strategy=CaptureStrategy(),
        initial_cash=1_000.0,
        transaction_cost_bps=0,
    )
    # On the first day, the strategy can see all pre-buffer bars + today.
    assert captured[0][1] >= 2
    # Counts must be monotonic non-decreasing.
    assert all(captured[i][1] <= captured[i + 1][1] for i in range(len(captured) - 1))
