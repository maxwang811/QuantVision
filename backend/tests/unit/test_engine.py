from datetime import date, timedelta

import pytest

from app.core.time import trading_days
from app.services.backtest.context import BacktestContext, PriceBar
from app.services.backtest.engine import run
from app.services.backtest.order import TargetWeightOrder


class NoopStrategy:
    def on_day(self, _ctx: BacktestContext):
        return []


def _flat_prices(start: date, end: date, tickers: dict[str, float]) -> dict[str, list[PriceBar]]:
    days = trading_days(start, end)
    return {t: [PriceBar(d, p) for d in days] for t, p in tickers.items()}


def test_noop_strategy_keeps_cash_flat():
    start, end = date(2024, 1, 2), date(2024, 1, 31)
    prices = _flat_prices(start, end, {"AAPL": 100.0})

    result = run(
        start_date=start,
        end_date=end,
        prices_master=prices,
        strategy=NoopStrategy(),
        initial_cash=10_000.0,
        transaction_cost_bps=10,
    )
    assert len(result.fills) == 0
    assert all(dv.total_value == pytest.approx(10_000.0) for dv in result.daily_values)
    assert len(result.daily_values) == len(trading_days(start, end))


def test_first_day_recorded_before_any_fills():
    """Day 0 is a flat all-cash snapshot regardless of strategy intent."""
    start, end = date(2024, 1, 2), date(2024, 1, 5)
    prices = _flat_prices(start, end, {"AAPL": 100.0})

    class DayZeroBuy:
        _fired = False

        def on_day(self, _ctx):
            if self._fired:
                return []
            self._fired = True
            return [TargetWeightOrder("AAPL", 1.0)]

    result = run(
        start_date=start,
        end_date=end,
        prices_master=prices,
        strategy=DayZeroBuy(),
        initial_cash=10_000.0,
        transaction_cost_bps=0,
    )
    assert result.daily_values[0].cash == pytest.approx(10_000.0)
    assert result.daily_values[0].holdings_value == pytest.approx(0.0)
    # Fill happens on day 1 (T+1).
    assert result.fills[0].date == result.daily_values[1].date


def test_pre_buffer_used_for_forward_fill():
    """If today's date has no bar, engine forward-fills from the most recent prior."""
    start, end = date(2024, 1, 2), date(2024, 1, 5)
    # Bars only on the first three days; engine should reuse last bar on day 4.
    days = trading_days(start, end)
    sparse = days[:3]
    prices = {"AAPL": [PriceBar(d, 100.0) for d in sparse]}

    result = run(
        start_date=start,
        end_date=end,
        prices_master=prices,
        strategy=NoopStrategy(),
        initial_cash=1_000.0,
        transaction_cost_bps=0,
    )
    assert len(result.daily_values) == len(days)
    assert all(dv.total_value == pytest.approx(1_000.0) for dv in result.daily_values)


def test_pre_start_dates_dont_appear_in_output():
    """Bars before start_date are valid for forward-fill but never produce snapshots."""
    start, end = date(2024, 1, 8), date(2024, 1, 12)
    pre_buffer = trading_days(start - timedelta(days=14), end)
    prices = {"AAPL": [PriceBar(d, 100.0) for d in pre_buffer]}

    result = run(
        start_date=start,
        end_date=end,
        prices_master=prices,
        strategy=NoopStrategy(),
        initial_cash=1_000.0,
        transaction_cost_bps=0,
    )
    assert result.daily_values[0].date == start
    assert result.daily_values[-1].date == end


def test_last_day_orders_dropped_with_log(caplog):
    start, end = date(2024, 1, 2), date(2024, 1, 5)
    prices = _flat_prices(start, end, {"AAPL": 100.0})

    class AlwaysOrder:
        def on_day(self, _ctx):
            return [TargetWeightOrder("AAPL", 1.0)]

    with caplog.at_level("WARNING"):
        run(
            start_date=start,
            end_date=end,
            prices_master=prices,
            strategy=AlwaysOrder(),
            initial_cash=1_000.0,
            transaction_cost_bps=0,
        )
    assert any("dropping" in r.message and "final trading day" in r.message for r in caplog.records)


def test_buy_full_allocation_yields_correct_holdings_at_constant_price():
    """100% AAPL on day 0 → fill on day 1 at $100/share with $10k → 100 shares."""
    start, end = date(2024, 1, 2), date(2024, 1, 10)
    prices = _flat_prices(start, end, {"AAPL": 100.0})

    class BuyOnce:
        _fired = False

        def on_day(self, _ctx):
            if self._fired:
                return []
            self._fired = True
            return [TargetWeightOrder("AAPL", 1.0)]

    result = run(
        start_date=start,
        end_date=end,
        prices_master=prices,
        strategy=BuyOnce(),
        initial_cash=10_000.0,
        transaction_cost_bps=0,
    )
    assert len(result.fills) == 1
    f = result.fills[0]
    assert f.side == "buy"
    assert f.ticker == "AAPL"
    assert f.quantity == pytest.approx(100.0)
    assert f.price == pytest.approx(100.0)
    # After fill, equity is unchanged at constant price.
    assert result.daily_values[-1].total_value == pytest.approx(10_000.0)


def test_transaction_cost_reduces_equity():
    start, end = date(2024, 1, 2), date(2024, 1, 10)
    prices = _flat_prices(start, end, {"AAPL": 100.0})

    class BuyOnce:
        _fired = False

        def on_day(self, _ctx):
            if self._fired:
                return []
            self._fired = True
            return [TargetWeightOrder("AAPL", 1.0)]

    result = run(
        start_date=start,
        end_date=end,
        prices_master=prices,
        strategy=BuyOnce(),
        initial_cash=10_000.0,
        transaction_cost_bps=10,  # 0.10%
    )
    expected_cost = 10_000.0 * 10 / 10_000.0  # $10
    assert result.daily_values[-1].total_value == pytest.approx(10_000.0 - expected_cost)
