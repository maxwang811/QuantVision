from __future__ import annotations

import copy
import itertools
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.models.backtest import Backtest
from app.models.experiment_sweep import ExperimentSweep
from app.models.experiment_sweep_run import ExperimentSweepRun
from app.models.forecast import Forecast
from app.models.forecast_distribution_bin import ForecastDistributionBin
from app.models.model_run import ModelRun
from app.models.portfolio_value import PortfolioValue
from app.schemas.backtest import BacktestCreate
from app.schemas.experiments import (
    BacktestComparisonItem,
    ExperimentCompareOut,
    ExperimentCompareRequest,
    ExperimentSummary,
    ExperimentSweepCreate,
    ForecastComparisonItem,
    ForecastDistributionCompareBin,
    NormalizedCurvePoint,
)
from app.schemas.forecast import ForecastCreate
from app.services.backtest.runner import run_backtest
from app.services.forecast.runner import run_forecast

MAX_COMPARE_PER_KIND = 8
MAX_SWEEP_RUNS = 50

BACKTEST_SWEEP_FIELDS = {
    "strategy",
    "transaction_cost_bps",
    "start_date",
    "end_date",
    "strategy_params.top_n",
    "strategy_params.lookback_days",
    "strategy_params.selected_model",
    "strategy_params.training_lookback_days",
    "strategy_params.label_horizon_days",
}

FORECAST_SWEEP_FIELDS = {
    "method",
    "horizon_months",
    "n_simulations",
    "lookback_days",
    "random_seed",
    "benchmark_ticker",
}


def list_experiment_summaries(
    db: Session,
    *,
    kind: str | None,
    status: str | None,
    q: str | None,
    limit: int,
    offset: int,
) -> tuple[list[ExperimentSummary], int]:
    items: list[ExperimentSummary] = []
    kinds = {kind} if kind else {"backtest", "forecast", "model_run", "sweep"}

    if "backtest" in kinds:
        items.extend(_backtest_summary(row) for row in db.scalars(select(Backtest)))
    if "forecast" in kinds:
        items.extend(_forecast_summary(row) for row in db.scalars(select(Forecast)))
    if "model_run" in kinds:
        items.extend(_model_run_summary(row) for row in db.scalars(select(ModelRun)))
    if "sweep" in kinds:
        items.extend(_sweep_summary(row) for row in db.scalars(select(ExperimentSweep)))

    if status:
        items = [item for item in items if item.status == status]
    if q:
        needle = q.strip().lower()
        if needle:
            items = [item for item in items if _summary_matches(item, needle)]

    items.sort(key=lambda item: item.created_at, reverse=True)
    total = len(items)
    return items[offset : offset + limit], total


def compare_experiments(db: Session, req: ExperimentCompareRequest) -> ExperimentCompareOut:
    if len(req.backtest_ids) > MAX_COMPARE_PER_KIND:
        raise ValidationError(
            f"at most {MAX_COMPARE_PER_KIND} backtests can be compared",
            code="compare_too_many",
        )
    if len(req.forecast_ids) > MAX_COMPARE_PER_KIND:
        raise ValidationError(
            f"at most {MAX_COMPARE_PER_KIND} forecasts can be compared",
            code="compare_too_many",
        )

    backtests = [_build_backtest_comparison(db, backtest_id) for backtest_id in req.backtest_ids]
    forecasts = [_build_forecast_comparison(db, forecast_id) for forecast_id in req.forecast_ids]
    return ExperimentCompareOut(backtests=backtests, forecasts=forecasts)


def create_and_run_sweep(db: Session, req: ExperimentSweepCreate) -> ExperimentSweep:
    expanded = expand_sweep_requests(req.kind, req.base_request, req.sweep_parameters)
    if len(expanded) > min(req.max_runs, MAX_SWEEP_RUNS):
        raise ValidationError(
            f"sweep expands to {len(expanded)} runs; max is {min(req.max_runs, MAX_SWEEP_RUNS)}",
            code="sweep_too_large",
        )

    sweep = ExperimentSweep(
        id=uuid.uuid4(),
        name=req.name,
        kind=req.kind,
        status="queued",
        base_request=req.base_request,
        sweep_parameters=req.sweep_parameters,
        total_runs=len(expanded),
        completed_runs=0,
        failed_runs=0,
    )
    db.add(sweep)
    db.commit()
    db.refresh(sweep)

    sweep.status = "running"
    db.commit()

    completed = 0
    failed = 0
    for index, params in enumerate(expanded):
        run = ExperimentSweepRun(
            id=uuid.uuid4(),
            sweep_id=sweep.id,
            run_index=index,
            kind=req.kind,
            params=params,
            status="running",
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        try:
            if req.kind == "backtest":
                backtest_req = BacktestCreate.model_validate(params)
                backtest = run_backtest(db, backtest_req)
                run.backtest_id = backtest.id
                run.status = backtest.status
                run.error_message = backtest.error_message
            else:
                forecast_req = ForecastCreate.model_validate(params)
                forecast = run_forecast(db, forecast_req)
                run.forecast_id = forecast.id
                run.status = forecast.status
                run.error_message = forecast.error_message
        except (ValidationError, PydanticValidationError, ValueError) as exc:
            run.status = "failed"
            run.error_message = str(exc)[:1000]
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)[:1000]

        run.completed_at = _utc_now(db)
        if run.status == "completed":
            completed += 1
        else:
            failed += 1
        db.commit()

    sweep.completed_runs = completed
    sweep.failed_runs = failed
    if completed == len(expanded):
        sweep.status = "completed"
    elif failed == len(expanded):
        sweep.status = "failed"
        sweep.error_message = "all sweep runs failed"
    else:
        sweep.status = "partial"
        sweep.error_message = f"{failed} of {len(expanded)} sweep runs failed"
    sweep.completed_at = _utc_now(db)
    db.commit()
    db.refresh(sweep)
    return sweep


