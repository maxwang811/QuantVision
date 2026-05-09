"""End-to-end backtest run against the test DB. Works on SQLite or Postgres.

Seeds synthetic prices, runs `run_backtest`, and asserts that:
  - the final value matches a hand-computed expected value
  - trades and portfolio_values are persisted with correct shapes
  - validation errors fire when expected

These tests exercise the runner + engine + persistence integration. They do not
require Postgres — every feature used (JSON column, UUID FK) has a SQLite
fallback in SQLAlchemy.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.errors import ValidationError
from app.core.time import trading_days
from app.models.asset import Asset
from app.models.portfolio_value import PortfolioValue
from app.models.price import PriceHistory
from app.models.trade import Trade
from app.schemas.backtest import BacktestCreate
from app.services.backtest.runner import run_backtest


def _seed_asset(db, ticker: str, name: str = "") -> Asset:
    asset = Asset(ticker=ticker, name=name or ticker, asset_class="equity")
    db.add(asset)
    db.flush()
    return asset


def _seed_prices(db, asset: Asset, start: date, end: date, prices: list[float]) -> None:
    days = trading_days(start, end)
    assert len(days) == len(prices), f"got {len(days)} days but {len(prices)} prices"
    for d, p in zip(days, prices, strict=True):
        db.add(PriceHistory(asset_id=asset.id, date=d, adj_close=Decimal(str(p))))
    db.flush()


def test_buy_and_hold_constant_price_returns_initial_minus_costs(db):
    """100% AAPL buy-and-hold over 30 days at flat $100 → final == initial - tx_cost."""
    aapl = _seed_asset(db, "AAPL")
    start, end = date(2024, 1, 2), date(2024, 1, 31)
    days = trading_days(start, end)
    _seed_prices(db, aapl, start, end, [100.0] * len(days))

    req = BacktestCreate(
        strategy="buy_and_hold",
        tickers=["AAPL"],
        weights=[1.0],
        initial_cash=10_000.0,
        start_date=start,
        end_date=end,
        transaction_cost_bps=10,
    )
    bt = run_backtest(db, req)
    assert bt.status == "completed"
    expected_cost = 10_000.0 * 0.001  # 10 bps
    assert float(bt.final_value) == pytest.approx(10_000.0 - expected_cost, rel=1e-6)
    # One buy trade per ticker.
    trades = list(db.scalars(select(Trade).where(Trade.backtest_id == bt.id)))
    assert len(trades) == 1
    assert trades[0].side == "buy"
    # Daily values count == trading days in window.
    pvs = list(db.scalars(select(PortfolioValue).where(PortfolioValue.backtest_id == bt.id)))
    assert len(pvs) == len(days)


def test_buy_and_hold_with_returns_doubles_value(db):
    """Single ticker doubling in price → portfolio value doubles (no tx cost)."""
    aapl = _seed_asset(db, "AAPL")
    start, end = date(2024, 1, 2), date(2024, 2, 29)
    days = trading_days(start, end)
    # Linearly ramp from $100 to $200 over the window.
    n = len(days)
    prices = [100.0 + (100.0 * i / (n - 1)) for i in range(n)]
    _seed_prices(db, aapl, start, end, prices)

    req = BacktestCreate(
        strategy="buy_and_hold",
        tickers=["AAPL"],
        weights=[1.0],
        initial_cash=10_000.0,
        start_date=start,
        end_date=end,
        transaction_cost_bps=0,
    )
    bt = run_backtest(db, req)
    assert bt.status == "completed"
    # Buy fills at close[T+1] = prices[1]; final at close[T_last] = prices[-1].
    # Shares = $10k / prices[1]; final value = shares * prices[-1].
    shares = 10_000.0 / prices[1]
    expected_final = shares * prices[-1]
    assert float(bt.final_value) == pytest.approx(expected_final, rel=1e-6)


def test_two_ticker_buy_and_hold_with_correct_split(db):
    """50/50 split with equal flat prices → both positions equal and unchanged."""
    aapl = _seed_asset(db, "AAPL")
    msft = _seed_asset(db, "MSFT")
    start, end = date(2024, 1, 2), date(2024, 2, 29)
    days = trading_days(start, end)
    _seed_prices(db, aapl, start, end, [100.0] * len(days))
    _seed_prices(db, msft, start, end, [200.0] * len(days))

    req = BacktestCreate(
        strategy="buy_and_hold",
        tickers=["AAPL", "MSFT"],
        weights=[0.5, 0.5],
        initial_cash=10_000.0,
        start_date=start,
        end_date=end,
        transaction_cost_bps=0,
    )
    bt = run_backtest(db, req)
    assert bt.status == "completed"
    assert float(bt.final_value) == pytest.approx(10_000.0, rel=1e-6)

    trades = list(db.scalars(select(Trade).where(Trade.backtest_id == bt.id)))
    assert len(trades) == 2
    aapl_trade = next(t for t in trades if t.asset_id == aapl.id)
    msft_trade = next(t for t in trades if t.asset_id == msft.id)
    assert float(aapl_trade.quantity) == pytest.approx(50.0)  # $5000 / $100
    assert float(msft_trade.quantity) == pytest.approx(25.0)  # $5000 / $200


def test_monthly_rebalance_generates_more_trades_than_buy_and_hold(db):
    aapl = _seed_asset(db, "AAPL")
    msft = _seed_asset(db, "MSFT")
    start, end = date(2024, 1, 2), date(2024, 6, 28)
    days = trading_days(start, end)
    # AAPL drifts up, MSFT flat — forces sells on rebalance days.
    aapl_prices = [100.0 * (1 + 0.001 * i) for i in range(len(days))]
    _seed_prices(db, aapl, start, end, aapl_prices)
    _seed_prices(db, msft, start, end, [100.0] * len(days))

    req = BacktestCreate(
        strategy="monthly_rebalance",
        tickers=["AAPL", "MSFT"],
        weights=[0.5, 0.5],
        initial_cash=10_000.0,
        start_date=start,
        end_date=end,
        transaction_cost_bps=0,
    )
    bt = run_backtest(db, req)
    assert bt.status == "completed"
    trades = list(db.scalars(select(Trade).where(Trade.backtest_id == bt.id)))
    # First-day allocation (2 trades) + at least 4 month-end rebalances (≥ 4 trades).
    assert len(trades) > 2


def test_unknown_ticker_raises_validation_error(db):
    req = BacktestCreate(
        strategy="buy_and_hold",
        tickers=["NOSUCH"],
        weights=[1.0],
        initial_cash=10_000.0,
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 31),
    )
    with pytest.raises(ValidationError) as exc:
        run_backtest(db, req)
    assert exc.value.code == "unknown_tickers"


def test_insufficient_coverage_raises_validation_error(db):
    aapl = _seed_asset(db, "AAPL")
    # Prices end before the requested end_date → coverage gap.
    start, short_end = date(2024, 1, 2), date(2024, 1, 12)
    days = trading_days(start, short_end)
    _seed_prices(db, aapl, start, short_end, [100.0] * len(days))

    req = BacktestCreate(
        strategy="buy_and_hold",
        tickers=["AAPL"],
        weights=[1.0],
        initial_cash=10_000.0,
        start_date=start,
        end_date=date(2024, 2, 28),
    )
    with pytest.raises(ValidationError) as exc:
        run_backtest(db, req)
    assert exc.value.code == "insufficient_coverage"


def test_weights_not_summing_to_one_rejected_at_schema():
    from pydantic import ValidationError as PydanticValidationError

    with pytest.raises(PydanticValidationError):
        BacktestCreate(
            strategy="buy_and_hold",
            tickers=["AAPL", "MSFT"],
            weights=[0.7, 0.4],
            initial_cash=10_000.0,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 31),
        )


def test_completed_backtest_is_persisted_with_completed_at(db):
    aapl = _seed_asset(db, "AAPL")
    start, end = date(2024, 1, 2), date(2024, 1, 31)
    _seed_prices(db, aapl, start, end, [100.0] * len(trading_days(start, end)))

    req = BacktestCreate(
        strategy="buy_and_hold",
        tickers=["AAPL"],
        weights=[1.0],
        initial_cash=10_000.0,
        start_date=start,
        end_date=end,
    )
    bt = run_backtest(db, req)
    assert bt.status == "completed"
    assert bt.completed_at is not None
    assert bt.error_message is None
    assert bt.params == {"target_weights": {"AAPL": 1.0}}
