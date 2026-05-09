"""ML drift predictor: Ridge regression on rolling features.

For each asset, build features from the rolling history (mean/std/momentum/
drawdown over multiple windows), train a Ridge regressor against the forward
252-day mean log-return, and predict on the most-recent feature row.

The output is a vector of *daily* drift estimates ready to feed into
`engine.simulate_monte_carlo(..., drift_override=...)`. We shrink the
prediction 50% toward the historical mean to dampen overconfidence on the
small effective sample size (~5 non-overlapping forward windows in 5 years).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

_FEATURE_WINDOWS = (21, 63, 252)
_FORWARD_WINDOW = 252
_TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class MLDriftResult:
    """Predicted drift output, with the historical baseline preserved for inspection."""

    mu_hist: np.ndarray  # historical sample drift, daily
    mu_pred: np.ndarray  # raw model prediction, daily
    mu_final: np.ndarray  # 50/50 shrinkage toward mu_hist, daily


def _build_features(asset_log_returns: np.ndarray) -> np.ndarray:
    """Build a (T, F) feature matrix from a (T,) per-asset log-return series.

    Features at row t reference data through index t (inclusive) ONLY — no
    look-ahead.
    """
    t = asset_log_returns.shape[0]
    cumsum = np.concatenate([[0.0], np.cumsum(asset_log_returns)])
    cumsum_sq = np.concatenate([[0.0], np.cumsum(asset_log_returns**2)])

    feats: list[np.ndarray] = []
    for w in _FEATURE_WINDOWS:
        rolling_mean = np.full(t, np.nan)
        rolling_std = np.full(t, np.nan)
        rolling_sum = np.full(t, np.nan)
        if t >= w:
            window_sum = cumsum[w:] - cumsum[:-w]
            window_sum_sq = cumsum_sq[w:] - cumsum_sq[:-w]
            mean = window_sum / w
            var = window_sum_sq / w - mean**2
            var = np.clip(var, 0.0, None)
            rolling_mean[w - 1 :] = mean
            rolling_std[w - 1 :] = np.sqrt(var)
            rolling_sum[w - 1 :] = window_sum
        feats.append(rolling_mean)
        feats.append(rolling_std)
        feats.append(rolling_sum)

    # Drawdown over 252-day window: (current_cum - max_cum_in_window) / max(1e-9).
    drawdown = np.full(t, np.nan)
    if t >= 252:
        # Use simple loop (vectorising rolling-max requires numpy stride tricks
        # that hurt readability for a 252-wide window).
        for i in range(251, t):
            window = cumsum[i + 1 - 251 : i + 2]  # cumsum at end of each day in window
            drawdown[i] = window[-1] - window.max()
    feats.append(drawdown)

    return np.column_stack(feats)


def _build_targets(asset_log_returns: np.ndarray) -> np.ndarray:
    """Per-row forward 252-day mean log-return target.

    target[t] = mean(returns[t+1 .. t+252]). Returns NaN for the last 252 rows
    where the forward window runs off the end.
    """
    t = asset_log_returns.shape[0]
    targets = np.full(t, np.nan)
    if t > _FORWARD_WINDOW:
        cumsum = np.concatenate([[0.0], np.cumsum(asset_log_returns)])
        # mean of returns[t+1 .. t+252] = (cumsum[t+253] - cumsum[t+1]) / 252
        for i in range(t - _FORWARD_WINDOW):
            targets[i] = (cumsum[i + 1 + _FORWARD_WINDOW] - cumsum[i + 1]) / _FORWARD_WINDOW
    return targets


def _predict_one_asset(asset_log_returns: np.ndarray) -> tuple[float, float]:
    """Return (mu_hist_daily, mu_pred_daily) for a single asset.

    Falls back to the historical mean when the asset has too little history
    for a non-trivial training set, or when feature/target rows are all NaN.
    """
    mu_hist = float(asset_log_returns.mean())
    if asset_log_returns.shape[0] < _FORWARD_WINDOW + max(_FEATURE_WINDOWS) + 30:
        return mu_hist, mu_hist

    features = _build_features(asset_log_returns)
    targets = _build_targets(asset_log_returns)

    # Training rows: where neither features nor targets contain NaN.
    feature_complete = ~np.isnan(features).any(axis=1)
    target_complete = ~np.isnan(targets)
    train_mask = feature_complete & target_complete
    if train_mask.sum() < 30:
        return mu_hist, mu_hist

    x_train = features[train_mask]
    y_train = targets[train_mask]
    if not np.all(np.isfinite(x_train)) or not np.all(np.isfinite(y_train)):
        return mu_hist, mu_hist

    pipeline = Pipeline(
        [("scaler", StandardScaler()), ("ridge", Ridge(alpha=1.0))]
    )
    pipeline.fit(x_train, y_train)

    # Predict on the most recent fully-observed feature row.
    last_complete_indices = np.flatnonzero(feature_complete)
    if last_complete_indices.size == 0:
        return mu_hist, mu_hist
    last_idx = last_complete_indices[-1]
    x_predict = features[last_idx : last_idx + 1]
    mu_pred = float(pipeline.predict(x_predict)[0])
    if not np.isfinite(mu_pred):
        return mu_hist, mu_hist
    return mu_hist, mu_pred


def predict_drift(historical_log_returns: np.ndarray, shrinkage: float = 0.5) -> MLDriftResult:
    """Predict per-asset daily drift via Ridge on rolling features.

    `historical_log_returns` shape: (T, A). Output `mu_final` is a length-A
    array suitable for `engine.simulate_monte_carlo(drift_override=...)`.
    `shrinkage=0.5` mixes mu_pred and mu_hist 50/50; pass 0.0 for raw
    historical, 1.0 for raw prediction.
    """
    if historical_log_returns.ndim != 2:
        raise ValueError("historical_log_returns must be 2D")
    if not 0.0 <= shrinkage <= 1.0:
        raise ValueError("shrinkage must be in [0, 1]")

    n_assets = historical_log_returns.shape[1]
    mu_hist = np.zeros(n_assets)
    mu_pred = np.zeros(n_assets)
    for j in range(n_assets):
        h, p = _predict_one_asset(historical_log_returns[:, j])
        mu_hist[j] = h
        mu_pred[j] = p

    mu_final = shrinkage * mu_pred + (1.0 - shrinkage) * mu_hist
    return MLDriftResult(mu_hist=mu_hist, mu_pred=mu_pred, mu_final=mu_final)
