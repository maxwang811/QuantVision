"""End-to-end forecast run against the test DB.

Seeds synthetic prices, runs `run_forecast`, and asserts that the row reaches
'completed' status with all summary metrics populated, the right number of
sample paths persisted, and the right number of histogram bins.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.errors import ValidationError
from app.models.asset import Asset
from app.models.forecast_distribution_bin import ForecastDistributionBin
from app.models.forecast_path import ForecastPath
from app.models.price import PriceHistory
from app.schemas.forecast import ForecastCreate
from app.services.forecast.runner import run_forecast


def _seed_asset(db, ticker: str) -> Asset:
    asset = Asset(ticker=ticker, name=ticker, asset_class="equity")
    db.add(asset)
    db.flush()
    return asset


def _seed_synthetic_prices(
    db, asset: Asset, end_date: date, n_days: int, seed: int = 0
) -> None:
    """Seed `n_days` of synthetic geometric brownian motion prices ending on `end_date`.

    Uses a deterministic RNG so test outcomes don't depend on global numpy state.
    Skips weekends to match the trading-day calendar.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    log_rets = rng.normal(0.0005, 0.012, size=n_days - 1)
    prices = [100.0]
    for r in log_rets:
        prices.append(prices[-1] * math.exp(r))

    # Walk back from end_date, skipping weekends.
    days: list[date] = []
    cursor = end_date
    while len(days) < n_days:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    days.reverse()

    for d, p in zip(days, prices, strict=True):
        db.add(PriceHistory(asset_id=asset.id, date=d, adj_close=Decimal(str(p))))
    db.flush()


def _seed_three_assets(db, end_date: date, n_days: int = 1500):
    spy = _seed_asset(db, "SPY")
    aapl = _seed_asset(db, "AAPL")
    msft = _seed_asset(db, "MSFT")
    _seed_synthetic_prices(db, spy, end_date, n_days, seed=1)
    _seed_synthetic_prices(db, aapl, end_date, n_days, seed=2)
    _seed_synthetic_prices(db, msft, end_date, n_days, seed=3)
    return spy, aapl, msft


def _basic_forecast_request(
    *, method: str = "monte_carlo", as_of: date | None = None, **overrides
) -> ForecastCreate:
    payload = {
        "method": method,
        "tickers": ["SPY", "AAPL", "MSFT"],
        "weights": [0.5, 0.25, 0.25],
        "initial_value": 10_000.0,
        "horizon_months": 12,
        "n_simulations": 1000,
        "lookback_days": 252,
        "as_of_date": as_of,
        "random_seed": 12345,
    }
    payload.update(overrides)
    return ForecastCreate(**payload)


def test_monte_carlo_forecast_completes(db):
    end_date = date(2025, 6, 30)
    _seed_three_assets(db, end_date)

    req = _basic_forecast_request(as_of=end_date)
    fc = run_forecast(db, req)
    assert fc.status == "completed", fc.error_message
    assert fc.completed_at is not None
    assert fc.error_message is None
    assert fc.expected_value is not None
    assert fc.median_value is not None
    assert fc.p5_value is not None
    assert fc.p95_value is not None
    assert fc.probability_of_loss is not None
    assert fc.annualized_volatility is not None
    assert fc.expected_return is not None


def test_monte_carlo_forecast_persists_sample_paths(db):
    end_date = date(2025, 6, 30)
    _seed_three_assets(db, end_date)

    req = _basic_forecast_request(as_of=end_date)
    fc = run_forecast(db, req)
    paths = list(
        db.scalars(
            select(ForecastPath).where(ForecastPath.forecast_id == fc.id)
        )
    )
    # Default n_sample_paths is 100.
    assert len(paths) == 100
    # Each path has horizon_trading_days + 1 entries.
    expected_len = fc.horizon_trading_days + 1
    for p in paths:
        assert len(p.values) == expected_len
        assert p.values[0] == pytest.approx(10_000.0, abs=1e-6)
    labels = {p.rank_label for p in paths if p.rank_label}
    assert {"best", "worst", "median"}.issubset(labels)


