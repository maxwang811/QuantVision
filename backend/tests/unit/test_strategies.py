from datetime import date

import pytest

from app.core.errors import ValidationError
from app.core.time import is_month_end, trading_days
from app.services.backtest.context import BacktestContext, PriceBar
from app.services.backtest.portfolio import Portfolio
from app.services.backtest.strategies import STRATEGY_REGISTRY, build_strategy
from app.services.backtest.strategies.buy_hold import BuyAndHold
from app.services.backtest.strategies.ma_crossover import MACrossover
from app.services.backtest.strategies.ranking import MLRanking, MomentumRanking
from app.services.backtest.strategies.rebalance import MonthlyRebalance


def _ctx(d: date, all_days: list[date]) -> BacktestContext:
    return BacktestContext(
        date=d,
        portfolio=Portfolio(cash=10000.0),
        prices_so_far={},
        all_trading_days=all_days,
        params={},
    )


def _price_ctx(d: date, all_days: list[date]) -> BacktestContext:
    idx = all_days.index(d)
    return BacktestContext(
        date=d,
        portfolio=Portfolio(cash=10000.0),
        prices_so_far={
            "A": [PriceBar(day, 100.0 + i) for i, day in enumerate(all_days[: idx + 1])],
            "B": [PriceBar(day, 100.0 - 0.1 * i) for i, day in enumerate(all_days[: idx + 1])],
            "C": [PriceBar(day, 100.0 + 0.2 * i) for i, day in enumerate(all_days[: idx + 1])],
        },
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
    assert "momentum" in STRATEGY_REGISTRY
    assert "ml_ranking" in STRATEGY_REGISTRY
    assert "ma_crossover" in STRATEGY_REGISTRY

    s = build_strategy("buy_and_hold", {"target_weights": {"SPY": 1.0}})
    assert isinstance(s, BuyAndHold)

    s = build_strategy("monthly_rebalance", {"target_weights": {"SPY": 1.0}})
    assert isinstance(s, MonthlyRebalance)

    s = build_strategy("momentum", {"target_weights": {"A": 0.5, "B": 0.5}})
    assert isinstance(s, MomentumRanking)

    s = build_strategy(
        "ma_crossover",
        {"target_weights": {"A": 0.5, "B": 0.5}, "short_window": 5, "long_window": 10},
    )
    assert isinstance(s, MACrossover)


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


def test_momentum_ranking_holds_top_n_and_zeroes_others():
    days = trading_days(date(2024, 1, 2), date(2024, 4, 30))
    s = MomentumRanking(target_weights={"A": 1 / 3, "B": 1 / 3, "C": 1 / 3}, top_n=2)

    orders = s.on_day(_price_ctx(days[80], days))
    weights = {o.ticker: o.target_weight for o in orders}
    assert weights["A"] == pytest.approx(0.5)
    assert weights["C"] == pytest.approx(0.5)
    assert weights["B"] == pytest.approx(0.0)


def _ma_ctx(d: date, all_days: list[date], prices_by_ticker: dict[str, list[float]]) -> BacktestContext:
    idx = all_days.index(d)
    return BacktestContext(
        date=d,
        portfolio=Portfolio(cash=10000.0),
        prices_so_far={
            t: [PriceBar(all_days[i], p) for i, p in enumerate(series[: idx + 1])]
            for t, series in prices_by_ticker.items()
        },
        all_trading_days=all_days,
        params={},
    )


def test_ma_crossover_validates_window_ordering():
    with pytest.raises(ValueError):
        MACrossover(target_weights={"SPY": 1.0}, short_window=10, long_window=5)
    with pytest.raises(ValueError):
        MACrossover(target_weights={"SPY": 1.0}, short_window=10, long_window=10)


def test_ma_crossover_respects_user_weights_when_signal_on():
    days = trading_days(date(2024, 1, 2), date(2024, 2, 29))
    rising = [100.0 + i for i in range(len(days))]
    s = MACrossover(
        target_weights={"A": 0.6, "B": 0.4}, short_window=2, long_window=4
    )

    orders = s.on_day(_ma_ctx(days[4], days, {"A": rising, "B": rising}))
    weights = {o.ticker: o.target_weight for o in orders}
    assert weights == {"A": pytest.approx(0.6), "B": pytest.approx(0.4)}


def test_ma_crossover_exits_to_cash_when_short_below_long():
    days = trading_days(date(2024, 1, 2), date(2024, 2, 29))
    falling = [200.0 - i for i in range(len(days))]
    s = MACrossover(
        target_weights={"A": 0.5, "B": 0.5}, short_window=2, long_window=4
    )

    orders = s.on_day(_ma_ctx(days[4], days, {"A": falling, "B": falling}))
    weights = {o.ticker: o.target_weight for o in orders}
    assert weights == {"A": 0.0, "B": 0.0}


def test_ma_crossover_only_emits_on_signal_change():
    days = trading_days(date(2024, 1, 2), date(2024, 2, 29))
    rising = [100.0 + i for i in range(len(days))]
    s = MACrossover(target_weights={"A": 1.0}, short_window=2, long_window=4)

    first = s.on_day(_ma_ctx(days[4], days, {"A": rising}))
    assert len(first) == 1
    assert first[0].target_weight == pytest.approx(1.0)
    # Same signal state on the next day → no new orders.
    second = s.on_day(_ma_ctx(days[5], days, {"A": rising}))
    assert second == []


def test_ma_crossover_insufficient_history_holds_cash():
    days = trading_days(date(2024, 1, 2), date(2024, 2, 29))
    rising = [100.0 + i for i in range(len(days))]
    s = MACrossover(target_weights={"A": 1.0}, short_window=2, long_window=4)

    # Day 0 has only 1 bar, less than long_window=4 → signal False.
    orders = s.on_day(_ma_ctx(days[0], days, {"A": rising}))
    assert {o.ticker: o.target_weight for o in orders} == {"A": 0.0}


def test_ml_ranking_uses_latest_available_prediction_scores():
    days = trading_days(date(2024, 1, 2), date(2024, 3, 29))
    scores = {
        days[0]: {"A": 0.1, "B": 0.9, "C": 0.4},
        days[20]: {"A": 0.8, "B": 0.2, "C": 0.7},
    }
    s = MLRanking(
        target_weights={"A": 1 / 3, "B": 1 / 3, "C": 1 / 3},
        prediction_scores=scores,
        top_n=2,
    )

    first = {o.ticker: o.target_weight for o in s.on_day(_ctx(days[0], days))}
    assert first == {"A": 0.0, "B": 0.5, "C": 0.5}

    month_end = next(d for d in days if is_month_end(d, days))
    second = {o.ticker: o.target_weight for o in s.on_day(_ctx(month_end, days))}
    assert second == {"A": 0.5, "B": 0.0, "C": 0.5}
