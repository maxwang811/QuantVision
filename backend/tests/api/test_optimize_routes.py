"""End-to-end tests for /api/optimize."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.time import add_trading_days, trading_days
from app.models.asset import Asset
from app.models.price import PriceHistory


def _seed_prices(
    db, ticker: str, end: date, *, n_days: int = 320,
    base: float = 100.0, slope: float = 0.0005, jitter: float = 0.00002,
):
    asset = Asset(ticker=ticker, name=ticker, asset_class="equity")
    db.add(asset)
    db.flush()
    start = add_trading_days(end, -(n_days - 1))
    days = trading_days(start, end)
    for i, d in enumerate(days):
        price = base * (1.0 + slope * i + jitter * (i % 7))
        db.add(PriceHistory(
            asset_id=asset.id, date=d,
            adj_close=Decimal(str(price)), close=Decimal(str(price)),
        ))
    db.commit()
    return asset


def test_optimize_happy_path(client, db):
    end = date(2025, 6, 30)
    _seed_prices(db, "AAA", end, base=100.0, slope=0.0006)
    _seed_prices(db, "BBB", end, base=150.0, slope=0.0004, jitter=0.00005)
    _seed_prices(db, "CCC", end, base=80.0, slope=0.0008, jitter=0.00003)

    r = client.post("/api/optimize", json={
        "tickers": ["AAA", "BBB", "CCC"],
        "lookback_days": 252,
        "risk_free_rate": 0.0,
        "n_frontier_points": 15,
        "as_of_date": "2025-06-30",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tickers"] == ["AAA", "BBB", "CCC"]
    assert body["n_observations"] >= 250
    assert len(body["min_variance"]["weights"]) == 3
    assert abs(sum(body["min_variance"]["weights"]) - 1.0) < 1e-3
    assert abs(sum(body["max_sharpe"]["weights"]) - 1.0) < 1e-3
    assert len(body["frontier"]) >= 5
    assert body["target_return"] is None
    assert body["lookback_start"] <= body["lookback_end"]


def test_optimize_unknown_ticker_returns_422(client, db):
    end = date(2025, 6, 30)
    _seed_prices(db, "AAA", end)
    _seed_prices(db, "BBB", end)
    r = client.post("/api/optimize", json={
        "tickers": ["AAA", "ZZZ"],
        "lookback_days": 252,
    })
    assert r.status_code == 422


def test_optimize_single_ticker_rejected_by_schema(client, db):
    r = client.post("/api/optimize", json={
        "tickers": ["AAA"],
        "lookback_days": 252,
    })
    assert r.status_code == 422


def test_optimize_with_target_return(client, db):
    end = date(2025, 6, 30)
    _seed_prices(db, "AAA", end, base=100.0, slope=0.0006)
    _seed_prices(db, "BBB", end, base=150.0, slope=0.0004, jitter=0.00005)

    r = client.post("/api/optimize", json={
        "tickers": ["AAA", "BBB"],
        "lookback_days": 252,
        "target_return": 0.10,
        "as_of_date": "2025-06-30",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["target_return"] is not None
    assert abs(sum(body["target_return"]["weights"]) - 1.0) < 1e-3
