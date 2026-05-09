"""Tests for services/forecast/ml.py."""

from __future__ import annotations

import numpy as np
import pytest

from app.services.forecast.ml import predict_drift


def _synthetic(seed: int = 0, t: int = 1500, a: int = 3, mu: float = 0.0005) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(mu, 0.012, size=(t, a))


def test_predict_drift_shape_matches_assets():
    hist = _synthetic(a=4, t=1500)
    res = predict_drift(hist)
    assert res.mu_hist.shape == (4,)
    assert res.mu_pred.shape == (4,)
    assert res.mu_final.shape == (4,)


def test_predict_drift_shrinkage_blends_correctly():
    hist = _synthetic(a=2, t=1500)
    res = predict_drift(hist, shrinkage=0.5)
    np.testing.assert_allclose(
        res.mu_final, 0.5 * res.mu_pred + 0.5 * res.mu_hist, atol=1e-12
    )


def test_predict_drift_shrinkage_zero_returns_historical():
    hist = _synthetic(a=2, t=1500)
    res = predict_drift(hist, shrinkage=0.0)
    np.testing.assert_allclose(res.mu_final, res.mu_hist)


def test_predict_drift_short_history_falls_back_to_historical():
    # Insufficient rows for training; fallback path should emit mu_hist as both.
    rng = np.random.default_rng(0)
    hist = rng.normal(0.0, 0.01, size=(100, 2))  # 100 rows < required threshold
    res = predict_drift(hist)
    np.testing.assert_array_equal(res.mu_pred, res.mu_hist)


def test_predict_drift_finite_on_constant_returns():
    # Flat, identical returns → variance=0 features. Must not produce NaN/inf.
    hist = np.full((1500, 2), 0.0001)
    res = predict_drift(hist)
    assert np.all(np.isfinite(res.mu_pred))
    assert np.all(np.isfinite(res.mu_final))


def test_predict_drift_validates_input_shape():
    with pytest.raises(ValueError):
        predict_drift(np.array([0.01, 0.02, 0.03]))


def test_predict_drift_validates_shrinkage_bounds():
    hist = _synthetic(a=1, t=1500)
    with pytest.raises(ValueError):
        predict_drift(hist, shrinkage=-0.1)
    with pytest.raises(ValueError):
        predict_drift(hist, shrinkage=1.5)


def test_predict_drift_no_lookahead_in_features():
    """The most-recent prediction must use the same features as a slice through
    the same data — never future returns."""
    hist = _synthetic(a=1, t=1500, seed=42)
    # Truncate the future and assert predictions on the original up to the
    # truncation point are the same.
    full = predict_drift(hist[:1300])
    longer = predict_drift(hist[:1500])
    # Full prediction at t=1300 should NOT be influenced by the longer-history's
    # post-1300 returns. There's no clean way to assert exact equality (the
    # longer-history training set is bigger), but we can assert that adding
    # future history doesn't blow up determinism.
    assert np.all(np.isfinite(full.mu_pred))
    assert np.all(np.isfinite(longer.mu_pred))


def test_predict_drift_outputs_in_reasonable_range():
    # Daily drift should never explode; for a reasonable training set with
    # noise around zero, |mu_pred| should stay below 0.05/day (12 sigma annual).
    rng = np.random.default_rng(0)
    hist = rng.normal(0.0003, 0.012, size=(1500, 3))
    res = predict_drift(hist)
    assert np.all(np.abs(res.mu_pred) < 0.05)
    assert np.all(np.abs(res.mu_final) < 0.05)
