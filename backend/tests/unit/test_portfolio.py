from datetime import date

import pytest

from app.services.backtest.order import Fill
from app.services.backtest.portfolio import Portfolio


def test_equity_with_no_holdings_is_cash():
    p = Portfolio(cash=10000.0)
    assert p.equity({}) == 10000.0


def test_equity_with_holdings():
    p = Portfolio(cash=1000.0, holdings={"AAPL": 10.0, "MSFT": 5.0})
    prices = {"AAPL": 200.0, "MSFT": 400.0}
    assert p.equity(prices) == pytest.approx(1000.0 + 10 * 200 + 5 * 400)


def test_apply_buy_fill_reduces_cash_increases_shares():
    p = Portfolio(cash=10000.0)
    fill = Fill(
        date=date(2024, 1, 2),
        ticker="AAPL",
        side="buy",
        quantity=10.0,
        price=150.0,
        transaction_cost=1.5,
        notional=1500.0,
    )
    p.apply_fill(fill)
    assert p.holdings["AAPL"] == 10.0
    assert p.cash == pytest.approx(10000.0 - 1500.0 - 1.5)


def test_apply_sell_fill_increases_cash_decreases_shares():
    p = Portfolio(cash=1000.0, holdings={"AAPL": 10.0})
    fill = Fill(
        date=date(2024, 1, 3),
        ticker="AAPL",
        side="sell",
        quantity=4.0,
        price=160.0,
        transaction_cost=0.64,
        notional=640.0,
    )
    p.apply_fill(fill)
    assert p.holdings["AAPL"] == pytest.approx(6.0)
    assert p.cash == pytest.approx(1000.0 + 640.0 - 0.64)


def test_buy_then_sell_preserves_cash_minus_costs():
    p = Portfolio(cash=10000.0)
    p.apply_fill(
        Fill(date(2024, 1, 2), "AAPL", "buy", 10.0, 150.0, 1.5, 1500.0)
    )
    p.apply_fill(
        Fill(date(2024, 1, 3), "AAPL", "sell", 10.0, 150.0, 1.5, 1500.0)
    )
    assert p.holdings["AAPL"] == pytest.approx(0.0)
    assert p.cash == pytest.approx(10000.0 - 3.0)


def test_snapshot_components_sum_to_total():
    p = Portfolio(cash=500.0, holdings={"AAPL": 3.0, "MSFT": 2.0})
    prices = {"AAPL": 100.0, "MSFT": 200.0}
    cash, holdings, total = p.snapshot(prices)
    assert cash == 500.0
    assert holdings == pytest.approx(700.0)
    assert total == pytest.approx(1200.0)


def test_zero_share_position_doesnt_require_price():
    p = Portfolio(cash=100.0, holdings={"GHOST": 0.0})
    # No KeyError — zero-share positions skipped during equity sum.
    assert p.equity({}) == 100.0
