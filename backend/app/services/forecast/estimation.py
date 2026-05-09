"""Pure helpers for estimating drift, volatility, and correlation from price history.

All functions are numpy-only and have no I/O — fully deterministic and easy to test.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ReturnStatistics:
    """Sample statistics estimated from a daily log-return matrix.

    Attributes:
        mu: shape (A,). Daily-mean log-return per asset.
        sigma: shape (A,). Daily std dev of log-returns per asset.
        cov: shape (A, A). Sample covariance of daily log-returns.
        corr: shape (A, A). Pearson correlation of daily log-returns.
        cholesky: shape (A, A). Lower Cholesky factor of `psd_correct(cov)`.
    """

    mu: np.ndarray
    sigma: np.ndarray
    cov: np.ndarray
    corr: np.ndarray
    cholesky: np.ndarray


def compute_log_returns(prices: np.ndarray) -> np.ndarray:
    """Convert a (T, A) matrix of adjusted close prices into a (T-1, A) log-return matrix.

    Raises:
        ValueError: when prices contain non-positive entries (log undefined).
    """
    if prices.ndim != 2:
        raise ValueError(f"prices must be 2D, got shape {prices.shape}")
    if prices.shape[0] < 2:
        raise ValueError("need at least 2 rows of prices to compute returns")
    if np.any(prices <= 0):
        raise ValueError("prices must be strictly positive")
    return np.diff(np.log(prices), axis=0)


def psd_correct(matrix: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Project a (possibly indefinite or near-singular) symmetric matrix onto the PSD cone.

    Clips eigenvalues at `eps` and reconstructs. Used before Cholesky factorisation
    to avoid LinAlgError on highly correlated tickers (e.g., SPY + IVV).
    """
    sym = 0.5 * (matrix + matrix.T)
    eigvals, eigvecs = np.linalg.eigh(sym)
    clipped = np.clip(eigvals, eps, None)
    return (eigvecs * clipped) @ eigvecs.T


def estimate_statistics(log_returns: np.ndarray) -> ReturnStatistics:
    """Compute mean, std, covariance, correlation, and Cholesky factor.

    `log_returns` shape: (T, A). T is the number of historical observations,
    A is the number of assets. Single-asset (A=1) is supported.
    """
    if log_returns.ndim != 2:
        raise ValueError(f"log_returns must be 2D, got shape {log_returns.shape}")
    if log_returns.shape[0] < 2:
        raise ValueError("need at least 2 observations to estimate statistics")

    mu = log_returns.mean(axis=0)
    # ddof=1 matches Stage 3 metrics convention (sample variance).
    sigma = log_returns.std(axis=0, ddof=1)
    cov = np.cov(log_returns, rowvar=False, ddof=1)
    if cov.ndim == 0:  # single-asset → np.cov returns 0-d
        cov = np.array([[float(cov)]])

    # Pearson correlation: defined as cov_ij / (sigma_i * sigma_j); guard against
    # zero-volatility assets by setting their row/col to identity contributions.
    safe_sigma = np.where(sigma > 0, sigma, 1.0)
    outer = np.outer(safe_sigma, safe_sigma)
    corr = cov / outer
    np.fill_diagonal(corr, 1.0)

    cholesky = np.linalg.cholesky(psd_correct(cov))
    return ReturnStatistics(mu=mu, sigma=sigma, cov=cov, corr=corr, cholesky=cholesky)