def expand_sweep_requests(
    kind: str,
    base_request: dict[str, Any],
    sweep_parameters: dict[str, list[Any]],
) -> list[dict[str, Any]]:
    allowed = BACKTEST_SWEEP_FIELDS if kind == "backtest" else FORECAST_SWEEP_FIELDS
    unknown = [key for key in sweep_parameters if key not in allowed]
    if unknown:
        raise ValidationError(
            f"unsupported {kind} sweep parameter(s): {', '.join(unknown)}",
            code="invalid_sweep_parameter",
        )

    keys = list(sweep_parameters.keys())
    values = [sweep_parameters[key] for key in keys]
    runs: list[dict[str, Any]] = []
    for combo in itertools.product(*values):
        payload = copy.deepcopy(base_request)
        for key, value in zip(keys, combo, strict=True):
            _set_nested(payload, key, value)
        runs.append(payload)
    return runs


def get_sweep_or_404(db: Session, sweep_id: uuid.UUID) -> ExperimentSweep:
    sweep = db.get(ExperimentSweep, sweep_id)
    if sweep is None:
        raise NotFoundError(f"experiment sweep not found: {sweep_id}")
    return sweep


def list_sweep_runs(db: Session, sweep_id: uuid.UUID) -> list[ExperimentSweepRun]:
    get_sweep_or_404(db, sweep_id)
    return list(
        db.scalars(
            select(ExperimentSweepRun)
            .where(ExperimentSweepRun.sweep_id == sweep_id)
            .order_by(ExperimentSweepRun.run_index)
        )
    )


def _backtest_summary(row: Backtest) -> ExperimentSummary:
    params = row.params or {}
    return ExperimentSummary(
        id=row.id,
        kind="backtest",
        name=row.name,
        status=row.status,
        created_at=row.created_at,
        completed_at=row.completed_at,
        label=row.strategy,
        primary_metric_label="Final value",
        primary_metric_value=_float(row.final_value),
        secondary_metric_label="Total return",
        secondary_metric_value=_float(row.total_return),
        details={
            "strategy": row.strategy,
            "start_date": row.start_date.isoformat(),
            "end_date": row.end_date.isoformat(),
            "benchmark_ticker": row.benchmark_ticker,
            "tickers": list((params.get("target_weights") or {}).keys()),
            "sharpe_ratio": _float(row.sharpe_ratio),
            "max_drawdown": _float(row.max_drawdown),
        },
    )


def _forecast_summary(row: Forecast) -> ExperimentSummary:
    params = row.params or {}
    return ExperimentSummary(
        id=row.id,
        kind="forecast",
        name=row.name,
        status=row.status,
        created_at=row.created_at,
        completed_at=row.completed_at,
        label=row.method,
        primary_metric_label="Expected value",
        primary_metric_value=_float(row.expected_value),
        secondary_metric_label="Probability of loss",
        secondary_metric_value=_float(row.probability_of_loss),
        details={
            "method": row.method,
            "horizon_months": row.horizon_months,
            "n_simulations": row.n_simulations,
            "benchmark_ticker": row.benchmark_ticker,
            "tickers": params.get("tickers"),
            "median_value": _float(row.median_value),
            "p10_value": _float(row.p10_value),
            "p90_value": _float(row.p90_value),
        },
    )


def _model_run_summary(row: ModelRun) -> ExperimentSummary:
    selected_metrics = ((row.metrics or {}).get("models") or {}).get(row.selected_model) or {}
    return ExperimentSummary(
        id=row.id,
        kind="model_run",
        name=row.name,
        status=row.status,
        created_at=row.created_at,
        completed_at=row.completed_at,
        label=row.selected_model,
        primary_metric_label="AUC",
        primary_metric_value=_float(selected_metrics.get("auc")),
        secondary_metric_label="Accuracy",
        secondary_metric_value=_float(selected_metrics.get("accuracy")),
        details={
            "selected_model": row.selected_model,
            "benchmark_ticker": row.benchmark_ticker,
            "start_date": row.start_date.isoformat(),
            "end_date": row.end_date.isoformat(),
            "tickers": row.tickers,
        },
    )


