"""Tests for the pure estimation helpers in services/forecast/estimation.py."""

from __future__ import annotations

import numpy as np
import pytest

from app.services.forecast.estimation import (
    compute_log_returns,
    estimate_statistics,
    psd_correct,
)


def test_log_returns_shape_and_values():
    prices = np.array([[100.0, 50.0], [110.0, 55.0], [121.0, 60.5]])
    log_rets = compute_log_returns(prices)
    assert log_rets.shape == (2, 2)
    # Both assets grew exactly 10% each step → log(1.1) ≈ 0.0953.
    np.testing.assert_allclose(log_rets, np.log(1.1), atol=1e-9)


def test_log_returns_rejects_non_positive_prices():
    with pytest.raises(ValueError):
        compute_log_returns(np.array([[1.0, 0.0], [1.0, 1.0]]))


def test_log_returns_rejects_too_few_rows():
    with pytest.raises(ValueError):
        compute_log_returns(np.array([[1.0, 1.0]]))


def test_log_returns_rejects_wrong_shape():
    with pytest.raises(ValueError):
        compute_log_returns(np.array([1.0, 2.0, 3.0]))


def test_estimate_statistics_shapes():
    rng = np.random.default_rng(0)
    log_rets = rng.normal(0, 0.01, size=(500, 3))
    stats = estimate_statistics(log_rets)
    assert stats.mu.shape == (3,)
    assert stats.sigma.shape == (3,)
    assert stats.cov.shape == (3, 3)
    assert stats.corr.shape == (3, 3)
    assert stats.cholesky.shape == (3, 3)


def test_estimate_statistics_recovers_drift_and_vol():
    rng = np.random.default_rng(42)
    n = 50_000
    true_mu = np.array([0.0005, -0.0002, 0.0008])
    true_sigma = np.array([0.012, 0.008, 0.020])
    eps = rng.standard_normal((n, 3)) * true_sigma
    log_rets = true_mu + eps
    stats = estimate_statistics(log_rets)
    np.testing.assert_allclose(stats.mu, true_mu, atol=2e-4)
    np.testing.assert_allclose(stats.sigma, true_sigma, rtol=0.02)


def test_estimate_statistics_correlation_diagonal_is_one():
    rng = np.random.default_rng(7)
    log_rets = rng.normal(0, 0.01, size=(1000, 4))
    stats = estimate_statistics(log_rets)
    np.testing.assert_allclose(np.diag(stats.corr), 1.0, atol=1e-12)


def test_estimate_statistics_handles_perfectly_correlated_assets():
    # Two identical series → singular covariance. PSD correction should keep
    # Cholesky stable.
    rng = np.random.default_rng(0)
    base = rng.normal(0, 0.01, size=(500,))
    log_rets = np.column_stack([base, base])
    stats = estimate_statistics(log_rets)
    # Cholesky factor should not contain NaN/inf.
    assert np.all(np.isfinite(stats.cholesky))


def test_psd_correct_makes_indefinite_matrix_psd():
    indefinite = np.array([[1.0, 2.0], [2.0, 1.0]])  # eigenvalues 3, -1
    corrected = psd_correct(indefinite)
    eigvals = np.linalg.eigvalsh(corrected)
    assert np.all(eigvals > 0)


def test_psd_correct_preserves_already_psd_matrix():
    psd = np.array([[2.0, 0.5], [0.5, 1.0]])
    corrected = psd_correct(psd)
    np.testing.assert_allclose(corrected, psd, atol=1e-9)


def test_estimate_statistics_single_asset():
    rng = np.random.default_rng(0)
    log_rets = rng.normal(0, 0.01, size=(500, 1))
    stats = estimate_statistics(log_rets)
    assert stats.mu.shape == (1,)
    assert stats.cov.shape == (1, 1)
    assert stats.cholesky.shape == (1, 1)
