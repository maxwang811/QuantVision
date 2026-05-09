from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app.core.time import add_trading_days, trading_days
from app.models.asset import Asset
from app.models.backtest import Backtest
from app.models.experiment_sweep import ExperimentSweep
from app.models.forecast import Forecast
from app.models.forecast_distribution_bin import ForecastDistributionBin
from app.models.forecast_path import ForecastPath
from app.models.model_run import ModelRun
from app.models.portfolio_value import PortfolioValue
from app.models.price import PriceHistory
from app.models.trade import Trade


def _seed_prices(db, ticker: str, end: date, n_days: int = 320, *, base: float = 100.0):
    asset = Asset(ticker=ticker, name=ticker, asset_class="equity")
    db.add(asset)
    db.flush()
    start = add_trading_days(end, -(n_days - 1))
    for i, d in enumerate(trading_days(start, end)):
        price = base * (1.0 + 0.0005 * i + 0.00001 * (i % 5))
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


def _completed_backtest(db, *, created_at: datetime | None = None) -> Backtest:
    bt = Backtest(
        id=uuid.uuid4(),
        name="baseline backtest",
        strategy="buy_and_hold",
        params={"target_weights": {"SPY": 1.0}},
        initial_cash=Decimal("10000"),
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 5),
        transaction_cost_bps=0,
        final_value=Decimal("11000"),
        total_return=Decimal("0.10"),
        annualized_return=Decimal("0.12"),
        volatility=Decimal("0.20"),
        sharpe_ratio=Decimal("1.25"),
        max_drawdown=Decimal("-0.05"),
        status="completed",
        created_at=created_at or datetime(2024, 1, 10, tzinfo=UTC),
        completed_at=created_at or datetime(2024, 1, 10, tzinfo=UTC),
    )
    db.add(bt)
    for i, value in enumerate([10000, 10500, 11000]):
        db.add(
            PortfolioValue(
                backtest_id=bt.id,
                date=date(2024, 1, 2) + timedelta(days=i),
                cash=Decimal("0"),
                holdings_value=Decimal(str(value)),
                total_value=Decimal(str(value)),
            )
        )
    db.commit()
    return bt


def _completed_forecast(db, *, created_at: datetime | None = None) -> Forecast:
    fc = Forecast(
        id=uuid.uuid4(),
        name="baseline forecast",
        method="monte_carlo",
        params={"tickers": ["SPY"], "weights": [1.0], "lookback_days": 252},
        initial_value=Decimal("10000"),
        horizon_months=12,
        horizon_trading_days=252,
        n_simulations=1000,
        as_of_date=date(2024, 1, 5),
        lookback_start=date(2023, 1, 5),
        lookback_end=date(2024, 1, 5),
        random_seed=7,
        expected_value=Decimal("11200"),
        median_value=Decimal("11100"),
        p10_value=Decimal("9000"),
        p90_value=Decimal("13000"),
        probability_of_loss=Decimal("0.20"),
        probability_beat_benchmark=Decimal("0.55"),
        annualized_volatility=Decimal("0.18"),
        expected_return=Decimal("0.12"),
        status="completed",
        created_at=created_at or datetime(2024, 1, 11, tzinfo=UTC),
        completed_at=created_at or datetime(2024, 1, 11, tzinfo=UTC),
    )
    db.add(fc)
    for i, (lower, upper, count) in enumerate([(8000, 10000, 200), (10000, 12000, 500)]):
        db.add(
            ForecastDistributionBin(
                forecast_id=fc.id,
                bin_index=i,
                bin_lower=Decimal(str(lower)),
                bin_upper=Decimal(str(upper)),
                count=count,
            )
        )
    db.add(ForecastPath(forecast_id=fc.id, path_index=0, rank_label="median", values=[10000, 11100]))
    db.commit()
    return fc


def test_list_experiments_filters_and_sorts(client, db):
    _completed_backtest(db, created_at=datetime(2024, 1, 10, tzinfo=UTC))
    _completed_forecast(db, created_at=datetime(2024, 1, 11, tzinfo=UTC))
    db.add(
        ModelRun(
            id=uuid.uuid4(),
            name="ranking run",
            tickers=["SPY"],
            benchmark_ticker="SPY",
            start_date=date(2023, 1, 1),
            end_date=date(2024, 1, 1),
            label_horizon_days=20,
            training_lookback_days=756,
            selected_model="xgboost",
            params={},
            metrics={"models": {"xgboost": {"auc": 0.7, "accuracy": 0.6}}},
            status="completed",
            created_at=datetime(2024, 1, 12, tzinfo=UTC),
        )
    )
    db.add(
        ExperimentSweep(
            id=uuid.uuid4(),
            name="cost sweep",
            kind="backtest",
            status="completed",
            base_request={},
            sweep_parameters={"transaction_cost_bps": [0, 10]},
            total_runs=2,
            completed_runs=2,
            failed_runs=0,
            created_at=datetime(2024, 1, 13, tzinfo=UTC),
        )
    )
    db.commit()

    r = client.get("/api/experiments")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 4
    assert body["items"][0]["kind"] == "sweep"

    r_kind = client.get("/api/experiments?kind=forecast")
    assert r_kind.status_code == 200
    assert r_kind.json()["total"] == 1
    assert r_kind.json()["items"][0]["name"] == "baseline forecast"

    r_q = client.get("/api/experiments?q=ranking")
    assert r_q.status_code == 200
    assert r_q.json()["items"][0]["kind"] == "model_run"


