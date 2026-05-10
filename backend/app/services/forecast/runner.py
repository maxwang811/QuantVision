"""Runner: validation, persistence, orchestration for the forecasting engine.

The only layer that touches the DB. The engine module is pure; the runner wraps
it in a transaction lifecycle, persists the summary statistics + sampled paths +
histogram bins, and records the final result on the `forecasts` row.
"""

from __future__ import annotations

import logging
import secrets
import uuid
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import NotFoundError, ValidationError
from app.core.time import add_trading_days
from app.models.asset import Asset
from app.models.backtest import Backtest
from app.models.forecast import Forecast
from app.models.forecast_distribution_bin import ForecastDistributionBin
from app.models.forecast_path import ForecastPath
from app.models.price import PriceHistory
from app.models.trade import Trade
from app.schemas.forecast import ForecastCreate
from app.services.data.returns import build_log_returns_matrix
from app.services.forecast import aggregation, engine, ml

log = logging.getLogger(__name__)

_TRADING_DAYS_PER_YEAR = 252


def run_forecast(db: Session, req: ForecastCreate) -> Forecast:
    """Validate, run, persist. Always returns a Forecast row (status reflects outcome).

    On success the returned row has `status='completed'` with all summary metrics
    set, and child rows in `forecast_paths` and `forecast_distribution_bins`. On
    validation failure (unknown ticker, insufficient history, bad backtest seed,
    etc.) we raise a `ValidationError` BEFORE creating the row — the FastAPI
    error handler turns that into a 422. Engine-time failures (numerical
    explosion etc.) are swallowed and persisted as `status='failed'` with the
    exception message.
    """
    settings = get_settings()
    seed = req.random_seed if req.random_seed is not None else secrets.randbits(32)

    # Resolve the basket and starting value before persisting anything — that way
    # validation failures don't leave dangling 'running' rows.
    if req.from_backtest_id is not None:
        tickers, weights, initial_value, default_as_of = _seed_from_backtest(
            db, req.from_backtest_id
        )
    else:
        # Schema validation guarantees these are non-None when from_backtest_id is None.
        assert req.tickers is not None
        assert req.weights is not None
        assert req.initial_value is not None
        tickers = list(req.tickers)
        weights = list(req.weights)
        initial_value = float(req.initial_value)
        default_as_of = None

    # Validate tickers exist + benchmark.
    asset_map = _load_assets(db, tickers)
    if req.benchmark_ticker:
        bench_asset = db.scalar(
            select(Asset).where(Asset.ticker == req.benchmark_ticker)
        )
        if bench_asset is None:
            raise ValidationError(
                f"unknown benchmark ticker: {req.benchmark_ticker}",
                code="unknown_tickers",
            )
        asset_map[req.benchmark_ticker] = bench_asset

    # Resolve as_of_date: explicit > derived from backtest > latest common price date.
    as_of_date = req.as_of_date or default_as_of or _latest_common_price_date(
        db, [asset_map[t] for t in tickers]
    )
    if as_of_date is None:
        raise ValidationError(
            "no overlapping price coverage across the requested tickers",
            code="insufficient_history",
        )

    # Fetch lookback returns.
    lookback_start_calendar = as_of_date - _calendar_days_for_lookback(req.lookback_days)
    returns_matrix, common_dates = build_log_returns_matrix(
        db, [asset_map[t] for t in tickers], lookback_start_calendar, as_of_date
    )
    if returns_matrix.shape[0] < int(req.lookback_days * 0.95):
        raise ValidationError(
            f"insufficient overlapping history: got {returns_matrix.shape[0]} return"
            f" observations, need at least {int(req.lookback_days * 0.95)}",
            code="insufficient_history",
        )

    horizon_trading_days = round(req.horizon_months / 12.0 * _TRADING_DAYS_PER_YEAR)
    lookback_start = common_dates[0]
    lookback_end = common_dates[-1]

    # Persist 'running' row up-front for status visibility & error reporting.
    fc = Forecast(
        id=uuid.uuid4(),
        name=req.name,
        method=req.method,
        params={
            "tickers": tickers,
            "weights": weights,
            "lookback_days": req.lookback_days,
            "block_size": 1,  # bootstrap default; reserved for future UI knob
        },
        initial_value=Decimal(str(initial_value)),
        horizon_months=req.horizon_months,
        horizon_trading_days=horizon_trading_days,
        n_simulations=req.n_simulations,
        as_of_date=as_of_date,
        lookback_start=lookback_start,
        lookback_end=lookback_end,
        benchmark_ticker=req.benchmark_ticker,
        from_backtest_id=req.from_backtest_id,
        random_seed=int(seed),
        status="running",
    )
    db.add(fc)
    db.commit()

    try:
        weights_arr = np.asarray(weights, dtype=np.float64)
        rng = np.random.default_rng(seed)
        if req.method == "monte_carlo":
            sim = engine.simulate_monte_carlo(
                returns_matrix, weights_arr, initial_value,
                horizon_trading_days, req.n_simulations, rng,
            )
        elif req.method == "bootstrap":
            sim = engine.simulate_bootstrap(
                returns_matrix, weights_arr, initial_value,
                horizon_trading_days, req.n_simulations, rng,
            )
        elif req.method == "ml_drift":
            ml_result = ml.predict_drift(returns_matrix)
            sim = engine.simulate_monte_carlo(
                returns_matrix, weights_arr, initial_value,
                horizon_trading_days, req.n_simulations, rng,
                drift_override=ml_result.mu_final,
            )
            params_with_ml = dict(fc.params)
            params_with_ml["ml_predicted_drift"] = {
                "mu_hist": ml_result.mu_hist.tolist(),
                "mu_pred": ml_result.mu_pred.tolist(),
                "mu_final": ml_result.mu_final.tolist(),
            }
            fc.params = params_with_ml
        else:  # pragma: no cover — schema enum prevents this
            raise ValueError(f"unknown method: {req.method}")

        horizon_years = horizon_trading_days / float(_TRADING_DAYS_PER_YEAR)
        summary = aggregation.summarize_distribution(
            sim.terminal_values, initial_value, horizon_years
        )
        sample_paths, labels = aggregation.select_sample_paths(
            sim.paths, settings.forecast_default_n_sample_paths
        )
        bins = aggregation.build_histogram(
            sim.terminal_values, settings.forecast_default_n_bins
        )

        prob_beat = None
        if req.benchmark_ticker:
            bench_returns_matrix, _ = build_log_returns_matrix(
                db, [asset_map[req.benchmark_ticker]], lookback_start_calendar, as_of_date
            )
            if bench_returns_matrix.shape[0] >= int(req.lookback_days * 0.95):
                bench_sim = engine.simulate_monte_carlo(
                    bench_returns_matrix,
                    np.array([1.0]),
                    initial_value,
                    horizon_trading_days,
                    req.n_simulations,
                    np.random.default_rng(int(seed) + 1),
                )
                prob_beat = aggregation.prob_beat_benchmark(
                    sim.terminal_values, bench_sim.terminal_values
                )

        _persist_summary(fc, summary, prob_beat)
        _persist_paths(db, fc.id, sample_paths, labels)
        _persist_histogram(db, fc.id, bins)

        fc.status = "completed"
        fc.completed_at = _utc_now(db)
    except ValidationError:
        # Re-raise so the route handler turns it into a 422; mark the row failed first.
        fc.status = "failed"
        fc.error_message = "validation error during forecast execution"
        db.commit()
        raise
    except Exception as e:
        log.exception("forecast %s failed", fc.id)
        fc.status = "failed"
        fc.error_message = str(e)[:1000]
    finally:
        db.commit()
        db.refresh(fc)

    return fc