def _sweep_summary(row: ExperimentSweep) -> ExperimentSummary:
    return ExperimentSummary(
        id=row.id,
        kind="sweep",
        name=row.name,
        status=row.status,
        created_at=row.created_at,
        completed_at=row.completed_at,
        label=f"{row.kind} sweep",
        primary_metric_label="Completed runs",
        primary_metric_value=float(row.completed_runs),
        secondary_metric_label="Failed runs",
        secondary_metric_value=float(row.failed_runs),
        details={
            "kind": row.kind,
            "total_runs": row.total_runs,
            "completed_runs": row.completed_runs,
            "failed_runs": row.failed_runs,
        },
    )


def _summary_matches(item: ExperimentSummary, needle: str) -> bool:
    haystack = " ".join(
        [
            str(item.id),
            item.kind,
            item.status,
            item.name or "",
            item.label,
            str(item.details),
        ]
    ).lower()
    return needle in haystack


def _build_backtest_comparison(db: Session, backtest_id: uuid.UUID) -> BacktestComparisonItem:
    bt = db.get(Backtest, backtest_id)
    if bt is None:
        raise NotFoundError(f"backtest not found: {backtest_id}")
    if bt.status != "completed":
        raise ValidationError(
            f"backtest {backtest_id} is not completed (status={bt.status})",
            code="compare_invalid_status",
        )

    rows = list(
        db.scalars(
            select(PortfolioValue)
            .where(PortfolioValue.backtest_id == backtest_id)
            .order_by(PortfolioValue.date)
        )
    )
    normalized: list[NormalizedCurvePoint] = []
    if rows:
        base = float(rows[0].total_value)
        if base > 0:
            normalized = [
                NormalizedCurvePoint(date=row.date, value=float(row.total_value) / base * 100.0)
                for row in rows
            ]

    return BacktestComparisonItem(
        id=bt.id,
        name=bt.name,
        strategy=bt.strategy,
        status=bt.status,
        start_date=bt.start_date,
        end_date=bt.end_date,
        initial_cash=float(bt.initial_cash),
        final_value=_float(bt.final_value),
        total_return=_float(bt.total_return),
        annualized_return=_float(bt.annualized_return),
        volatility=_float(bt.volatility),
        sharpe_ratio=_float(bt.sharpe_ratio),
        max_drawdown=_float(bt.max_drawdown),
        benchmark_ticker=bt.benchmark_ticker,
        benchmark_total_return=_float(bt.benchmark_total_return),
        created_at=bt.created_at,
        normalized_curve=normalized,
    )


def _build_forecast_comparison(db: Session, forecast_id: uuid.UUID) -> ForecastComparisonItem:
    fc = db.get(Forecast, forecast_id)
    if fc is None:
        raise NotFoundError(f"forecast not found: {forecast_id}")
    if fc.status != "completed":
        raise ValidationError(
            f"forecast {forecast_id} is not completed (status={fc.status})",
            code="compare_invalid_status",
        )

    bins = list(
        db.scalars(
            select(ForecastDistributionBin)
            .where(ForecastDistributionBin.forecast_id == forecast_id)
            .order_by(ForecastDistributionBin.bin_index)
        )
    )
    return ForecastComparisonItem(
        id=fc.id,
        name=fc.name,
        method=fc.method,
        status=fc.status,
        initial_value=float(fc.initial_value),
        horizon_months=fc.horizon_months,
        n_simulations=fc.n_simulations,
        expected_value=_float(fc.expected_value),
        median_value=_float(fc.median_value),
        p10_value=_float(fc.p10_value),
        p90_value=_float(fc.p90_value),
        probability_of_loss=_float(fc.probability_of_loss),
        probability_beat_benchmark=_float(fc.probability_beat_benchmark),
        benchmark_ticker=fc.benchmark_ticker,
        created_at=fc.created_at,
        distribution_bins=[
            ForecastDistributionCompareBin(
                index=row.bin_index,
                lower=float(row.bin_lower),
                upper=float(row.bin_upper),
                count=row.count,
            )
            for row in bins
        ],
    )


def _set_nested(payload: dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    cursor = payload
    for part in parts[:-1]:
        nested = cursor.get(part)
        if nested is None:
            nested = {}
            cursor[part] = nested
        if not isinstance(nested, dict):
            raise ValidationError(
                f"cannot set nested sweep parameter {dotted_key}",
                code="invalid_sweep_parameter",
            )
        cursor = nested
    cursor[parts[-1]] = value


def _float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _utc_now(db: Session) -> datetime:
    val = db.scalar(select(func.now()))
    if isinstance(val, datetime):
        return val
    return datetime.now(tz=UTC)
