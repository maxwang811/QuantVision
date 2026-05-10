"""Unit tests for the pure portfolio optimization kernel."""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pytest

from app.services.optimization.optimizer import (
    annualized_stats,
    optimize_portfolio,
)


def _correlated_returns(
    n_obs: int,
    sigmas: list[float],
    mus_log_daily: list[float],
    corr: np.ndarray,
    seed: int = 0,
) -> np.ndarray:
    """Generate (n_obs, n_assets) correlated daily log-returns from a Gaussian."""
    rng = np.random.default_rng(seed)
    n_assets = len(sigmas)
    L = np.linalg.cholesky(corr + 1e-12 * np.eye(n_assets))
    z = rng.standard_normal((n_obs, n_assets))
    correlated = z @ L.T
    sigma_daily = np.array(sigmas) / np.sqrt(252)
    mu_daily = np.array(mus_log_daily)
    return mu_daily + correlated * sigma_daily


def test_two_asset_min_variance_matches_closed_form():
    """For two assets, min-variance long-only weight is closed-form when both
    contribute (no corner solution).

    Closed form (long-only, fully invested):
        w1 = (sigma2^2 - rho * sigma1 * sigma2) / (sigma1^2 + sigma2^2 - 2*rho*sigma1*sigma2)
    """
    sigma1, sigma2, rho = 0.20, 0.40, 0.3
    corr = np.array([[1.0, rho], [rho, 1.0]])
    returns = _correlated_returns(
        n_obs=4000, sigmas=[sigma1, sigma2],
        mus_log_daily=[0.0003, 0.0005], corr=corr, seed=42,
    )

    result = optimize_portfolio(returns, tickers=["A", "B"], n_frontier_points=10)
    w1 = result.min_variance.weights[0]

    # Closed form on annualized inputs.
    expected_w1 = (sigma2**2 - rho * sigma1 * sigma2) / (
        sigma1**2 + sigma2**2 - 2 * rho * sigma1 * sigma2
    )
    # Allow generous tolerance because the empirical cov differs from the prior.
    assert abs(w1 - expected_w1) < 0.05, (
        f"min-var w1={w1:.4f} expected ~{expected_w1:.4f}"
    )


def test_max_sharpe_corner_when_dominated():
    """If two assets share the same vol but one has higher mu, max-Sharpe should
    put effectively all weight on the dominant asset (corner solution)."""
    sigma = 0.20
    corr = np.array([[1.0, 0.0], [0.0, 1.0]])
    returns = _correlated_returns(
        n_obs=4000, sigmas=[sigma, sigma],
        mus_log_daily=[0.001, 0.0001], corr=corr, seed=7,
    )

    result = optimize_portfolio(returns, tickers=["A", "B"])
    # Asset A dominates: weight on A should be very close to 1.
    assert result.max_sharpe.weights[0] > 0.95


def test_weights_sum_to_one_and_nonneg():
    sigmas = [0.18, 0.25, 0.30]
    corr = np.array([
        [1.0, 0.3, 0.1],
        [0.3, 1.0, 0.4],
        [0.1, 0.4, 1.0],
    ])
    returns = _correlated_returns(
        n_obs=2000, sigmas=sigmas,
        mus_log_daily=[0.0004, 0.0005, 0.0006], corr=corr, seed=11,
    )
    result = optimize_portfolio(returns, tickers=["A", "B", "C"], n_frontier_points=25)

    points = [result.min_variance, result.max_sharpe, *result.frontier]
    assert len(points) >= 3
    for p in points:
        assert abs(float(np.sum(p.weights)) - 1.0) < 1e-4
        assert float(np.min(p.weights)) >= -1e-8
        assert p.weights.shape == (3,)


def test_efficient_frontier_volatility_monotonic_on_upper_half():
    """On the efficient half of the frontier (returns >= min-var return),
    higher expected return must come with higher (or equal) volatility."""
    sigmas = [0.18, 0.25, 0.30]
    corr = np.array([
        [1.0, 0.3, 0.1],
        [0.3, 1.0, 0.4],
        [0.1, 0.4, 1.0],
    ])
    returns = _correlated_returns(
        n_obs=2500, sigmas=sigmas,
        mus_log_daily=[0.0004, 0.0005, 0.0006], corr=corr, seed=13,
    )
    result = optimize_portfolio(returns, tickers=["A", "B", "C"], n_frontier_points=25)

    min_var_ret = result.min_variance.ret
    upper = sorted(
        [p for p in result.frontier if p.ret >= min_var_ret - 1e-9],
        key=lambda p: p.ret,
    )
    for prev, cur in pairwise(upper):
        assert cur.vol >= prev.vol - 1e-4, (
            f"frontier not monotonic: ret {prev.ret:.4f}->{cur.ret:.4f} but "
            f"vol {prev.vol:.4f}->{cur.vol:.4f}"
        )


def test_target_return_satisfied_within_range():
    sigmas = [0.20, 0.30]
    corr = np.array([[1.0, 0.2], [0.2, 1.0]])
    returns = _correlated_returns(
        n_obs=3000, sigmas=sigmas,
        mus_log_daily=[0.0003, 0.0008], corr=corr, seed=99,
    )

    mu_annual, _ = annualized_stats(returns)
    target = float(np.mean(mu_annual))
    result = optimize_portfolio(
        returns, tickers=["A", "B"], target_return=target,
    )

    assert result.target_return is not None
    assert abs(result.target_return.ret - target) < 1e-3


def test_insufficient_history_raises():
    # 1 observation with 3 assets should not optimize — annualized_stats raises.
    returns = np.zeros((1, 3))
    with pytest.raises(ValueError):
        optimize_portfolio(returns, tickers=["A", "B", "C"])


def test_tickers_length_must_match_columns():
    returns = np.zeros((100, 3))
    with pytest.raises(ValueError):
        optimize_portfolio(returns, tickers=["A", "B"])


def test_sharpe_consistent_with_returns_and_vol():
    sigmas = [0.20, 0.25]
    corr = np.array([[1.0, 0.2], [0.2, 1.0]])
    returns = _correlated_returns(
        n_obs=2500, sigmas=sigmas,
        mus_log_daily=[0.0004, 0.0006], corr=corr, seed=21,
    )
    rf = 0.03
    result = optimize_portfolio(returns, tickers=["A", "B"], risk_free_rate=rf)

    for p in [result.min_variance, result.max_sharpe, *result.frontier]:
        if p.vol > 1e-8:
            expected = (p.ret - rf) / p.vol
            assert abs(p.sharpe - expected) < 1e-6
