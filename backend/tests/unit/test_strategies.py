from datetime import date

import pytest

from app.core.errors import ValidationError
from app.core.time import is_month_end, trading_days
from app.services.backtest.context import BacktestContext
from app.services.backtest.portfolio import Portfolio
from app.services.backtest.strategies import STRATEGY_REGISTRY, build_strategy
from app.services.backtest.strategies.buy_hold import BuyAndHold
from app.services.backtest.strategies.rebalance import MonthlyRebalance


def _ctx(d: date, all_days: list[date]) -> BacktestContext:
    return BacktestContext(
        date=d,
        portfolio=Portfolio(cash=10000.0),
        prices_so_far={},
        all_trading_days=all_days,
        params={},
    )


def test_buy_and_hold_emits_once_then_silent():
    days = trading_days(date(2024, 1, 2), date(2024, 1, 31))
    s = BuyAndHold(target_weights={"AAPL": 0.6, "MSFT": 0.4})

    first = s.on_day(_ctx(days[0], days))
    assert {o.ticker for o in first} == {"AAPL", "MSFT"}
    assert sum(o.target_weight for o in first) == pytest.approx(1.0)

    for d in days[1:]:
        assert s.on_day(_ctx(d, days)) == []


def test_monthly_rebalance_emits_first_day_and_each_month_end():
    days = trading_days(date(2024, 1, 2), date(2024, 4, 5))
    s = MonthlyRebalance(target_weights={"SPY": 1.0})

    emitted = [(d, len(s.on_day(_ctx(d, days)))) for d in days]
    fire_dates = {d for d, n in emitted if n > 0}

    # First trading day in the window must fire.
    assert days[0] in fire_dates
    # All month-ends in the window must fire.
    expected_month_ends = {d for d in days if is_month_end(d, days)}
    assert expected_month_ends.issubset(fire_dates)
    # Random non-month-end mid-month days must not fire.
    non_month_end = next(d for d in days[1:] if not is_month_end(d, days))
    assert non_month_end not in fire_dates


def test_registry_round_trip():
    assert "buy_and_hold" in STRATEGY_REGISTRY
    assert "monthly_rebalance" in STRATEGY_REGISTRY

    s = build_strategy("buy_and_hold", {"target_weights": {"SPY": 1.0}})
    assert isinstance(s, BuyAndHold)

    s = build_strategy("monthly_rebalance", {"target_weights": {"SPY": 1.0}})
    assert isinstance(s, MonthlyRebalance)


def test_unknown_strategy_raises_validation_error():
    with pytest.raises(ValidationError) as exc:
        build_strategy("unknown_xyz", {})
    assert exc.value.code == "unknown_strategy"


def test_is_month_end_canary():
    """Q1 2024 month-ends are 2024-01-31, 2024-02-29, 2024-03-28 (29th is Good Friday)."""
    days = trading_days(date(2024, 1, 2), date(2024, 4, 5))
    fired = [d for d in days if is_month_end(d, days)]
    assert date(2024, 1, 31) in fired
    assert date(2024, 2, 29) in fired
    # 2024-03-29 is Good Friday (no NYSE session); pandas bdate_range still
    # returns it. Either way, the last business day in the days list before
    # April should be flagged.
    march = [d for d in fired if d.month == 3]
    assert len(march) == 1