def get_forecast_or_404(db: Session, forecast_id: uuid.UUID) -> Forecast:
    fc = db.get(Forecast, forecast_id)
    if fc is None:
        raise NotFoundError(f"forecast not found: {forecast_id}")
    return fc


def compute_step_dates(as_of: date, n_steps: int) -> list[date]:
    """Build the X-axis for path visualization: as_of plus n_steps trading days."""
    out = [as_of]
    cursor = as_of
    for _ in range(n_steps):
        cursor = add_trading_days(cursor, 1)
        out.append(cursor)
    return out


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_assets(db: Session, tickers: list[str]) -> dict[str, Asset]:
    rows = list(db.scalars(select(Asset).where(Asset.ticker.in_(tickers))))
    found = {a.ticker: a for a in rows}
    missing = [t for t in tickers if t not in found]
    if missing:
        raise ValidationError(
            f"unknown tickers: {', '.join(missing)}", code="unknown_tickers"
        )
    return found


def _calendar_days_for_lookback(lookback_days: int):
    """Convert trading-day count into a calendar-day buffer for the SQL window.

    We always over-fetch (multiply by ~1.5) and let the dates intersection trim
    the result. 365/252 ≈ 1.45, then add 30 days margin to absorb partial weeks.
    """
    from datetime import timedelta

    return timedelta(days=int(lookback_days * 365 / 252) + 30)


def _latest_common_price_date(db: Session, assets: list[Asset]) -> date | None:
    """Earliest of each asset's latest price date — i.e., the most recent date
    on which ALL requested assets have a price observation."""
    if not assets:
        return None
    latest_dates = []
    for asset in assets:
        d = db.scalar(
            select(func.max(PriceHistory.date)).where(PriceHistory.asset_id == asset.id)
        )
        if d is None:
            return None
        latest_dates.append(d)
    return min(latest_dates)