def test_compare_completed_runs_and_rejects_failed(client, db):
    bt = _completed_backtest(db)
    fc = _completed_forecast(db)
    failed = Backtest(
        id=uuid.uuid4(),
        name="failed",
        strategy="buy_and_hold",
        params={"target_weights": {"SPY": 1.0}},
        initial_cash=Decimal("10000"),
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 5),
        transaction_cost_bps=0,
        status="failed",
        error_message="boom",
    )
    db.add(failed)
    db.commit()

    r = client.post(
        "/api/experiments/compare",
        json={"backtest_ids": [str(bt.id)], "forecast_ids": [str(fc.id)]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["backtests"][0]["normalized_curve"][0]["value"] == 100.0
    assert body["forecasts"][0]["distribution_bins"][0]["count"] == 200

    r_failed = client.post(
        "/api/experiments/compare",
        json={"backtest_ids": [str(failed.id)], "forecast_ids": []},
    )
    assert r_failed.status_code == 422
    assert r_failed.json()["error"]["code"] == "compare_invalid_status"


def test_backtest_and_forecast_sweeps_run_and_persist_children(client, db):
    end = date(2025, 6, 30)
    _seed_prices(db, "SPY", end)
    start = add_trading_days(end, -20)

    backtest_payload = {
        "kind": "backtest",
        "name": "cost sweep",
        "base_request": {
            "name": "cost sweep run",
            "strategy": "buy_and_hold",
            "tickers": ["SPY"],
            "weights": [1.0],
            "initial_cash": 10000.0,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "transaction_cost_bps": 0,
        },
        "sweep_parameters": {"transaction_cost_bps": [0, 10]},
    }
    rb = client.post("/api/experiment-sweeps", json=backtest_payload)
    assert rb.status_code == 200, rb.text
    backtest_sweep = rb.json()
    assert backtest_sweep["status"] == "completed"
    assert backtest_sweep["total_runs"] == 2

    rb_runs = client.get(f"/api/experiment-sweeps/{backtest_sweep['id']}/runs")
    assert rb_runs.status_code == 200
    assert len(rb_runs.json()["runs"]) == 2
    assert all(run["backtest_id"] for run in rb_runs.json()["runs"])

    forecast_payload = {
        "kind": "forecast",
        "name": "seed sweep",
        "base_request": {
            "name": "seed sweep run",
            "method": "bootstrap",
            "tickers": ["SPY"],
            "weights": [1.0],
            "initial_value": 10000.0,
            "horizon_months": 1,
            "n_simulations": 100,
            "lookback_days": 252,
            "as_of_date": end.isoformat(),
        },
        "sweep_parameters": {"random_seed": [7, 42]},
    }
    rf = client.post("/api/experiment-sweeps", json=forecast_payload)
    assert rf.status_code == 200, rf.text
    forecast_sweep = rf.json()
    assert forecast_sweep["status"] == "completed"
    assert forecast_sweep["total_runs"] == 2

    rf_runs = client.get(f"/api/experiment-sweeps/{forecast_sweep['id']}/runs")
    assert rf_runs.status_code == 200
    assert all(run["forecast_id"] for run in rf_runs.json()["runs"])


def test_exports_return_json_bundles_and_csv_tables(client, db):
    asset = Asset(ticker="SPY", name="SPY", asset_class="equity")
    db.add(asset)
    db.flush()
    bt = _completed_backtest(db)
    db.add(
        Trade(
            id=uuid.uuid4(),
            backtest_id=bt.id,
            asset_id=asset.id,
            date=bt.start_date,
            side="buy",
            quantity=Decimal("10"),
            price=Decimal("100"),
            transaction_cost=Decimal("0"),
            notional=Decimal("1000"),
        )
    )
    fc = _completed_forecast(db)
    db.commit()

    r_json = client.get(f"/api/exports/backtests/{bt.id}?format=json")
    assert r_json.status_code == 200
    body = r_json.json()
    assert body["summary"]["id"] == str(bt.id)
    assert body["portfolio_values"]
    assert body["trades"][0]["ticker"] == "SPY"

    r_csv = client.get(f"/api/exports/forecasts/{fc.id}?format=csv&artifact=distribution")
    assert r_csv.status_code == 200
    assert "text/csv" in r_csv.headers["content-type"]
    assert "count" in r_csv.text

    r_compare = client.post(
        "/api/exports/compare?format=csv",
        json={"backtest_ids": [str(bt.id)], "forecast_ids": [str(fc.id)]},
    )
    assert r_compare.status_code == 200
    assert "backtest" in r_compare.text
