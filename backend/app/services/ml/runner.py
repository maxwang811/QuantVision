"""Walk-forward ML ranking service.

This module trains no durable model artifact. Instead, each `ModelRun` persists
the out-of-sample scores that a strategy needs on each rebalance date. That is
enough to reproduce the backtest decisions while keeping Stage 6 small and
inspectable.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationError
from app.core.time import is_month_end
from app.models.asset import Asset
from app.models.model_prediction import ModelPrediction
from app.models.model_run import ModelRun
from app.models.price import PriceHistory
from app.schemas.ml import ModelRunCreate

try:  # pragma: no cover - exercised when xgboost is installed in the environment
    from xgboost import XGBClassifier
except Exception:
    XGBClassifier = None  # type: ignore[assignment]

log = logging.getLogger(__name__)

MODEL_LOGISTIC = "logistic_regression"
MODEL_XGBOOST = "xgboost"
MODEL_NAMES = (MODEL_LOGISTIC, MODEL_XGBOOST)

FEATURE_NAMES = (
    "ret_5",
    "ret_21",
    "ret_63",
    "vol_21",
    "vol_63",
    "sma_gap_20_100",
    "rsi_14",
    "volume_change_21",
    "corr_63",
    "beta_63",
)

_MAX_FEATURE_WINDOW = 100


@dataclass(frozen=True)
class FeatureRow:
    index: int
    date: date
    ticker: str
    features: tuple[float, ...]
    label: int | None
    label_end_index: int | None
    label_end_date: date | None
    forward_return: float | None
    benchmark_forward_return: float | None


@dataclass(frozen=True)
class PredictionRecord:
    date: date
    ticker: str
    model_name: str
    score: float
    rank: int
    label: int | None
    forward_return: float | None
    benchmark_forward_return: float | None


def run_model_training(db: Session, req: ModelRunCreate) -> ModelRun:
    """Validate, train walk-forward models, persist scores, and return the run."""
    asset_map = _load_assets(db, req.tickers, req.benchmark_ticker)
    all_tickers = _with_benchmark(req.tickers, req.benchmark_ticker)

    fetch_start = req.start_date - _calendar_days_for_trading_days(
        req.training_lookback_days + _MAX_FEATURE_WINDOW + req.label_horizon_days
    )
    fetch_end = req.end_date + _calendar_days_for_trading_days(req.label_horizon_days + 5)
    price_panel = _load_price_panel(
        db, [asset_map[t] for t in all_tickers], fetch_start, fetch_end
    )

    common_dates = _common_dates(price_panel, all_tickers)
    window_dates = [d for d in common_dates if req.start_date <= d <= req.end_date]
    if len(window_dates) < 2:
        raise ValidationError(
            "no overlapping prediction dates across requested tickers",
            code="insufficient_history",
        )

    rows = build_feature_rows(
        tickers=req.tickers,
        benchmark_ticker=req.benchmark_ticker,
        common_dates=common_dates,
        price_panel=price_panel,
        label_horizon_days=req.label_horizon_days,
    )
    signal_dates = monthly_signal_dates(window_dates)
    if not signal_dates:
        raise ValidationError(
            "model run window has no monthly signal dates",
            code="window_too_short",
        )

    run = ModelRun(
        id=uuid.uuid4(),
        name=req.name,
        tickers=req.tickers,
        benchmark_ticker=req.benchmark_ticker,
        start_date=req.start_date,
        end_date=req.end_date,
        label_horizon_days=req.label_horizon_days,
        training_lookback_days=req.training_lookback_days,
        selected_model=req.selected_model,
        params={
            "feature_names": list(FEATURE_NAMES),
            "models": list(MODEL_NAMES),
            "random_seed": req.random_seed,
        },
        status="running",
    )
    db.add(run)
    db.commit()

    try:
        predictions = walk_forward_predict(
            rows=rows,
            signal_dates=signal_dates,
            tickers=req.tickers,
            training_lookback_days=req.training_lookback_days,
            random_seed=req.random_seed,
        )
        if not predictions:
            raise ValidationError(
                "not enough feature-complete rows to generate predictions",
                code="insufficient_history",
            )

        _persist_predictions(db, run.id, predictions, asset_map)
        run.metrics = summarize_predictions(predictions)
        run.status = "completed"
        run.completed_at = _utc_now(db)
    except ValidationError as e:
        run.status = "failed"
        run.error_message = e.message
        db.commit()
        raise
    except Exception as e:
        log.exception("model run %s failed", run.id)
        run.status = "failed"
        run.error_message = str(e)[:1000]
    finally:
        db.commit()
        db.refresh(run)

    return run


def get_model_run_or_404(db: Session, model_run_id: uuid.UUID) -> ModelRun:
    run = db.get(ModelRun, model_run_id)
    if run is None:
        raise NotFoundError(f"model run not found: {model_run_id}")
    return run


def load_prediction_score_map(
    db: Session,
    model_run_id: uuid.UUID,
    model_name: str,
    start: date,
    end: date,
) -> dict[date, dict[str, float]]:
    rows = list(
        db.execute(
            select(ModelPrediction, Asset.ticker)
            .join(Asset, Asset.id == ModelPrediction.asset_id)
            .where(ModelPrediction.model_run_id == model_run_id)
            .where(ModelPrediction.model_name == model_name)
            .where(ModelPrediction.date >= start)
            .where(ModelPrediction.date <= end)
            .order_by(ModelPrediction.date, ModelPrediction.rank)
        )
    )
    out: dict[date, dict[str, float]] = defaultdict(dict)
    for pred, ticker in rows:
        out[pred.date][ticker] = float(pred.score)
    return dict(out)


def build_feature_rows(
    *,
    tickers: list[str],
    benchmark_ticker: str,
    common_dates: list[date],
    price_panel: dict[str, dict[date, tuple[float, float]]],
    label_horizon_days: int,
) -> list[FeatureRow]:
    """Build feature rows without lookahead.

    Feature values at index `i` only use prices/volume through `i`. Labels, when
    available, use the next trading day's close as the fill anchor and compare
    performance over the configured horizon.
    """
    prices = {
        t: np.asarray([price_panel[t][d][0] for d in common_dates], dtype=np.float64)
        for t in _with_benchmark(tickers, benchmark_ticker)
    }
    volumes = {
        t: np.asarray([price_panel[t][d][1] for d in common_dates], dtype=np.float64)
        for t in _with_benchmark(tickers, benchmark_ticker)
    }
    bench_prices = prices[benchmark_ticker]
    bench_log_returns = np.diff(np.log(bench_prices))

    rows: list[FeatureRow] = []
    for ticker in tickers:
        asset_prices = prices[ticker]
        asset_log_returns = np.diff(np.log(asset_prices))
        for i, d in enumerate(common_dates):
            feats = _features_at(
                i,
                asset_prices=asset_prices,
                asset_log_returns=asset_log_returns,
                asset_volumes=volumes[ticker],
                bench_log_returns=bench_log_returns,
            )
            if feats is None:
                continue

            label = None
            label_end_index = None
            label_end_date = None
            fwd = None
            bench_fwd = None
            fill_index = i + 1
            end_index = fill_index + label_horizon_days
            if end_index < len(common_dates):
                fwd = asset_prices[end_index] / asset_prices[fill_index] - 1.0
                bench_fwd = bench_prices[end_index] / bench_prices[fill_index] - 1.0
                label = int(fwd > bench_fwd)
                label_end_index = end_index
                label_end_date = common_dates[end_index]

            rows.append(
                FeatureRow(
                    index=i,
                    date=d,
                    ticker=ticker,
                    features=feats,
                    label=label,
                    label_end_index=label_end_index,
                    label_end_date=label_end_date,
                    forward_return=fwd,
                    benchmark_forward_return=bench_fwd,
                )
            )
    return rows


def monthly_signal_dates(dates: list[date]) -> list[date]:
    if not dates:
        return []
    signals = [dates[0]]
    signals.extend(d for d in dates[1:] if is_month_end(d, dates))
    return signals


def walk_forward_predict(
    *,
    rows: list[FeatureRow],
    signal_dates: list[date],
    tickers: list[str],
    training_lookback_days: int,
    random_seed: int,
) -> list[PredictionRecord]:
    rows_by_date: dict[date, dict[str, FeatureRow]] = defaultdict(dict)
    for row in rows:
        rows_by_date[row.date][row.ticker] = row

    predictions: list[PredictionRecord] = []
    for signal_date in signal_dates:
        pred_rows = [rows_by_date.get(signal_date, {}).get(t) for t in tickers]
        pred_rows = [r for r in pred_rows if r is not None]
        if not pred_rows:
            continue

        pred_idx = pred_rows[0].index
        train_rows = [
            row
            for row in rows
            if row.label is not None
            and row.label_end_index is not None
            and row.label_end_index <= pred_idx
            and row.index >= pred_idx - training_lookback_days
        ]

        x_pred = np.asarray([r.features for r in pred_rows], dtype=np.float64)
        for model_name in MODEL_NAMES:
            scores = _fit_predict_scores(
                model_name=model_name,
                train_rows=train_rows,
                x_pred=x_pred,
                random_seed=random_seed,
            )
            ranks = _rank_scores(pred_rows, scores)
            for row, score in zip(pred_rows, scores, strict=True):
                predictions.append(
                    PredictionRecord(
                        date=row.date,
                        ticker=row.ticker,
                        model_name=model_name,
                        score=float(np.clip(score, 0.0, 1.0)),
                        rank=ranks[row.ticker],
                        label=row.label,
                        forward_return=row.forward_return,
                        benchmark_forward_return=row.benchmark_forward_return,
                    )
                )
    return predictions


def summarize_predictions(predictions: list[PredictionRecord]) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "feature_names": list(FEATURE_NAMES),
        "n_predictions": len(predictions),
        "models": {},
    }
    for model_name in MODEL_NAMES:
        rows = [p for p in predictions if p.model_name == model_name and p.label is not None]
        y = np.asarray([p.label for p in rows], dtype=np.int64)
        scores = np.asarray([p.score for p in rows], dtype=np.float64)
        model_metrics: dict[str, Any] = {"n_labeled_predictions": len(rows)}
        if len(rows) > 0:
            model_metrics["accuracy"] = float(accuracy_score(y, scores >= 0.5))
            model_metrics["mean_score"] = float(scores.mean())
        else:
            model_metrics["accuracy"] = None
            model_metrics["mean_score"] = None
        if len(np.unique(y)) == 2:
            model_metrics["auc"] = float(roc_auc_score(y, scores))
        else:
            model_metrics["auc"] = None
        metrics["models"][model_name] = model_metrics
    return metrics


def _fit_predict_scores(
    *,
    model_name: str,
    train_rows: list[FeatureRow],
    x_pred: np.ndarray,
    random_seed: int,
) -> np.ndarray:
    if not train_rows:
        return np.full(x_pred.shape[0], 0.5, dtype=np.float64)

    x_train = np.asarray([r.features for r in train_rows], dtype=np.float64)
    y_train = np.asarray([r.label for r in train_rows], dtype=np.int64)
    if len(np.unique(y_train)) < 2:
        return np.full(x_pred.shape[0], float(y_train.mean()), dtype=np.float64)

    if model_name == MODEL_LOGISTIC:
        model = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=500,
                        class_weight="balanced",
                        random_state=random_seed,
                    ),
                ),
            ]
        )
    elif model_name == MODEL_XGBOOST:
        if XGBClassifier is not None:
            model = XGBClassifier(
                n_estimators=50,
                max_depth=3,
                learning_rate=0.05,
                subsample=0.9,
                colsample_bytree=0.9,
                eval_metric="logloss",
                random_state=random_seed,
                n_jobs=1,
            )
        else:
            model = GradientBoostingClassifier(random_state=random_seed)
    else:  # pragma: no cover - guarded by callers
        raise ValueError(f"unknown model name: {model_name}")

    model.fit(x_train, y_train)
    scores = model.predict_proba(x_pred)[:, 1]
    return np.asarray(scores, dtype=np.float64)


def _rank_scores(rows: list[FeatureRow], scores: np.ndarray) -> dict[str, int]:
    ordered = sorted(
        zip(rows, scores, strict=True),
        key=lambda rs: (-float(rs[1]), rs[0].ticker),
    )
    return {row.ticker: i + 1 for i, (row, _score) in enumerate(ordered)}


def _features_at(
    i: int,
    *,
    asset_prices: np.ndarray,
    asset_log_returns: np.ndarray,
    asset_volumes: np.ndarray,
    bench_log_returns: np.ndarray,
) -> tuple[float, ...] | None:
    if i < _MAX_FEATURE_WINDOW:
        return None

    ret_5 = _window_return(asset_prices, i, 5)
    ret_21 = _window_return(asset_prices, i, 21)
    ret_63 = _window_return(asset_prices, i, 63)
    vol_21 = _rolling_std(asset_log_returns, i, 21)
    vol_63 = _rolling_std(asset_log_returns, i, 63)
    sma_gap = _sma_gap(asset_prices, i, 20, 100)
    rsi = _rsi(asset_prices, i, 14)
    volume_change = _volume_change(asset_volumes, i, 21)
    corr, beta = _corr_beta(asset_log_returns, bench_log_returns, i, 63)

    vals = (ret_5, ret_21, ret_63, vol_21, vol_63, sma_gap, rsi, volume_change, corr, beta)
    if not np.all(np.isfinite(vals)):
        return None
    return tuple(float(v) for v in vals)


def _window_return(prices: np.ndarray, i: int, window: int) -> float:
    return float(prices[i] / prices[i - window] - 1.0)


def _rolling_std(log_returns: np.ndarray, price_index: int, window: int) -> float:
    vals = log_returns[price_index - window : price_index]
    return float(vals.std(ddof=1))


def _sma_gap(prices: np.ndarray, i: int, short: int, long: int) -> float:
    short_avg = prices[i - short + 1 : i + 1].mean()
    long_avg = prices[i - long + 1 : i + 1].mean()
    return float(short_avg / long_avg - 1.0)


def _rsi(prices: np.ndarray, i: int, window: int) -> float:
    deltas = np.diff(prices[i - window : i + 1])
    gains = np.clip(deltas, 0.0, None).mean()
    losses = np.clip(-deltas, 0.0, None).mean()
    if losses == 0.0 and gains == 0.0:
        return 50.0
    if losses == 0.0:
        return 100.0
    rs = gains / losses
    return float(100.0 - (100.0 / (1.0 + rs)))


def _volume_change(volumes: np.ndarray, i: int, window: int) -> float:
    current = volumes[i]
    baseline = volumes[i - window : i].mean()
    if baseline <= 0.0 or current <= 0.0:
        return 0.0
    return float(current / baseline - 1.0)


def _corr_beta(
    asset_log_returns: np.ndarray,
    bench_log_returns: np.ndarray,
    price_index: int,
    window: int,
) -> tuple[float, float]:
    a = asset_log_returns[price_index - window : price_index]
    b = bench_log_returns[price_index - window : price_index]
    a_std = a.std(ddof=1)
    b_std = b.std(ddof=1)
    if a_std <= 0.0 or b_std <= 0.0:
        return 0.0, 0.0
    cov = float(np.cov(a, b, ddof=1)[0, 1])
    corr = cov / (a_std * b_std)
    beta = cov / float(np.var(b, ddof=1))
    return float(np.clip(corr, -1.0, 1.0)), float(beta)


def _load_assets(db: Session, tickers: list[str], benchmark_ticker: str) -> dict[str, Asset]:
    all_tickers = _with_benchmark(tickers, benchmark_ticker)
    rows = list(db.scalars(select(Asset).where(Asset.ticker.in_(all_tickers))))
    found = {a.ticker: a for a in rows}
    missing = [t for t in all_tickers if t not in found]
    if missing:
        raise ValidationError(
            f"unknown tickers: {', '.join(missing)}", code="unknown_tickers"
        )
    return found


def _load_price_panel(
    db: Session,
    assets: list[Asset],
    start: date,
    end: date,
) -> dict[str, dict[date, tuple[float, float]]]:
    rows = list(
        db.execute(
            select(PriceHistory, Asset.ticker)
            .join(Asset, Asset.id == PriceHistory.asset_id)
            .where(PriceHistory.asset_id.in_([a.id for a in assets]))
            .where(PriceHistory.date >= start)
            .where(PriceHistory.date <= end)
            .order_by(PriceHistory.date)
        )
    )
    panel: dict[str, dict[date, tuple[float, float]]] = defaultdict(dict)
    for price, ticker in rows:
        volume = float(price.volume or 0)
        panel[ticker][price.date] = (float(price.adj_close), volume)
    for asset in assets:
        if asset.ticker not in panel:
            raise ValidationError(
                f"insufficient price coverage for: {asset.ticker}",
                code="insufficient_history",
            )
    return dict(panel)


def _common_dates(
    price_panel: dict[str, dict[date, tuple[float, float]]], tickers: list[str]
) -> list[date]:
    common = set(price_panel[tickers[0]])
    for ticker in tickers[1:]:
        common &= set(price_panel[ticker])
    dates = sorted(common)
    if len(dates) < _MAX_FEATURE_WINDOW + 2:
        raise ValidationError(
            "insufficient overlapping history for ML features",
            code="insufficient_history",
        )
    for ticker in tickers:
        if any(price_panel[ticker][d][0] <= 0 for d in dates):
            raise ValidationError(
                f"non-positive adjusted close found for: {ticker}",
                code="invalid_price_history",
            )
    return dates


def _persist_predictions(
    db: Session,
    model_run_id: uuid.UUID,
    predictions: list[PredictionRecord],
    asset_map: dict[str, Asset],
) -> None:
    payload = [
        {
            "id": uuid.uuid4(),
            "model_run_id": model_run_id,
            "asset_id": asset_map[p.ticker].id,
            "date": p.date,
            "model_name": p.model_name,
            "score": Decimal(str(round(p.score, 8))),
            "rank": p.rank,
            "label": p.label,
            "forward_return": (
                Decimal(str(round(p.forward_return, 8)))
                if p.forward_return is not None
                else None
            ),
            "benchmark_forward_return": (
                Decimal(str(round(p.benchmark_forward_return, 8)))
                if p.benchmark_forward_return is not None
                else None
            ),
        }
        for p in predictions
    ]
    db.execute(ModelPrediction.__table__.insert(), payload)


def _with_benchmark(tickers: list[str], benchmark_ticker: str) -> list[str]:
    out = list(tickers)
    if benchmark_ticker not in out:
        out.append(benchmark_ticker)
    return out


def _calendar_days_for_trading_days(n: int) -> timedelta:
    return timedelta(days=int(n * 365 / 252) + 30)


def _utc_now(db: Session) -> datetime:
    val = db.scalar(select(func.now()))
    if isinstance(val, datetime):
        return val
    return datetime.now(tz=UTC)