def _seed_from_backtest(
    db: Session, backtest_id: uuid.UUID
) -> tuple[list[str], list[float], float, date]:
    """Reconstruct (tickers, weights, initial_value, as_of_date) from a backtest.

    Strategy:
      * Replay all `Trade` rows for the backtest, accumulating signed quantities
        per ticker (buy adds, sell subtracts).
      * Look up each held ticker's price on `backtest.end_date` and compute
        market value.
      * Re-normalize the holding values to weights summing to 1. Cash is rolled
        proportionally into the basket (documented simplification).
      * `initial_value` = `backtest.final_value`.
      * `as_of_date` = `backtest.end_date`.
    """
    bt = db.get(Backtest, backtest_id)
    if bt is None:
        raise ValidationError(
            f"backtest not found: {backtest_id}", code="backtest_not_found"
        )
    if bt.status != "completed":
        raise ValidationError(
            f"backtest {backtest_id} is not completed (status={bt.status})",
            code="backtest_not_completed",
        )
    if bt.final_value is None:
        raise ValidationError(
            f"backtest {backtest_id} has no final_value",
            code="backtest_not_completed",
        )

    trade_rows = list(
        db.execute(
            select(Trade, Asset.ticker)
            .join(Asset, Asset.id == Trade.asset_id)
            .where(Trade.backtest_id == backtest_id)
        )
    )
    holdings: dict[str, float] = defaultdict(float)
    for t, ticker in trade_rows:
        sign = 1.0 if t.side == "buy" else -1.0
        holdings[ticker] += sign * float(t.quantity)

    # Drop fully-closed positions.
    holdings = {t: q for t, q in holdings.items() if q > 1e-12}
    if not holdings:
        raise ValidationError(
            f"backtest {backtest_id} ended with no open positions (all cash);"
            " cannot seed a forecast",
            code="from_backtest_all_cash",
        )

    # Look up close prices on the backtest's end date.
    tickers = list(holdings.keys())
    asset_rows = list(db.scalars(select(Asset).where(Asset.ticker.in_(tickers))))
    asset_id_map = {a.ticker: a.id for a in asset_rows}

    end_prices: dict[str, float] = {}
    for ticker in tickers:
        price_row = db.scalar(
            select(PriceHistory)
            .where(PriceHistory.asset_id == asset_id_map[ticker])
            .where(PriceHistory.date <= bt.end_date)
            .order_by(PriceHistory.date.desc())
            .limit(1)
        )
        if price_row is None:
            raise ValidationError(
                f"no price for {ticker} on or before {bt.end_date}",
                code="insufficient_history",
            )
        end_prices[ticker] = float(price_row.adj_close)

    holding_values = {t: holdings[t] * end_prices[t] for t in tickers}
    total = sum(holding_values.values())
    if total <= 0:
        raise ValidationError(
            f"backtest {backtest_id} ended with no open positions (all cash);"
            " cannot seed a forecast",
            code="from_backtest_all_cash",
        )

    weights = [holding_values[t] / total for t in tickers]
    initial_value = float(bt.final_value)
    return tickers, weights, initial_value, bt.end_date


def _persist_summary(
    fc: Forecast,
    summary: aggregation.SummaryStats,
    prob_beat: float | None,
) -> None:
    fc.expected_value = Decimal(str(summary.expected_value))
    fc.median_value = Decimal(str(summary.median_value))
    fc.p5_value = Decimal(str(summary.p5))
    fc.p10_value = Decimal(str(summary.p10))
    fc.p25_value = Decimal(str(summary.p25))
    fc.p75_value = Decimal(str(summary.p75))
    fc.p90_value = Decimal(str(summary.p90))
    fc.p95_value = Decimal(str(summary.p95))
    fc.probability_of_loss = Decimal(str(round(summary.probability_of_loss, 6)))
    fc.annualized_volatility = Decimal(str(summary.annualized_volatility))
    fc.expected_return = Decimal(str(summary.expected_return))
    fc.probability_beat_benchmark = (
        Decimal(str(round(prob_beat, 6))) if prob_beat is not None else None
    )


def _persist_paths(
    db: Session,
    forecast_id: uuid.UUID,
    sample_paths: np.ndarray,
    labels: list[str | None],
) -> None:
    if sample_paths.size == 0:
        return
    payload = [
        {
            "forecast_id": forecast_id,
            "path_index": i,
            "rank_label": labels[i],
            "values": [float(v) for v in sample_paths[i]],
        }
        for i in range(sample_paths.shape[0])
    ]
    db.execute(ForecastPath.__table__.insert(), payload)


def _persist_histogram(
    db: Session, forecast_id: uuid.UUID, bins: list[aggregation.HistogramBin]
) -> None:
    if not bins:
        return
    payload = [
        {
            "forecast_id": forecast_id,
            "bin_index": b.index,
            "bin_lower": Decimal(str(b.lower)),
            "bin_upper": Decimal(str(b.upper)),
            "count": b.count,
        }
        for b in bins
    ]
    db.execute(ForecastDistributionBin.__table__.insert(), payload)


def _utc_now(db: Session) -> datetime:
    """Wall-clock timestamp via the DB so timezone semantics match `created_at`."""
    val = db.scalar(select(func.now()))
    if isinstance(val, datetime):
        return val
    return datetime.now(tz=UTC)
