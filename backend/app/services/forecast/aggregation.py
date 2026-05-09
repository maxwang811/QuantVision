"""Pure post-processing for simulation results.

Takes raw `SimulationResult` arrays and produces percentile summaries, sampled
paths for visualization, and histogram bins. No DB, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SummaryStats:
    expected_value: float
    median_value: float
    p5: float
    p10: float
    p25: float
    p75: float
    p90: float
    p95: float
    probability_of_loss: float
    annualized_volatility: float
    expected_return: float


@dataclass(frozen=True)
class HistogramBin:
    index: int
    lower: float
    upper: float
    count: int


def summarize_distribution(
    terminal_values: np.ndarray,
    initial_value: float,
    horizon_years: float,
) -> SummaryStats:
    """Aggregate the terminal-value distribution into headline numbers.

    `annualized_volatility` is the std of log-terminal-returns divided by
    sqrt(horizon_years) — the standard form for annualizing log-return std.
    `expected_return` is the mean log-terminal-return divided by horizon_years.
    """
    if terminal_values.ndim != 1:
        raise ValueError("terminal_values must be 1D")
    if terminal_values.size == 0:
        raise ValueError("terminal_values must be non-empty")
    if initial_value <= 0:
        raise ValueError("initial_value must be positive")
    if horizon_years <= 0:
        raise ValueError("horizon_years must be positive")

    pcts = np.percentile(terminal_values, [5, 10, 25, 50, 75, 90, 95])
    log_term = np.log(terminal_values / initial_value)
    return SummaryStats(
        expected_value=float(terminal_values.mean()),
        median_value=float(pcts[3]),
        p5=float(pcts[0]),
        p10=float(pcts[1]),
        p25=float(pcts[2]),
        p75=float(pcts[4]),
        p90=float(pcts[5]),
        p95=float(pcts[6]),
        probability_of_loss=float((terminal_values < initial_value).mean()),
        annualized_volatility=float(log_term.std(ddof=1) / np.sqrt(horizon_years)),
        expected_return=float(log_term.mean() / horizon_years),
    )


def select_sample_paths(
    paths: np.ndarray, n_sample: int
) -> tuple[np.ndarray, list[str | None]]:
    """Pick a representative subset of paths for visualization.

    Strategy: rank simulations by terminal value, then pick the worst, the
    median, the best, plus `n_sample - 3` evenly-spaced rank quantiles. The
    result preserves the *shape* of the distribution at the cost of slight
    redundancy when n_sims is small.

    Returns:
        sampled_paths: shape (n_sample, n_steps + 1).
        rank_labels: list of length `n_sample`, with 'best'/'worst'/'median'
            on the corresponding rows and None elsewhere.
    """
    if paths.ndim != 2:
        raise ValueError("paths must be 2D")
    n_sims = paths.shape[0]
    if n_sims == 0:
        raise ValueError("paths must contain at least one simulation")
    n_sample = min(n_sample, n_sims)
    if n_sample < 3:
        # Degenerate case (n_sims < 3): just return everything we have.
        return paths.copy(), [None] * n_sample

    order = np.argsort(paths[:, -1])
    worst_idx = int(order[0])
    best_idx = int(order[-1])
    median_idx = int(order[n_sims // 2])

    # Evenly spaced rank positions across [0, n_sims-1] for the remaining slots.
    fillers_needed = n_sample - 3
    if fillers_needed > 0:
        positions = np.linspace(0, n_sims - 1, num=fillers_needed + 2)[1:-1]
        filler_indices = order[positions.astype(int)]
    else:
        filler_indices = np.array([], dtype=int)

    chosen_indices: list[int] = list(filler_indices.tolist()) + [worst_idx, median_idx, best_idx]
    # De-duplicate while preserving insertion order; if duplicates collapse the
    # output, top up with extra rank-quantile rows.
    seen: set[int] = set()
    deduped: list[int] = []
    for idx in chosen_indices:
        if idx not in seen:
            seen.add(idx)
            deduped.append(idx)
    # Top up if dedup removed entries (only happens when n_sample is close to n_sims).
    cursor = 0
    while len(deduped) < n_sample and cursor < n_sims:
        candidate = int(order[cursor])
        if candidate not in seen:
            seen.add(candidate)
            deduped.append(candidate)
        cursor += 1

    sampled = paths[deduped]
    labels: list[str | None] = [None] * len(deduped)
    for i, idx in enumerate(deduped):
        if idx == worst_idx:
            labels[i] = "worst"
        elif idx == best_idx:
            labels[i] = "best"
        elif idx == median_idx:
            labels[i] = "median"
    return sampled, labels


def build_histogram(
    terminal_values: np.ndarray, n_bins: int = 50
) -> list[HistogramBin]:
    """Compute a fixed-width histogram of terminal values."""
    if terminal_values.ndim != 1:
        raise ValueError("terminal_values must be 1D")
    if n_bins < 1:
        raise ValueError("n_bins must be >= 1")
    counts, edges = np.histogram(terminal_values, bins=n_bins)
    return [
        HistogramBin(
            index=i,
            lower=float(edges[i]),
            upper=float(edges[i + 1]),
            count=int(counts[i]),
        )
        for i in range(n_bins)
    ]


def prob_beat_benchmark(
    portfolio_terminals: np.ndarray, benchmark_terminals: np.ndarray
) -> float:
    """Fraction of simulations where the portfolio terminal exceeds the benchmark.

    Note: this uses element-wise comparison of independent simulations of the
    portfolio and benchmark. The simulations are NOT jointly drawn — see the
    Stage 5 plan and API docs for the rationale.
    """
    if portfolio_terminals.shape != benchmark_terminals.shape:
        raise ValueError(
            f"portfolio_terminals shape {portfolio_terminals.shape} must match "
            f"benchmark_terminals shape {benchmark_terminals.shape}"
        )
    return float((portfolio_terminals > benchmark_terminals).mean())