def test_monte_carlo_forecast_persists_histogram(db):
    end_date = date(2025, 6, 30)
    _seed_three_assets(db, end_date)

    req = _basic_forecast_request(as_of=end_date)
    fc = run_forecast(db, req)
    bins = list(
        db.scalars(
            select(ForecastDistributionBin)
            .where(ForecastDistributionBin.forecast_id == fc.id)
            .order_by(ForecastDistributionBin.bin_index)
        )
    )
    assert len(bins) == 50
    assert sum(b.count for b in bins) == fc.n_simulations
    # Edges monotonic.
    for i in range(1, len(bins)):
        assert bins[i].bin_lower >= bins[i - 1].bin_lower


def test_bootstrap_forecast_completes(db):
    end_date = date(2025, 6, 30)
    _seed_three_assets(db, end_date)

    req = _basic_forecast_request(as_of=end_date, method="bootstrap")
    fc = run_forecast(db, req)
    assert fc.status == "completed", fc.error_message
    assert fc.expected_value is not None


def test_ml_drift_forecast_completes_and_records_predicted_drift(db):
    end_date = date(2025, 6, 30)
    _seed_three_assets(db, end_date, n_days=1600)

    req = _basic_forecast_request(
        as_of=end_date, method="ml_drift", lookback_days=1260
    )
    fc = run_forecast(db, req)
    assert fc.status == "completed", fc.error_message
    assert "ml_predicted_drift" in fc.params
    drift = fc.params["ml_predicted_drift"]
    assert "mu_hist" in drift and "mu_pred" in drift and "mu_final" in drift
    assert len(drift["mu_final"]) == 3


def test_unknown_ticker_raises_validation_error(db):
    req = _basic_forecast_request(tickers=["NOPE"], weights=[1.0])
    with pytest.raises(ValidationError) as exc:
        run_forecast(db, req)
    assert exc.value.code == "unknown_tickers"


def test_insufficient_history_raises_validation_error(db):
    end_date = date(2025, 6, 30)
    spy = _seed_asset(db, "SPY")
    # Only 50 days of data - less than the default 252-day lookback x 0.95.
    _seed_synthetic_prices(db, spy, end_date, 50, seed=1)

    req = ForecastCreate(
        method="monte_carlo",
        tickers=["SPY"],
        weights=[1.0],
        initial_value=10_000.0,
        horizon_months=6,
        n_simulations=500,
        lookback_days=252,
        as_of_date=end_date,
    )
    with pytest.raises(ValidationError) as exc:
        run_forecast(db, req)
    assert exc.value.code == "insufficient_history"


def test_seed_reproducibility(db):
    end_date = date(2025, 6, 30)
    _seed_three_assets(db, end_date)

    req1 = _basic_forecast_request(as_of=end_date)
    req2 = _basic_forecast_request(as_of=end_date)
    fc1 = run_forecast(db, req1)
    fc2 = run_forecast(db, req2)
    assert fc1.expected_value == fc2.expected_value
    assert fc1.median_value == fc2.median_value
    assert fc1.p5_value == fc2.p5_value
    assert fc1.p95_value == fc2.p95_value


def test_random_seed_recorded(db):
    end_date = date(2025, 6, 30)
    _seed_three_assets(db, end_date)

    req = _basic_forecast_request(as_of=end_date, random_seed=None)
    fc = run_forecast(db, req)
    assert fc.random_seed > 0  # generator filled it in


def test_benchmark_probability_computed_when_benchmark_set(db):
    end_date = date(2025, 6, 30)
    _seed_three_assets(db, end_date)

    req = _basic_forecast_request(as_of=end_date, benchmark_ticker="SPY")
    fc = run_forecast(db, req)
    assert fc.probability_beat_benchmark is not None
    p = float(fc.probability_beat_benchmark)
    assert 0.0 <= p <= 1.0


def test_benchmark_probability_none_when_no_benchmark(db):
    end_date = date(2025, 6, 30)
    _seed_three_assets(db, end_date)

    req = _basic_forecast_request(as_of=end_date, benchmark_ticker=None)
    fc = run_forecast(db, req)
    assert fc.probability_beat_benchmark is None


def test_unknown_benchmark_ticker_rejected(db):
    end_date = date(2025, 6, 30)
    _seed_three_assets(db, end_date)

    req = _basic_forecast_request(as_of=end_date, benchmark_ticker="ZZZZ")
    with pytest.raises(ValidationError) as exc:
        run_forecast(db, req)
    assert exc.value.code == "unknown_tickers"
