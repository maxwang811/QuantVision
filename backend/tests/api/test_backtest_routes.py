"""End-to-end tests for /api/backtests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.time import trading_days
from app.models.asset import Asset
from app.models.price import PriceHistory


def _seed(db, ticker: str, start: date, end: date, prices: list[float]):
    asset = Asset(ticker=ticker, name=ticker, asset_class="equity")
    db.add(asset)
    db.flush()
    for d, p in zip(trading_days(start, end), prices, strict=True):
        db.add(PriceHistory(asset_id=asset.id, date=d, adj_close=Decimal(str(p))))
    db.commit()
    return asset


def test_post_backtest_happy_path(client, db):
    start, end = date(2024, 1, 2), date(2024, 1, 31)
    days = trading_days(start, end)
    _seed(db, "AAPL", start, end, [100.0] * len(days))

    payload = {
        "name": "smoke",
        "strategy": "buy_and_hold",
        "tickers": ["AAPL"],
        "weights": [1.0],
        "initial_cash": 10000.0,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "transaction_cost_bps": 0,
    }
    r = client.post("/api/backtests", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["final_value"] == 10000.0
    assert body["total_return"] == 0.0
    assert body["name"] == "smoke"
    bt_id = body["id"]

    r2 = client.get(f"/api/backtests/{bt_id}")
    assert r2.status_code == 200
    assert r2.json()["id"] == bt_id

    rt = client.get(f"/api/backtests/{bt_id}/trades")
    assert rt.status_code == 200
    trades_body = rt.json()
    assert len(trades_body["trades"]) == 1
    assert trades_body["trades"][0]["ticker"] == "AAPL"
    assert trades_body["trades"][0]["side"] == "buy"

    rp = client.get(f"/api/backtests/{bt_id}/portfolio_values")
    assert rp.status_code == 200
    points = rp.json()["points"]
    assert len(points) == len(days)
    assert points[0]["date"] == start.isoformat()


def test_post_backtest_unknown_ticker_returns_validation_error(client, db):
    payload = {
        "strategy": "buy_and_hold",
        "tickers": ["NOSUCH"],
        "weights": [1.0],
        "initial_cash": 10000.0,
        "start_date": "2024-01-02",
        "end_date": "2024-01-31",
    }
    r = client.post("/api/backtests", json=payload)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "unknown_tickers"


def test_post_backtest_weights_must_sum_to_one(client):
    payload = {
        "strategy": "buy_and_hold",
        "tickers": ["AAPL", "MSFT"],
        "weights": [0.7, 0.4],
        "initial_cash": 10000.0,
        "start_date": "2024-01-02",
        "end_date": "2024-01-31",
    }
    r = client.post("/api/backtests", json=payload)
    # Pydantic schema validation triggers FastAPI's own 422.
    assert r.status_code == 422


def test_get_unknown_backtest_returns_404(client):
    r = client.get("/api/backtests/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_get_trades_for_unknown_backtest_returns_404(client):
    r = client.get("/api/backtests/00000000-0000-0000-0000-000000000000/trades")
    assert r.status_code == 404


def test_post_backtest_unknown_strategy_rejected_at_schema(client):
    payload = {
        "strategy": "telepathic_alpha",
        "tickers": ["AAPL"],
        "weights": [1.0],
        "initial_cash": 10000.0,
        "start_date": "2024-01-02",
        "end_date": "2024-01-31",
    }
    r = client.post("/api/backtests", json=payload)
    assert r.status_code == 422


def test_monthly_rebalance_via_api(client, db):
    start, end = date(2024, 1, 2), date(2024, 4, 30)
    days = trading_days(start, end)
    _seed(db, "AAPL", start, end, [100.0 * (1 + 0.001 * i) for i in range(len(days))])
    _seed(db, "MSFT", start, end, [200.0] * len(days))

    payload = {
        "strategy": "monthly_rebalance",
        "tickers": ["AAPL", "MSFT"],
        "weights": [0.5, 0.5],
        "initial_cash": 10000.0,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "transaction_cost_bps": 10,
    }
    r = client.post("/api/backtests", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    bt_id = body["id"]

    rt = client.get(f"/api/backtests/{bt_id}/trades")
    assert rt.status_code == 200
    # First-day allocation (2) + at least 3 month-end rebalances ⇒ > 2 trades.
    assert len(rt.json()["trades"]) > 2
