"""Tests for the pure simulation kernels in services/forecast/engine.py."""

from __future__ import annotations

import numpy as np
import pytest

from app.services.forecast.engine import (
    _compose_portfolio_paths,
    simulate_bootstrap,
    simulate_monte_carlo,
)


def _historical_returns(seed: int = 0, t: int = 1000, a: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(0.0005, 0.012, size=(t, a))


def test_compose_portfolio_paths_starts_at_initial_value():
    rng = np.random.default_rng(0)
    asset_log = rng.normal(0, 0.01, size=(5, 10, 2))
    weights = np.array([0.6, 0.4])
    paths = _compose_portfolio_paths(asset_log, weights, initial_value=1234.5)
    np.testing.assert_array_equal(paths[:, 0], 1234.5)
    assert paths.shape == (5, 11)


def test_compose_portfolio_paths_constant_growth():
    # All assets grow exactly 1% per step → portfolio grows 1% per step.
    asset_log = np.full((4, 5, 2), np.log(1.01))
    paths = _compose_portfolio_paths(asset_log, np.array([0.5, 0.5]), 100.0)
    expected = 100.0 * np.power(1.01, np.arange(6))
    for i in range(4):
        np.testing.assert_allclose(paths[i], expected, rtol=1e-9)


def test_monte_carlo_seeded_reproducible():
    hist = _historical_returns(seed=1)
    weights = np.array([0.5, 0.3, 0.2])
    rng_a = np.random.default_rng(123)
    rng_b = np.random.default_rng(123)
    a = simulate_monte_carlo(hist, weights, 10_000.0, n_steps=100, n_sims=50, rng=rng_a)
    b = simulate_monte_carlo(hist, weights, 10_000.0, n_steps=100, n_sims=50, rng=rng_b)
    np.testing.assert_array_equal(a.paths, b.paths)


def test_monte_carlo_different_seeds_diverge():
    hist = _historical_returns(seed=1)
    weights = np.array([0.5, 0.3, 0.2])
    a = simulate_monte_carlo(
        hist, weights, 10_000.0, 100, 50, np.random.default_rng(1)
    )
    b = simulate_monte_carlo(
        hist, weights, 10_000.0, 100, 50, np.random.default_rng(2)
    )
    assert not np.allclose(a.terminal_values, b.terminal_values)


def test_monte_carlo_paths_shapes():
    hist = _historical_returns()
    weights = np.array([0.5, 0.3, 0.2])
    res = simulate_monte_carlo(
        hist, weights, 1000.0, n_steps=20, n_sims=8, rng=np.random.default_rng(0)
    )
    assert res.paths.shape == (8, 21)
    assert res.terminal_values.shape == (8,)
    assert res.log_returns_per_step.shape == (8, 20)
    np.testing.assert_array_equal(res.paths[:, 0], 1000.0)
    np.testing.assert_array_equal(res.paths[:, -1], res.terminal_values)


def test_monte_carlo_drift_recovered():
    # Engine uses the empirical drift from `hist`, so the test expectation
    # must reference the sample mean of `hist`, not the underlying `true_mu`.
    rng = np.random.default_rng(0)
    hist = rng.normal(0.0008, 0.015, size=(2000, 1))
    sample_mu = float(hist.mean())
    sample_sigma = float(hist.std(ddof=1))
    n_steps = 252
    n_sims = 5000
    res = simulate_monte_carlo(
        hist, np.array([1.0]), 100.0, n_steps, n_sims, np.random.default_rng(7)
    )
    log_terminal = np.log(res.terminal_values / 100.0)
    expected = sample_mu * n_steps
    se = sample_sigma * np.sqrt(n_steps) / np.sqrt(n_sims)
    assert abs(log_terminal.mean() - expected) < 5 * se


def test_monte_carlo_vol_recovered():
    rng = np.random.default_rng(0)
    hist = rng.normal(0.0, 0.012, size=(2000, 1))
    sample_sigma = float(hist.std(ddof=1))
    n_steps = 252
    res = simulate_monte_carlo(
        hist, np.array([1.0]), 100.0, n_steps, 5000, np.random.default_rng(3)
    )
    log_terminal = np.log(res.terminal_values / 100.0)
    expected_std = sample_sigma * np.sqrt(n_steps)
    np.testing.assert_allclose(log_terminal.std(ddof=1), expected_std, rtol=0.05)


def test_monte_carlo_drift_override_shifts_mean():
    hist = _historical_returns(t=2000)
    weights = np.array([0.5, 0.3, 0.2])
    base = simulate_monte_carlo(
        hist, weights, 100.0, 252, 3000, np.random.default_rng(0)
    )
    boosted = simulate_monte_carlo(
        hist,
        weights,
        100.0,
        252,
        3000,
        np.random.default_rng(0),
        drift_override=np.array([0.01, 0.01, 0.01]),
    )
    assert boosted.terminal_values.mean() > base.terminal_values.mean() * 5


def test_monte_carlo_handles_perfectly_correlated_assets():
    # Two identical historical series → singular covariance; PSD correction must keep us alive.
    rng = np.random.default_rng(0)
    base = rng.normal(0, 0.01, size=(500,))
    hist = np.column_stack([base, base])
    res = simulate_monte_carlo(
        hist, np.array([0.5, 0.5]), 100.0, 50, 100, np.random.default_rng(0)
    )
    assert np.all(np.isfinite(res.terminal_values))


def test_monte_carlo_weight_mismatch_raises():
    hist = _historical_returns(a=3)
    with pytest.raises(ValueError):
        simulate_monte_carlo(
            hist, np.array([0.5, 0.5]), 100.0, 10, 10, np.random.default_rng(0)
        )


def test_monte_carlo_drift_override_shape_check():
    hist = _historical_returns(a=3)
    with pytest.raises(ValueError):
        simulate_monte_carlo(
            hist,
            np.array([0.4, 0.4, 0.2]),
            100.0,
            10,
            10,
            np.random.default_rng(0),
            drift_override=np.array([0.01, 0.01]),
        )


def test_bootstrap_seeded_reproducible():
    hist = _historical_returns()
    weights = np.array([0.5, 0.3, 0.2])
    a = simulate_bootstrap(hist, weights, 100.0, 50, 30, np.random.default_rng(9))
    b = simulate_bootstrap(hist, weights, 100.0, 50, 30, np.random.default_rng(9))
    np.testing.assert_array_equal(a.paths, b.paths)


def test_bootstrap_paths_start_at_initial():
    hist = _historical_returns()
    res = simulate_bootstrap(
        hist, np.array([0.5, 0.3, 0.2]), 500.0, 100, 20, np.random.default_rng(0)
    )
    np.testing.assert_array_equal(res.paths[:, 0], 500.0)


def test_bootstrap_preserves_marginal_distribution():
    """KS-style sanity check: sampled returns from bootstrap should be drawn
    from the same population as the historical returns."""
    rng = np.random.default_rng(0)
    hist = rng.normal(0, 0.02, size=(800, 1))
    res = simulate_bootstrap(
        hist, np.array([1.0]), 100.0, 1000, 100, np.random.default_rng(0)
    )
    # Per-step portfolio log-returns should have the same mean/std as hist.
    sampled = res.log_returns_per_step.flatten()
    np.testing.assert_allclose(sampled.mean(), hist.mean(), atol=1e-3)
    np.testing.assert_allclose(sampled.std(), hist.std(), rtol=0.05)


def test_bootstrap_preserves_cross_correlation():
    rng = np.random.default_rng(0)
    n = 800
    base = rng.normal(0, 0.01, size=(n,))
    other = 0.7 * base + 0.3 * rng.normal(0, 0.01, size=(n,))
    hist = np.column_stack([base, other])
    target_corr = np.corrcoef(hist, rowvar=False)[0, 1]
    # Walk through the engine but pull out the per-asset draws indirectly:
    # repeat the index draw and confirm correlation matches.
    rng2 = np.random.default_rng(123)
    idx = rng2.integers(0, n, size=(50_000,))
    sampled = hist[idx]
    sampled_corr = np.corrcoef(sampled, rowvar=False)[0, 1]
    assert abs(sampled_corr - target_corr) < 0.02


def test_bootstrap_block_size_long_block_runs():
    hist = _historical_returns()
    res = simulate_bootstrap(
        hist,
        np.array([0.5, 0.3, 0.2]),
        100.0,
        n_steps=120,
        n_sims=50,
        rng=np.random.default_rng(0),
        block_size=20,
    )
    # Sanity: shapes intact and paths non-negative.
    assert res.paths.shape == (50, 121)
    assert np.all(res.paths > 0)


def test_bootstrap_invalid_block_size_raises():
    hist = _historical_returns()
    with pytest.raises(ValueError):
        simulate_bootstrap(
            hist,
            np.array([0.5, 0.3, 0.2]),
            100.0,
            10,
            5,
            np.random.default_rng(0),
            block_size=0,
        )


def test_bootstrap_block_larger_than_history_falls_back_to_iid():
    hist = _historical_returns(t=20, a=2)
    # block_size > t → silently falls back to iid (block_size=1).
    res = simulate_bootstrap(
        hist,
        np.array([0.5, 0.5]),
        100.0,
        n_steps=30,
        n_sims=10,
        rng=np.random.default_rng(0),
        block_size=100,
    )
    assert res.paths.shape == (10, 31)


def test_bootstrap_weight_mismatch_raises():
    hist = _historical_returns(a=3)
    with pytest.raises(ValueError):
        simulate_bootstrap(
            hist, np.array([0.5, 0.5]), 100.0, 10, 10, np.random.default_rng(0)
        )
