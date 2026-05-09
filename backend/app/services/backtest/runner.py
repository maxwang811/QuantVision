"""Runner: validation, persistence, orchestration.

The only layer that touches the DB. The engine is pure; the runner wraps it
in a transaction lifecycle, persists trades and daily portfolio values, and
records the final result on the `backtests` row.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import ValidationError
from app.core.time import trading_days
from app.models.asset import Asset
from app.models.backtest import Backtest
from app.models.portfolio_value import PortfolioValue
from app.models.price import PriceHistory
from app.models.trade import Trade
from app.schemas.backtest import BacktestCreate
from app.schemas.ml import ModelRunCreate
from app.services.backtest import engine, metrics
from app.services.backtest.context import PriceBar
from app.services.backtest.strategies import build_strategy
from app.services.data.price_repo import (
    earliest_price_date,
    get_prices,
    latest_price_date,
)
from app.services.ml.runner import (
    get_model_run_or_404,
    load_prediction_score_map,
    run_model_training,
)

log = logging.getLogger(__name__)

PRE_BUFFER_DAYS = 14


def run_backtest(db: Session, req: BacktestCreate) -> Backtest:
    """Validate, run, persist. Always returns a Backtest row (status reflects outcome)."""
    asset_map = _validate(db, req)
    # Drop the benchmark from the trading universe; metrics load it separately.
    trading_assets = {t: asset_map[t] for t in req.tickers}
    target_weights = dict(zip(req.tickers, req.weights, strict=True))
    strategy_params = _normalize_strategy_params(req)
    model_prediction_scores: dict[date, dict[str, float]] | None = None
    if req.strategy == "ml_ranking":
        model_prediction_scores = _prepare_ml_model_run(db, req, strategy_params)

    prices_master = _load_prices(
        db,
        trading_assets,
        req.start_date - _strategy_prebuffer(req.strategy, strategy_params),
        req.end_date,
    )

    backtest = Backtest(
        id=uuid.uuid4(),
        name=req.name,
        strategy=req.strategy,
        params=_backtest_params(target_weights, strategy_params),
        initial_cash=Decimal(str(req.initial_cash)),
        start_date=req.start_date,
        end_date=req.end_date,
        benchmark_ticker=req.benchmark_ticker,
        transaction_cost_bps=req.transaction_cost_bps,
        status="running",
    )
    db.add(backtest)
    db.commit()

    try:
        strategy_kwargs = _strategy_kwargs(
            req.strategy,
            target_weights,
            strategy_params,
            model_prediction_scores,
        )
        strategy = build_strategy(req.strategy, strategy_kwargs)

        result = engine.run(
            start_date=req.start_date,
            end_date=req.end_date,
            prices_master=prices_master,
            strategy=strategy,
            initial_cash=req.initial_cash,
            transaction_cost_bps=req.transaction_cost_bps,
        )

        _persist_trades(db, backtest.id, result.fills, trading_assets)
        _persist_portfolio_values(db, backtest.id, result.daily_values)

        final_value = result.daily_values[-1].total_value
        total_return = (final_value - req.initial_cash) / req.initial_cash
        backtest.final_value = Decimal(str(final_value))
        backtest.total_return = Decimal(str(total_return))

        _compute_and_persist_metrics(
            db,
            backtest,
            daily_total_values=[dv.total_value for dv in result.daily_values],
            daily_dates=[dv.date for dv in result.daily_values],
        )

        backtest.status = "completed"
        backtest.completed_at = _utc_now(db)
    except Exception as e:
        log.exception("backtest %s failed", backtest.id)
        backtest.status = "failed"
        backtest.error_message = str(e)[:1000]
    finally:
        db.commit()
        db.refresh(backtest)

    return backtest


def compute_metrics_for_backtest(db: Session, backtest: Backtest) -> None:
    """Re-derive metrics from persisted portfolio_values + benchmark prices.

    Used by the recompute endpoint. Mutates the passed Backtest in place; the
    caller is responsible for committing.
    """
    rows = list(
        db.scalars(
            select(PortfolioValue)
            .where(PortfolioValue.backtest_id == backtest.id)
            .order_by(PortfolioValue.date)
        )
    )
    if not rows:
        raise ValidationError(
            f"backtest {backtest.id} has no portfolio_values to recompute from",
            code="no_portfolio_values",
        )
    daily_total_values = [float(r.total_value) for r in rows]
    daily_dates = [r.date for r in rows]
    _compute_and_persist_metrics(
        db, backtest, daily_total_values=daily_total_values, daily_dates=daily_dates
    )


def _compute_and_persist_metrics(
    db: Session,
    backtest: Backtest,
    *,
    daily_total_values: list[float],
    daily_dates: list[date],
) -> None:
    """Compute core + (optional) benchmark metrics and write them to the row."""
    settings = get_settings()
    rf = settings.risk_free_rate

    core = metrics.core_metrics(
        daily_total_values=daily_total_values,
        initial_cash=float(backtest.initial_cash),
        period_start=backtest.start_date,
        period_end=backtest.end_date,
        risk_free_rate=rf,
    )
    backtest.total_return = Decimal(str(core.total_return))
    backtest.annualized_return = Decimal(str(core.annualized_return))
    backtest.volatility = Decimal(str(core.volatility))
    backtest.sharpe_ratio = Decimal(str(core.sharpe_ratio))
    backtest.max_drawdown = Decimal(str(core.max_drawdown))

    if backtest.benchmark_ticker:
        bench_rows = get_prices(
            db, backtest.benchmark_ticker, backtest.start_date, backtest.end_date
        )
        if not bench_rows:
            # Validation should have caught this, but if recompute runs after
            # benchmark prices were deleted we just clear the benchmark fields.
            log.warning(
                "benchmark %s has no prices in [%s, %s]; clearing benchmark metrics",
                backtest.benchmark_ticker,
                backtest.start_date,
                backtest.end_date,
            )
            _clear_benchmark_metrics(backtest)
            return

        bench_pairs = [(r.date, float(r.adj_close)) for r in bench_rows]
        bench_series = metrics.build_benchmark_series(
            benchmark_prices=bench_pairs,
            portfolio_dates=daily_dates,
            initial_cash=float(backtest.initial_cash),
        )
        bench = metrics.benchmark_metrics(
            portfolio_values=daily_total_values,
            benchmark_values=bench_series,
            period_start=backtest.start_date,
            period_end=backtest.end_date,
            risk_free_rate=rf,
        )
        backtest.benchmark_total_return = Decimal(str(bench.benchmark_total_return))
        backtest.benchmark_annualized_return = Decimal(
            str(bench.benchmark_annualized_return)
        )
        backtest.alpha = Decimal(str(bench.alpha))
        backtest.beta = Decimal(str(bench.beta))
        backtest.information_ratio = Decimal(str(bench.information_ratio))
        backtest.tracking_error = Decimal(str(bench.tracking_error))
    else:
        _clear_benchmark_metrics(backtest)


def _clear_benchmark_metrics(backtest: Backtest) -> None:
    backtest.benchmark_total_return = None
    backtest.benchmark_annualized_return = None
    backtest.alpha = None
    backtest.beta = None
    backtest.information_ratio = None
    backtest.tracking_error = None


def _normalize_strategy_params(req: BacktestCreate) -> dict[str, Any]:
    raw = dict(req.strategy_params or {})
    if req.strategy in {"buy_and_hold", "monthly_rebalance"}:
        return raw

    top_n = int(raw.get("top_n", 5))
    if top_n < 1:
        raise ValidationError("top_n must be at least 1", code="invalid_strategy_params")
    top_n = min(top_n, len(req.tickers))

    frequency = str(raw.get("rebalance_frequency", "monthly"))
    if frequency != "monthly":
        raise ValidationError(
            "only monthly rebalance_frequency is supported",
            code="invalid_strategy_params",
        )

    out: dict[str, Any] = {
        "top_n": top_n,
        "rebalance_frequency": frequency,
    }
    if req.strategy == "momentum":
        lookback_days = int(raw.get("lookback_days", raw.get("momentum_lookback_days", 63)))
        if lookback_days < 5 or lookback_days > 504:
            raise ValidationError(
                "momentum lookback_days must be between 5 and 504",
                code="invalid_strategy_params",
            )
        out["lookback_days"] = lookback_days
        return out

    label_horizon_days = int(raw.get("label_horizon_days", 20))
    training_lookback_days = int(raw.get("training_lookback_days", 756))
    selected_model = str(raw.get("selected_model", "xgboost"))
    if selected_model not in {"logistic_regression", "xgboost"}:
        raise ValidationError(
            f"unknown selected_model: {selected_model}",
            code="invalid_strategy_params",
        )
    if label_horizon_days < 5 or label_horizon_days > 126:
        raise ValidationError(
            "label_horizon_days must be between 5 and 126",
            code="invalid_strategy_params",
        )
    if training_lookback_days < 126 or training_lookback_days > 5040:
        raise ValidationError(
            "training_lookback_days must be between 126 and 5040",
            code="invalid_strategy_params",
        )

    out.update(
        {
            "label_horizon_days": label_horizon_days,
            "training_lookback_days": training_lookback_days,
            "selected_model": selected_model,
            "random_seed": int(raw.get("random_seed", 7)),
        }
    )
    if raw.get("model_run_id"):
        out["model_run_id"] = str(raw["model_run_id"])
    return out


def _backtest_params(
    target_weights: dict[str, float], strategy_params: dict[str, Any]
) -> dict[str, Any]:
    params: dict[str, Any] = {"target_weights": target_weights}
    if strategy_params:
        params["strategy_params"] = strategy_params
    return params


def _prepare_ml_model_run(
    db: Session,
    req: BacktestCreate,
    strategy_params: dict[str, Any],
) -> dict[date, dict[str, float]]:
    selected_model = strategy_params["selected_model"]
    model_run_id = strategy_params.get("model_run_id")
    if model_run_id:
        try:
            run_id = uuid.UUID(str(model_run_id))
        except ValueError as e:
            raise ValidationError(
                f"invalid model_run_id: {model_run_id}",
                code="invalid_strategy_params",
            ) from e
        model_run = get_model_run_or_404(db, run_id)
        if model_run.status != "completed":
            raise ValidationError(
                f"model run {run_id} is not completed (status={model_run.status})",
                code="model_run_not_completed",
            )
    else:
        model_req = ModelRunCreate(
            name=f"{req.name or 'Backtest'} ML ranking",
            tickers=req.tickers,
            benchmark_ticker=req.benchmark_ticker or "SPY",
            start_date=req.start_date,
            end_date=req.end_date,
            label_horizon_days=strategy_params["label_horizon_days"],
            training_lookback_days=strategy_params["training_lookback_days"],
            selected_model=selected_model,
            random_seed=strategy_params["random_seed"],
        )
        model_run = run_model_training(db, model_req)
        if model_run.status != "completed":
            raise ValidationError(
                f"auto-created model run failed: {model_run.error_message}",
                code="model_run_failed",
            )

    strategy_params["model_run_id"] = str(model_run.id)
    strategy_params["benchmark_ticker"] = model_run.benchmark_ticker
    scores = load_prediction_score_map(
        db, model_run.id, selected_model, req.start_date, req.end_date
    )
    if not scores:
        raise ValidationError(
            f"model run {model_run.id} has no {selected_model} predictions in the backtest window",
            code="model_predictions_unavailable",
        )
    return scores


def _strategy_prebuffer(strategy: str, strategy_params: dict[str, Any]) -> timedelta:
    if strategy == "momentum":
        lookback = int(strategy_params.get("lookback_days", 63))
        return timedelta(days=int(lookback * 365 / 252) + 30)
    return timedelta(days=PRE_BUFFER_DAYS)


def _strategy_kwargs(
    strategy: str,
    target_weights: dict[str, float],
    strategy_params: dict[str, Any],
    model_prediction_scores: dict[date, dict[str, float]] | None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"target_weights": target_weights}
    if strategy == "momentum":
        kwargs.update(
            {
                "top_n": strategy_params["top_n"],
                "lookback_days": strategy_params["lookback_days"],
                "rebalance_frequency": strategy_params["rebalance_frequency"],
            }
        )
    elif strategy == "ml_ranking":
        kwargs.update(
            {
                "prediction_scores": model_prediction_scores or {},
                "top_n": strategy_params["top_n"],
                "rebalance_frequency": strategy_params["rebalance_frequency"],
            }
        )
    return kwargs


def _validate(db: Session, req: BacktestCreate) -> dict[str, Asset]:
    """Returns ticker → Asset map for the validated input."""
    tickers_to_check = list(req.tickers)
    if req.benchmark_ticker and req.benchmark_ticker not in tickers_to_check:
        tickers_to_check.append(req.benchmark_ticker)

    rows = list(
        db.scalars(select(Asset).where(Asset.ticker.in_(tickers_to_check)))
    )
    found = {a.ticker: a for a in rows}
    missing = [t for t in req.tickers if t not in found]
    if missing:
        raise ValidationError(
            f"unknown tickers: {', '.join(missing)}", code="unknown_tickers"
        )

    insufficient: list[str] = []
    for ticker in req.tickers:
        asset = found[ticker]
        earliest = earliest_price_date(db, asset.id)
        latest = latest_price_date(db, asset.id)
        if (
            earliest is None
            or latest is None
            or earliest > req.start_date
            or latest < req.end_date
        ):
            insufficient.append(ticker)
    if insufficient:
        raise ValidationError(
            f"insufficient price coverage for: {', '.join(insufficient)}",
            code="insufficient_coverage",
        )

    if req.benchmark_ticker:
        bench_asset = found.get(req.benchmark_ticker)
        bench_earliest = (
            earliest_price_date(db, bench_asset.id) if bench_asset else None
        )
        bench_latest = (
            latest_price_date(db, bench_asset.id) if bench_asset else None
        )
        if (
            bench_asset is None
            or bench_earliest is None
            or bench_latest is None
            or bench_earliest > req.start_date
            or bench_latest < req.end_date
        ):
            raise ValidationError(
                f"insufficient price coverage for benchmark: {req.benchmark_ticker}",
                code="insufficient_benchmark_coverage",
            )

    if len(trading_days(req.start_date, req.end_date)) < 2:
        raise ValidationError(
            "backtest window must span at least 2 trading days",
            code="window_too_short",
        )

    return found


def _load_prices(
    db: Session,
    asset_map: dict[str, Asset],
    fetch_start: date,
    fetch_end: date,
) -> dict[str, list[PriceBar]]:
    """Pull adj_close series for each ticker, including pre-buffer for forward-fill.

    Excludes the benchmark ticker from the price master so the engine doesn't
    treat it as a tradable asset; benchmark prices are loaded separately by the
    metrics step.
    """
    asset_ids = [a.id for a in asset_map.values()]
    rows = list(
        db.scalars(
            select(PriceHistory)
            .where(PriceHistory.asset_id.in_(asset_ids))
            .where(PriceHistory.date >= fetch_start)
            .where(PriceHistory.date <= fetch_end)
            .order_by(PriceHistory.date)
        )
    )
    id_to_ticker = {a.id: t for t, a in asset_map.items()}
    out: dict[str, list[PriceBar]] = {t: [] for t in asset_map}
    for r in rows:
        out[id_to_ticker[r.asset_id]].append(PriceBar(r.date, float(r.adj_close)))
    return out


def _persist_trades(
    db: Session,
    backtest_id: uuid.UUID,
    fills: list,
    asset_map: dict[str, Asset],
) -> None:
    if not fills:
        return
    payload = [
        {
            "id": uuid.uuid4(),
            "backtest_id": backtest_id,
            "asset_id": asset_map[f.ticker].id,
            "date": f.date,
            "side": f.side,
            "quantity": Decimal(str(f.quantity)),
            "price": Decimal(str(f.price)),
            "transaction_cost": Decimal(str(f.transaction_cost)),
            "notional": Decimal(str(f.notional)),
        }
        for f in fills
    ]
    db.execute(Trade.__table__.insert(), payload)


def _persist_portfolio_values(
    db: Session, backtest_id: uuid.UUID, daily_values: list
) -> None:
    if not daily_values:
        return
    payload = [
        {
            "backtest_id": backtest_id,
            "date": dv.date,
            "cash": Decimal(str(dv.cash)),
            "holdings_value": Decimal(str(dv.holdings_value)),
            "total_value": Decimal(str(dv.total_value)),
        }
        for dv in daily_values
    ]
    db.execute(PortfolioValue.__table__.insert(), payload)


def _utc_now(db: Session):
    """Wall-clock timestamp via the DB so timezone semantics match `created_at`."""
    return db.scalar(select(func.now()))
