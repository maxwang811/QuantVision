"""Pure simulation kernels for the forecasting engine.

No I/O, no DB, no globals. Each kernel takes pre-loaded numpy arrays plus a seeded
`np.random.Generator` and returns a `SimulationResult`. Use `standard_normal +
Cholesky` rather than `multivariate_normal` because the latter has historically
changed sample order across numpy versions.

Portfolio composition: per-asset returns are simulated as log-returns, but
portfolio returns are weight-mixed in *simple-return* space (log is non-linear,
so summing weighted log-returns across assets is mathematically wrong).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.services.forecast.estimation import estimate_statistics


@dataclass(frozen=True)
class SimulationResult:
    """Output of a single simulation method.

    Attributes:
        paths: shape (n_sims, n_steps + 1). Portfolio dollar value path; column 0
            equals `initial_value` exactly.
        terminal_values: shape (n_sims,). Convenience view of `paths[:, -1]`.
        log_returns_per_step: shape (n_sims, n_steps). Per-step portfolio
            log-return; useful for downstream vol metrics.
    """

    paths: np.ndarray
    terminal_values: np.ndarray
    log_returns_per_step: np.ndarray


def _compose_portfolio_paths(
    asset_log_returns: np.ndarray,
    weights: np.ndarray,
    initial_value: float,
) -> np.ndarray:
    """Build portfolio dollar paths from per-asset log-return draws.

    `asset_log_returns` shape: (n_sims, n_steps, n_assets).
    `weights` shape: (n_assets,). Must be non-negative and sum to 1.
    Returns shape: (n_sims, n_steps + 1) — column 0 is `initial_value`.
    """
    asset_simple = np.expm1(asset_log_returns)
    # Weighted sum over the asset axis → portfolio simple return per step.
    port_simple = np.einsum("sta,a->st", asset_simple, weights)
    # Cumulative wealth, prepended with the initial 1.0 column.
    factors = 1.0 + port_simple
    cum = np.cumprod(factors, axis=1)
    ones = np.ones((cum.shape[0], 1), dtype=cum.dtype)
    paths = np.concatenate([ones, cum], axis=1) * initial_value
    return paths


def _portfolio_log_returns(paths: np.ndarray) -> np.ndarray:
    """Per-step portfolio log-returns derived from a paths matrix."""
    return np.log(paths[:, 1:] / paths[:, :-1])


def simulate_monte_carlo(
    historical_log_returns: np.ndarray,
    weights: np.ndarray,
    initial_value: float,
    n_steps: int,
    n_sims: int,
    rng: np.random.Generator,
    drift_override: np.ndarray | None = None,
) -> SimulationResult:
    """Multivariate-normal log-return simulation (parametric Monte Carlo).

    Drift defaults to the historical mean log-return per asset. `drift_override`
    (used by the ML method) replaces only the drift; covariance/Cholesky come
    from the historical sample regardless.
    """
    weights = np.asarray(weights, dtype=np.float64)
    n_assets = weights.shape[0]
    if historical_log_returns.shape[1] != n_assets:
        raise ValueError(
            f"weights length ({n_assets}) must match historical_log_returns "
            f"asset axis ({historical_log_returns.shape[1]})"
        )

    stats = estimate_statistics(historical_log_returns)
    mu = stats.mu if drift_override is None else np.asarray(drift_override, dtype=np.float64)
    if mu.shape != (n_assets,):
        raise ValueError(f"drift shape {mu.shape} must equal ({n_assets},)")

    # Independent standard normals → multivariate normal via Cholesky.
    z = rng.standard_normal((n_sims, n_steps, n_assets))
    eps = z @ stats.cholesky.T  # (n_sims, n_steps, n_assets)
    asset_log_returns = mu + eps  # broadcast: (n_sims, n_steps, n_assets)

    paths = _compose_portfolio_paths(asset_log_returns, weights, initial_value)
    terminal = paths[:, -1].copy()
    port_log = _portfolio_log_returns(paths)
    return SimulationResult(
        paths=paths, terminal_values=terminal, log_returns_per_step=port_log
    )


def simulate_bootstrap(
    historical_log_returns: np.ndarray,
    weights: np.ndarray,
    initial_value: float,
    n_steps: int,
    n_sims: int,
    rng: np.random.Generator,
    block_size: int = 1,
) -> SimulationResult:
    """Historical-bootstrap simulation.

    Samples whole *rows* of the historical return matrix with replacement so
    contemporaneous cross-asset correlations are preserved exactly. With
    `block_size > 1`, draws contiguous blocks (moving-block bootstrap) to
    preserve short-run autocorrelation.
    """
    weights = np.asarray(weights, dtype=np.float64)
    n_assets = weights.shape[0]
    if historical_log_returns.shape[1] != n_assets:
        raise ValueError(
            f"weights length ({n_assets}) must match historical_log_returns "
            f"asset axis ({historical_log_returns.shape[1]})"
        )

    t_hist = historical_log_returns.shape[0]
    if t_hist < 2:
        raise ValueError("need at least 2 historical observations for bootstrap")
    if block_size < 1:
        raise ValueError("block_size must be >= 1")
    if block_size > t_hist:
        block_size = 1  # fall back to iid when history is too short for blocks

    if block_size == 1:
        idx = rng.integers(0, t_hist, size=(n_sims, n_steps))
        sampled = historical_log_returns[idx]  # (n_sims, n_steps, n_assets)
    else:
        n_blocks = (n_steps + block_size - 1) // block_size
        starts = rng.integers(0, t_hist - block_size + 1, size=(n_sims, n_blocks))
        offsets = np.arange(block_size)
        # Build (n_sims, n_blocks, block_size) of indices, flatten to (n_sims, n_blocks*block_size),
        # then truncate to n_steps.
        idx_full = (starts[..., None] + offsets[None, None, :]).reshape(n_sims, -1)
        idx = idx_full[:, :n_steps]
        sampled = historical_log_returns[idx]

    paths = _compose_portfolio_paths(sampled, weights, initial_value)
    terminal = paths[:, -1].copy()
    port_log = _portfolio_log_returns(paths)
    return SimulationResult(
        paths=paths, terminal_values=terminal, log_returns_per_step=port_log
    )
