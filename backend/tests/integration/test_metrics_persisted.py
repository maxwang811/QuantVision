"""End-to-end metrics tests: run a backtest with a benchmark and verify that
the metric columns are populated, the equity-curve endpoint returns a benchmark
series, and the recompute endpoint reproduces the same values.
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.core.errors import ValidationError
from app.core.time import trading_days
from app.models.asset import Asset
from app.models.backtest import Backtest
from app.models.price import PriceHistory
from app.schemas.backtest import BacktestCreate
from app.services.backtest.runner import run_backtest


def _seed_asset(db, ticker: str) -> Asset:
    asset = Asset(ticker=ticker, name=ticker, asset_class="equity")
    db.add(asset)
    db.flush()
    return asset


def _seed_prices(db, asset: Asset, start: date, end: date, prices: list[float]) -> None:
    days = trading_days(start, end)
    assert len(days) == len(prices), f"got {len(days)} days but {len(prices)} prices"
    for d, p in zip(days, prices, strict=True):
        db.add(PriceHistory(asset_id=asset.id, date=d, adj_close=Decimal(str(p))))
    db.flush()


def test_backtest_persists_core_metrics(db):
    aapl = _seed_asset(db, "AAPL")
    start, end = date(2024, 1, 2), date(2024, 6, 28)
    days = trading_days(start, end)
    # Linear ramp $100 → $130.
    n = len(days)
    prices = [100.0 + 30.0 * i / (n - 1) for i in range(n)]
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
    assert bt.annualized_return is not None
    assert bt.volatility is not None
    assert bt.sharpe_ratio is not None
    assert bt.max_drawdown is not None
    # Linear ramp has no drawdowns.
    assert float(bt.max_drawdown) == pytest.approx(0.0, abs=1e-6)
    # No benchmark requested → benchmark fields stay null.
    assert bt.alpha is None
    assert bt.beta is None


def test_backtest_with_benchmark_populates_alpha_beta(db):
    aapl = _seed_asset(db, "AAPL")
    spy = _seed_asset(db, "SPY")
    start, end = date(2024, 1, 2), date(2024, 6, 28)
    days = trading_days(start, end)
    n = len(days)
    aapl_prices = [100.0 + 30.0 * i / (n - 1) for i in range(n)]
    spy_prices = [400.0 + 40.0 * i / (n - 1) for i in range(n)]
    _seed_prices(db, aapl, start, end, aapl_prices)
    _seed_prices(db, spy, start, end, spy_prices)

    req = BacktestCreate(
        strategy="buy_and_hold",
        tickers=["AAPL"],
        weights=[1.0],
        initial_cash=10_000.0,
        start_date=start,
        end_date=end,
        transaction_cost_bps=0,
        benchmark_ticker="SPY",
    )
    bt = run_backtest(db, req)
    assert bt.status == "completed"
    assert bt.benchmark_total_return is not None
    assert bt.benchmark_annualized_return is not None
    assert bt.alpha is not None
    assert bt.beta is not None
    assert bt.information_ratio is not None
    assert bt.tracking_error is not None
    # SPY went 400 → 440 = +10%.
    assert float(bt.benchmark_total_return) == pytest.approx(0.10, rel=1e-4)


def test_benchmark_missing_coverage_rejected(db):
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
        benchmark_ticker="ZZZZ",
    )
    with pytest.raises(ValidationError) as exc:
        run_backtest(db, req)
    assert exc.value.code == "insufficient_benchmark_coverage"


def test_recompute_metrics_endpoint_reproduces_values(db, client):
    aapl = _seed_asset(db, "AAPL")
    spy = _seed_asset(db, "SPY")
    start, end = date(2024, 1, 2), date(2024, 6, 28)
    days = trading_days(start, end)
    n = len(days)
    _seed_prices(db, aapl, start, end, [100.0 + i * 0.1 for i in range(n)])
    _seed_prices(db, spy, start, end, [400.0 + i * 0.05 for i in range(n)])
    db.commit()  # make rows visible to the API session

    payload = {
        "strategy": "buy_and_hold",
        "tickers": ["AAPL"],
        "weights": [1.0],
        "initial_cash": 10_000.0,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "transaction_cost_bps": 0,
        "benchmark_ticker": "SPY",
    }
    r = client.post("/api/backtests", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    bt_id = body["id"]
    original_sharpe = body["sharpe_ratio"]
    original_alpha = body["alpha"]
    original_beta = body["beta"]
    assert original_sharpe is not None
    assert original_beta is not None

    # Zero-out the metric columns to prove recompute actually rewrites them.
    bt = db.get(Backtest, uuid.UUID(bt_id))
    assert bt is not None
    bt.sharpe_ratio = None
    bt.alpha = None
    bt.beta = None
    db.commit()

    r2 = client.post(f"/api/backtests/{bt_id}/recompute_metrics")
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2["sharpe_ratio"] == pytest.approx(original_sharpe, rel=1e-6)
    assert body2["alpha"] == pytest.approx(original_alpha, rel=1e-6)
    assert body2["beta"] == pytest.approx(original_beta, rel=1e-6)


def test_equity_curve_endpoint_returns_benchmark_series(db, client):
    aapl = _seed_asset(db, "AAPL")
    spy = _seed_asset(db, "SPY")
    start, end = date(2024, 1, 2), date(2024, 3, 28)
    days = trading_days(start, end)
    n = len(days)
    _seed_prices(db, aapl, start, end, [100.0 + i * 0.5 for i in range(n)])
    _seed_prices(db, spy, start, end, [400.0 + i * 0.2 for i in range(n)])
    db.commit()

    payload = {
        "strategy": "buy_and_hold",
        "tickers": ["AAPL"],
        "weights": [1.0],
        "initial_cash": 10_000.0,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "transaction_cost_bps": 0,
        "benchmark_ticker": "SPY",
    }
    r = client.post("/api/backtests", json=payload)
    assert r.status_code == 200, r.text
    bt_id = r.json()["id"]

    r2 = client.get(f"/api/backtests/{bt_id}/portfolio_values")
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["benchmark_ticker"] == "SPY"
    assert body["benchmark"] is not None
    assert len(body["benchmark"]) == len(body["points"])
    # Benchmark series scaled to start at initial_cash.
    assert body["benchmark"][0]["value"] == pytest.approx(10_000.0)


def test_equity_curve_no_benchmark_returns_null(db, client):
    aapl = _seed_asset(db, "AAPL")
    start, end = date(2024, 1, 2), date(2024, 1, 31)
    _seed_prices(db, aapl, start, end, [100.0] * len(trading_days(start, end)))
    db.commit()

    payload = {
        "strategy": "buy_and_hold",
        "tickers": ["AAPL"],
        "weights": [1.0],
        "initial_cash": 10_000.0,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    }
    r = client.post("/api/backtests", json=payload)
    bt_id = r.json()["id"]

    r2 = client.get(f"/api/backtests/{bt_id}/portfolio_values")
    body = r2.json()
    assert body["benchmark"] is None
    assert body["benchmark_ticker"] is None


def test_recompute_rejected_on_failed_backtest(db, client):
    """Failed backtests can't be recomputed (no portfolio_values to read)."""
    bt = Backtest(
        id=uuid.uuid4(),
        strategy="buy_and_hold",
        params={"target_weights": {"AAPL": 1.0}},
        initial_cash=Decimal("10000"),
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 31),
        transaction_cost_bps=0,
        status="failed",
        error_message="manual fixture",
    )
    db.add(bt)
    db.commit()

    r = client.post(f"/api/backtests/{bt.id}/recompute_metrics")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "recompute_invalid_status"
