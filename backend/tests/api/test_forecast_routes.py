"""End-to-end tests for /api/forecasts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.time import add_trading_days, trading_days
from app.models.asset import Asset
from app.models.price import PriceHistory


def _seed_prices(db, ticker: str, end: date, n_days: int = 320, *, base: float = 100.0):
    asset = Asset(ticker=ticker, name=ticker, asset_class="equity")
    db.add(asset)
    db.flush()

    start = add_trading_days(end, -(n_days - 1))
    days = trading_days(start, end)
    assert len(days) == n_days

    for i, d in enumerate(days):
        # Smooth, deterministic history with a tiny ticker-specific slope so
        # multi-asset tests avoid identical covariance columns.
        price = base * (1.0 + 0.0005 * i + 0.00002 * (i % 7))
        db.add(
            PriceHistory(
                asset_id=asset.id,
                date=d,
                adj_close=Decimal(str(price)),
                close=Decimal(str(price)),
            )
        )
    db.commit()
    return asset


def _seed_forecast_universe(db, end: date = date(2025, 6, 30)) -> None:
    _seed_prices(db, "SPY", end, base=100.0)
    _seed_prices(db, "AAPL", end, base=180.0)
    _seed_prices(db, "MSFT", end, base=250.0)


def _forecast_payload(**overrides):
    payload = {
        "method": "monte_carlo",
        "tickers": ["SPY", "AAPL", "MSFT"],
        "weights": [0.5, 0.25, 0.25],
        "initial_value": 10000.0,
        "horizon_months": 1,
        "n_simulations": 500,
        "lookback_days": 252,
        "as_of_date": "2025-06-30",
        "benchmark_ticker": "SPY",
        "random_seed": 123,
    }
    payload.update(overrides)
    return payload


def test_post_forecast_manual_happy_path(client, db):
    _seed_forecast_universe(db)

    r = client.post("/api/forecasts", json=_forecast_payload())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["method"] == "monte_carlo"
    assert body["tickers"] == ["SPY", "AAPL", "MSFT"]
    assert body["weights"] == [0.5, 0.25, 0.25]
    assert body["initial_value"] == 10000.0
    assert body["expected_value"] is not None
    assert body["median_value"] is not None
    assert body["probability_of_loss"] is not None
    assert body["probability_beat_benchmark"] is not None


def test_get_forecast_returns_summary(client, db):
    _seed_forecast_universe(db)
    created = client.post("/api/forecasts", json=_forecast_payload()).json()

    r = client.get(f"/api/forecasts/{created['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == created["id"]
    assert body["status"] == "completed"
    assert body["p50_value"] if "p50_value" in body else body["median_value"] is not None


def test_get_forecast_paths_returns_ordered_sample_paths(client, db):
    _seed_forecast_universe(db)
    created = client.post("/api/forecasts", json=_forecast_payload()).json()

    r = client.get(f"/api/forecasts/{created['id']}/paths")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["forecast_id"] == created["id"]
    assert body["initial_value"] == 10000.0
    assert len(body["step_dates"]) == created["horizon_trading_days"] + 1
    assert len(body["paths"]) == 100
    assert [p["index"] for p in body["paths"]] == list(range(100))
    assert {p["rank_label"] for p in body["paths"] if p["rank_label"]} >= {
        "best",
        "median",
        "worst",
    }
    assert len(body["paths"][0]["values"]) == created["horizon_trading_days"] + 1


def test_get_forecast_distribution_returns_bins_and_percentiles(client, db):
    _seed_forecast_universe(db)
    created = client.post("/api/forecasts", json=_forecast_payload()).json()

    r = client.get(f"/api/forecasts/{created['id']}/distribution")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["forecast_id"] == created["id"]
    assert body["initial_value"] == 10000.0
    assert body["bin_count"] == 50
    assert len(body["bins"]) == 50
    assert sum(b["count"] for b in body["bins"]) == created["n_simulations"]
    assert body["percentiles"]["p50"] == created["median_value"]
    assert body["percentiles"]["p5"] <= body["percentiles"]["p50"] <= body["percentiles"]["p95"]


def test_post_forecast_from_backtest_id(client, db):
    end = date(2025, 6, 30)
    _seed_prices(db, "SPY", end, base=100.0)
    start = add_trading_days(end, -20)

    backtest_payload = {
        "strategy": "buy_and_hold",
        "tickers": ["SPY"],
        "weights": [1.0],
        "initial_cash": 10000.0,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "transaction_cost_bps": 0,
    }
    bt_response = client.post("/api/backtests", json=backtest_payload)
    assert bt_response.status_code == 200, bt_response.text
    bt = bt_response.json()
    assert bt["status"] == "completed"

    forecast_payload = {
        "method": "bootstrap",
        "from_backtest_id": bt["id"],
        "horizon_months": 1,
        "n_simulations": 500,
        "lookback_days": 252,
        "random_seed": 456,
    }
    r = client.post("/api/forecasts", json=forecast_payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["method"] == "bootstrap"
    assert body["from_backtest_id"] == bt["id"]
    assert body["tickers"] == ["SPY"]
    assert body["weights"] == [1.0]
    assert body["initial_value"] == bt["final_value"]


def test_post_forecast_unknown_ticker_returns_validation_error(client):
    r = client.post(
        "/api/forecasts",
        json=_forecast_payload(tickers=["NOPE"], weights=[1.0], benchmark_ticker=None),
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "unknown_tickers"


def test_get_unknown_forecast_returns_404(client):
    r = client.get("/api/forecasts/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_get_paths_for_unknown_forecast_returns_404(client):
    r = client.get("/api/forecasts/00000000-0000-0000-0000-000000000000/paths")
    assert r.status_code == 404


def test_get_distribution_for_unknown_forecast_returns_404(client):
    r = client.get(
        "/api/forecasts/00000000-0000-0000-0000-000000000000/distribution"
    )
    assert r.status_code == 404
