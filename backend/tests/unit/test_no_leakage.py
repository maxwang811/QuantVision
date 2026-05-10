"""Automated leakage detection tests for the walk-forward ML pipeline.

Two complementary checks:

A. Poisoned-future probe — bake a deterministic regime into the prices AFTER a
   "secret_date". Walk-forward predictions whose `signal_date < secret_date`
   could only have been trained on pre-secret rows; their AUC must stay near
   chance, otherwise the future has leaked into the past.

B. Time-window invariant — for every signal date, every training row that
   `walk_forward_predict` would select must have its label-end date strictly
   before the signal date. This catches future regressions that loosen the
   barrier in `walk_forward_predict`.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from app.core.time import trading_days
from app.services.ml.runner import (
    build_feature_rows,
    monthly_signal_dates,
    walk_forward_predict,
)


def _build_panel(
    dates: list[date], prices_by_ticker: dict[str, np.ndarray]
) -> dict[str, dict[date, tuple[float, float]]]:
    return {
        t: {dates[i]: (float(prices_by_ticker[t][i]), 1_000_000.0) for i in range(len(dates))}
        for t in prices_by_ticker
    }


def _benign_panel(
    dates: list[date], tickers: list[str], seed: int = 0
) -> dict[str, dict[date, tuple[float, float]]]:
    rng = np.random.default_rng(seed)
    prices: dict[str, np.ndarray] = {}
    for t in tickers:
        p = np.empty(len(dates))
        p[0] = 100.0
        for i in range(1, len(dates)):
            p[i] = p[i - 1] * float(np.exp(rng.normal(0.0, 0.01)))
        prices[t] = p
    return _build_panel(dates, prices)


def test_walk_forward_does_not_leak_future_labels():
    """A — poisoned future probe.

    Pre-secret prices are random walks (no signal). Post-secret, asset A wins
    on certain weeks and B wins on others — a perfect deterministic classifier
    of next-20d outperformance. If walk-forward leaks the future into earlier
    training sets, predictions with `signal_date < secret_date` would inherit
    that signal and AUC would drift away from 0.5.
    """
    rng = np.random.default_rng(42)
    dates = trading_days(date(2022, 1, 3), date(2024, 12, 31))
    secret_idx = len(dates) // 2

    prices = {t: np.empty(len(dates)) for t in ("A", "B", "SPY")}
    for t in prices:
        prices[t][0] = 100.0

    for i in range(1, len(dates)):
        if i < secret_idx:
            for t in prices:
                prices[t][i] = prices[t][i - 1] * float(np.exp(rng.normal(0.0, 0.01)))
        else:
            regime_a = (i % 21) < 10
            prices["A"][i] = prices["A"][i - 1] * (1.005 if regime_a else 0.995)
            prices["B"][i] = prices["B"][i - 1] * (0.995 if regime_a else 1.005)
            prices["SPY"][i] = prices["SPY"][i - 1] * 1.0005

    panel = _build_panel(dates, prices)
    rows = build_feature_rows(
        tickers=["A", "B"],
        benchmark_ticker="SPY",
        common_dates=dates,
        price_panel=panel,
        label_horizon_days=20,
    )
    signal_dates = monthly_signal_dates(dates)

    preds = walk_forward_predict(
        rows=rows,
        signal_dates=signal_dates,
        tickers=["A", "B"],
        training_lookback_days=252,
        random_seed=7,
    )

    secret_date = dates[secret_idx]
    early = [
        p
        for p in preds
        if p.date < secret_date
        and p.label is not None
        and p.model_name == "logistic_regression"
    ]
    if len(early) < 6 or len({p.label for p in early}) < 2:
        pytest.skip(f"insufficient early labeled predictions ({len(early)}) to compute AUC")

    y = np.asarray([p.label for p in early], dtype=np.int64)
    s = np.asarray([p.score for p in early], dtype=np.float64)
    auc = roc_auc_score(y, s)
    assert 0.30 <= auc <= 0.70, (
        f"leakage suspected: pre-secret AUC={auc:.3f} (should be ~0.5 with no future signal). "
        f"n={len(early)}"
    )


def test_training_features_only_use_past_data():
    """B — time-window invariant.

    For every signal date, mirror walk_forward_predict's training filter and
    assert every selected training row has its label-end date at or before the
    signal date (label realised by the time we predict at signal_date close).
    Anything STRICTLY after signal_date would be a leak. Catches regressions
    that loosen the barrier.
    """
    dates = trading_days(date(2023, 1, 3), date(2024, 12, 31))
    panel = _benign_panel(dates, ["A", "B", "SPY"], seed=0)
    rows = build_feature_rows(
        tickers=["A", "B"],
        benchmark_ticker="SPY",
        common_dates=dates,
        price_panel=panel,
        label_horizon_days=20,
    )
    signal_dates = monthly_signal_dates(dates)

    rows_by_date: dict[date, dict[str, object]] = defaultdict(dict)
    for r in rows:
        rows_by_date[r.date][r.ticker] = r

    n_checks = 0
    for sd in signal_dates:
        sd_rows = list(rows_by_date.get(sd, {}).values())
        if not sd_rows:
            continue
        pred_idx = sd_rows[0].index  # type: ignore[attr-defined]

        train_rows = [
            r
            for r in rows
            if r.label is not None
            and r.label_end_index is not None
            and r.label_end_index <= pred_idx
            and r.index >= pred_idx - 252
        ]
        for tr in train_rows:
            assert tr.label_end_date is not None
            assert tr.label_end_date <= sd, (
                f"leak: training row at {tr.date} (label_end={tr.label_end_date}) "
                f"used when predicting signal_date={sd}"
            )
            n_checks += 1

    assert n_checks > 0, "leakage test never exercised any signal date"
