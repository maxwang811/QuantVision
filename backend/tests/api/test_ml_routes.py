"""End-to-end tests for Stage 6 ML model routes and ML ranking backtests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.time import trading_days
from app.models.asset import Asset
from app.models.price import PriceHistory


def _seed_ml_universe(db) -> tuple[date, date]:
    seed_start, seed_end = date(2023, 1, 2), date(2024, 6, 28)
    days = trading_days(seed_start, seed_end)
    specs = {
        "AAA": 1.0020,
        "BBB": 0.9990,
        "SPY": 1.0005,
    }
    for ticker, daily_factor in specs.items():
        asset = Asset(ticker=ticker, name=ticker, asset_class="equity")
        db.add(asset)
        db.flush()
        for i, d in enumerate(days):
            db.add(
                PriceHistory(
                    asset_id=asset.id,
                    date=d,
                    adj_close=Decimal(str(100.0 * (daily_factor**i))),
                    volume=1_000_000 + i,
                )
            )
    db.commit()
    return days[180], days[260]


def test_create_model_run_and_get_predictions(client, db):
    start, end = _seed_ml_universe(db)
    payload = {
        "name": "stage6-smoke",
        "tickers": ["AAA", "BBB"],
        "benchmark_ticker": "SPY",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "label_horizon_days": 5,
        "training_lookback_days": 126,
        "selected_model": "xgboost",
        "random_seed": 3,
    }

    r = client.post("/api/model-runs", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["metrics"]["models"]["xgboost"]["n_labeled_predictions"] > 0

    preds = client.get(f"/api/model-runs/{body['id']}/predictions?model_name=xgboost")
    assert preds.status_code == 200, preds.text
    rows = preds.json()["predictions"]
    assert rows
    first_date = rows[0]["date"]
    first_date_rows = [p for p in rows if p["date"] == first_date]
    assert next(p for p in first_date_rows if p["ticker"] == "AAA")["rank"] == 1


def test_ml_ranking_backtest_auto_creates_model_run(client, db):
    start, end = _seed_ml_universe(db)
    payload = {
        "name": "ml-ranking-backtest",
        "strategy": "ml_ranking",
        "tickers": ["AAA", "BBB"],
        "weights": [0.5, 0.5],
        "initial_cash": 10000.0,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "transaction_cost_bps": 0,
        "benchmark_ticker": "SPY",
        "strategy_params": {
            "top_n": 1,
            "selected_model": "xgboost",
            "training_lookback_days": 126,
            "label_horizon_days": 5,
            "random_seed": 3,
        },
    }

    r = client.post("/api/backtests", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["model_run_id"]

    trades = client.get(f"/api/backtests/{body['id']}/trades")
    assert trades.status_code == 200
    buy_trades = [t for t in trades.json()["trades"] if t["side"] == "buy"]
    assert buy_trades
    assert buy_trades[0]["ticker"] == "AAA"
