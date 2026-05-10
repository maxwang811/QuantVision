"""Pure mean-variance / max-Sharpe portfolio optimizer.

All functions are numpy + scipy only — no DB, no I/O, fully deterministic given
inputs. The runner module wraps these in DB lookups and validation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from app.services.forecast.estimation import psd_correct

_TRADING_DAYS_PER_YEAR = 252
_EPS = 1e-12


@dataclass(frozen=True)
class FrontierPoint:
    """A single point on the efficient frontier or a named optimum."""

    ret: float
    """Annualized expected return (linear, not log)."""

    vol: float
    """Annualized volatility."""

    sharpe: float
    """Annualized Sharpe ratio (excess over risk-free rate)."""

    weights: np.ndarray
    """Portfolio weights, shape (A,). Long-only, sums to 1."""


@dataclass(frozen=True)
class OptimizationResult:
    tickers: list[str]
    min_variance: FrontierPoint
    max_sharpe: FrontierPoint
    target_return: FrontierPoint | None
    frontier: list[FrontierPoint]
    risk_free_rate: float
    n_observations: int


def annualized_stats(daily_log_returns: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Convert daily log-returns into annualized expected return + covariance.

    The expected-return vector here uses the simple-return convention
    `mu = exp(mu_log + 0.5 * var) - 1`, so the optimizer's sharpe number lines
    up with backtest CAGR. Covariance is annualized by multiplying daily by 252.
    """
    if daily_log_returns.ndim != 2:
        raise ValueError(f"daily_log_returns must be 2D, got {daily_log_returns.shape}")
    n_obs, n_assets = daily_log_returns.shape
    if n_obs < max(2, n_assets):
        raise ValueError(
            f"need at least max(2, n_assets={n_assets}) observations, got {n_obs}"
        )
    mu_log_daily = daily_log_returns.mean(axis=0)
    cov_daily = np.cov(daily_log_returns, rowvar=False, ddof=1)
    if cov_daily.ndim == 0:
        cov_daily = np.array([[float(cov_daily)]])
    var_daily = np.diag(cov_daily)
    mu_log_annual = mu_log_daily * _TRADING_DAYS_PER_YEAR
    var_annual = var_daily * _TRADING_DAYS_PER_YEAR
    mu_annual = np.exp(mu_log_annual + 0.5 * var_annual) - 1.0
    cov_annual = cov_daily * _TRADING_DAYS_PER_YEAR
    cov_annual = psd_correct(cov_annual)
    return mu_annual, cov_annual


def optimize_portfolio(
    daily_log_returns: np.ndarray,
    tickers: list[str],
    risk_free_rate: float = 0.0,
    target_return: float | None = None,
    n_frontier_points: int = 25,
) -> OptimizationResult:
    """Run min-variance, max-Sharpe, optional target-return, and an efficient frontier.

    Long-only, fully invested (weights ≥ 0, sum to 1). Uses SLSQP from scipy.

    Raises:
        ValueError: when input dimensions or history are insufficient.
    """
    if len(tickers) != daily_log_returns.shape[1]:
        raise ValueError(
            f"tickers length ({len(tickers)}) does not match returns columns "
            f"({daily_log_returns.shape[1]})"
        )

    mu, cov = annualized_stats(daily_log_returns)

    min_var = _min_variance(mu, cov, target_return=None)
    max_sharpe = _max_sharpe(mu, cov, risk_free_rate)
    target_pt = (
        _min_variance(mu, cov, target_return=target_return)
        if target_return is not None
        else None
    )
    frontier = _efficient_frontier(mu, cov, n_frontier_points, risk_free_rate)

    n_obs = int(daily_log_returns.shape[0])
    return OptimizationResult(
        tickers=list(tickers),
        min_variance=_with_sharpe(min_var, mu, cov, risk_free_rate),
        max_sharpe=_with_sharpe(max_sharpe, mu, cov, risk_free_rate),
        target_return=(
            _with_sharpe(target_pt, mu, cov, risk_free_rate)
            if target_pt is not None
            else None
        ),
        frontier=frontier,
        risk_free_rate=float(risk_free_rate),
        n_observations=n_obs,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _portfolio_stats(
    weights: np.ndarray, mu: np.ndarray, cov: np.ndarray
) -> tuple[float, float]:
    ret = float(weights @ mu)
    vol = float(np.sqrt(max(weights @ cov @ weights, 0.0)))
    return ret, vol


def _with_sharpe(
    pt: FrontierPoint, mu: np.ndarray, cov: np.ndarray, rf: float
) -> FrontierPoint:
    ret, vol = _portfolio_stats(pt.weights, mu, cov)
    sharpe = (ret - rf) / vol if vol > _EPS else 0.0
    return FrontierPoint(ret=ret, vol=vol, sharpe=sharpe, weights=pt.weights)


def _min_variance(
    mu: np.ndarray, cov: np.ndarray, *, target_return: float | None
) -> FrontierPoint:
    n = mu.shape[0]
    w0 = np.full(n, 1.0 / n)
    bounds = [(0.0, 1.0)] * n
    constraints: list[dict] = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    if target_return is not None:
        tr = float(target_return)
        constraints.append({"type": "eq", "fun": lambda w, m=mu, t=tr: float(w @ m) - t})

    result = minimize(
        fun=lambda w, c=cov: float(w @ c @ w),
        x0=w0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-10, "maxiter": 300},
    )
    if not result.success:
        raise ValueError(
            f"min-variance optimization failed: {result.message} "
            f"(target_return={target_return})"
        )
    weights = _clip_and_normalize(result.x)
    ret, vol = _portfolio_stats(weights, mu, cov)
    return FrontierPoint(ret=ret, vol=vol, sharpe=0.0, weights=weights)


def _max_sharpe(mu: np.ndarray, cov: np.ndarray, rf: float) -> FrontierPoint:
    n = mu.shape[0]
    w0 = np.full(n, 1.0 / n)
    bounds = [(0.0, 1.0)] * n
    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]

    def neg_sharpe(w: np.ndarray) -> float:
        ret = float(w @ mu)
        var = float(w @ cov @ w)
        vol = float(np.sqrt(max(var, _EPS)))
        return -(ret - rf) / vol

    result = minimize(
        fun=neg_sharpe,
        x0=w0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-10, "maxiter": 500},
    )
    if not result.success:
        # Corner case: degenerate — fall back to argmax(mu) one-hot.
        weights = np.zeros(n)
        weights[int(np.argmax(mu))] = 1.0
    else:
        weights = _clip_and_normalize(result.x)
    ret, vol = _portfolio_stats(weights, mu, cov)
    return FrontierPoint(ret=ret, vol=vol, sharpe=0.0, weights=weights)


def _efficient_frontier(
    mu: np.ndarray, cov: np.ndarray, n_points: int, rf: float
) -> list[FrontierPoint]:
    targets = np.linspace(float(np.min(mu)), float(np.max(mu)), n_points)
    points: list[FrontierPoint] = []
    for t in targets:
        try:
            pt = _min_variance(mu, cov, target_return=float(t))
        except ValueError:
            continue
        points.append(_with_sharpe(pt, mu, cov, rf))
    return points


def _clip_and_normalize(w: np.ndarray) -> np.ndarray:
    """SLSQP can produce tiny negatives or sums slightly off from 1.0. Clean up."""
    w = np.clip(w, 0.0, None)
    s = w.sum()
    if s <= 0:
        return np.full_like(w, 1.0 / w.shape[0])
    return w / s
