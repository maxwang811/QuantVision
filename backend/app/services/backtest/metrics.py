"""Risk and performance metrics over a daily portfolio value series.

Pure functions over numeric arrays. No DB, no SQLAlchemy, no I/O. The runner
calls these after the engine produces an EngineResult; the recompute endpoint
calls them against persisted portfolio_values.

All metrics are NaN-safe: degenerate inputs (zero volatility, single-point
series) return 0.0 rather than NaN/Inf so JSON serialization stays clean.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np

from app.core.time import year_fraction

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class CoreMetrics:
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float


@dataclass(frozen=True)
class BenchmarkMetrics:
    benchmark_total_return: float
    benchmark_annualized_return: float
    alpha: float
    beta: float
    information_ratio: float
    tracking_error: float


def daily_returns(values: list[float]) -> np.ndarray:
    """Simple period-over-period returns. Length is len(values) - 1."""
    arr = np.asarray(values, dtype=float)
    if arr.size < 2:
        return np.array([], dtype=float)
    return arr[1:] / arr[:-1] - 1.0


def max_drawdown(values: list[float]) -> float:
    """Deepest peak-to-trough decline as a fraction (e.g., -0.214 for -21.4%).

    Returns 0.0 if the series only goes up or has fewer than 2 points.
    """
    arr = np.asarray(values, dtype=float)
    if arr.size < 2:
        return 0.0
    running_peak = np.maximum.accumulate(arr)
    drawdowns = (arr - running_peak) / running_peak
    return float(drawdowns.min())


def core_metrics(
    daily_total_values: list[float],
    initial_cash: float,
    period_start: date,
    period_end: date,
    risk_free_rate: float,
) -> CoreMetrics:
    """Compute the five headline metrics over a daily portfolio value series."""
    if not daily_total_values:
        return CoreMetrics(0.0, 0.0, 0.0, 0.0, 0.0)

    final = float(daily_total_values[-1])
    total_ret = final / initial_cash - 1.0

    yf = year_fraction(period_start, period_end)
    if yf > 0 and (1.0 + total_ret) > 0:
        ann_ret = (1.0 + total_ret) ** (1.0 / yf) - 1.0
    else:
        ann_ret = 0.0

    rets = daily_returns(daily_total_values)
    if rets.size >= 2:
        # Sample std (ddof=1) annualized via sqrt(252).
        vol = float(rets.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR))
    else:
        vol = 0.0

    # Float-safe threshold: avoid Sharpe blow-up on near-zero variance series.
    sharpe = (ann_ret - risk_free_rate) / vol if vol > 1e-12 else 0.0
    mdd = max_drawdown(daily_total_values)

    return CoreMetrics(
        total_return=float(total_ret),
        annualized_return=float(ann_ret),
        volatility=float(vol),
        sharpe_ratio=float(sharpe),
        max_drawdown=float(mdd),
    )


def benchmark_metrics(
    portfolio_values: list[float],
    benchmark_values: list[float],
    period_start: date,
    period_end: date,
    risk_free_rate: float,
) -> BenchmarkMetrics:
    """Comparison metrics: benchmark return, beta, Jensen's alpha, info ratio.

    `portfolio_values` and `benchmark_values` must be equal-length and aligned
    on the same trading days. Both should start with the same nominal value
    (e.g., the initial cash) so total returns are directly comparable.
    """
    if (
        len(portfolio_values) != len(benchmark_values)
        or len(portfolio_values) < 2
    ):
        return BenchmarkMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    bench_arr = np.asarray(benchmark_values, dtype=float)
    bench_initial = float(bench_arr[0])
    bench_final = float(bench_arr[-1])
    bench_total_ret = bench_final / bench_initial - 1.0

    yf = year_fraction(period_start, period_end)
    if yf > 0 and (1.0 + bench_total_ret) > 0:
        bench_ann_ret = (1.0 + bench_total_ret) ** (1.0 / yf) - 1.0
    else:
        bench_ann_ret = 0.0

    port_rets = daily_returns(portfolio_values)
    bench_rets = daily_returns(benchmark_values)

    if port_rets.size < 2 or bench_rets.size < 2:
        return BenchmarkMetrics(
            benchmark_total_return=float(bench_total_ret),
            benchmark_annualized_return=float(bench_ann_ret),
            alpha=0.0,
            beta=0.0,
            information_ratio=0.0,
            tracking_error=0.0,
        )

    bench_var = float(bench_rets.var(ddof=1))
    if bench_var > 0:
        cov = float(np.cov(port_rets, bench_rets, ddof=1)[0, 1])
        beta = cov / bench_var
    else:
        beta = 0.0

    # Annualized portfolio return for Jensen's alpha. Recompute here rather
    # than threading it in — this function should stand on its own.
    port_initial = float(portfolio_values[0])
    port_final = float(portfolio_values[-1])
    port_total_ret = port_final / port_initial - 1.0
    if yf > 0 and (1.0 + port_total_ret) > 0:
        port_ann_ret = (1.0 + port_total_ret) ** (1.0 / yf) - 1.0
    else:
        port_ann_ret = 0.0

    alpha = port_ann_ret - (risk_free_rate + beta * (bench_ann_ret - risk_free_rate))

    excess = port_rets - bench_rets
    excess_std = float(excess.std(ddof=1))
    tracking_err = excess_std * np.sqrt(TRADING_DAYS_PER_YEAR)
    info_ratio = (
        (port_ann_ret - bench_ann_ret) / tracking_err if tracking_err > 1e-12 else 0.0
    )

    return BenchmarkMetrics(
        benchmark_total_return=float(bench_total_ret),
        benchmark_annualized_return=float(bench_ann_ret),
        alpha=float(alpha),
        beta=float(beta),
        information_ratio=float(info_ratio),
        tracking_error=float(tracking_err),
    )


def build_benchmark_series(
    benchmark_prices: list[tuple[date, float]],
    portfolio_dates: list[date],
    initial_cash: float,
) -> list[float]:
    """Align benchmark adj_close prices to portfolio_dates with forward-fill,
    then scale so the first point equals initial_cash.

    Both inputs must be sorted ascending by date. If a portfolio date precedes
    every benchmark price, the earliest benchmark price is used (warns implicitly
    via constant prefix). Raises ValueError if benchmark_prices is empty.
    """
    if not benchmark_prices:
        raise ValueError("benchmark_prices is empty")
    if not portfolio_dates:
        return []

    bench_dates = [d for d, _ in benchmark_prices]
    bench_vals = [p for _, p in benchmark_prices]

    aligned: list[float] = []
    j = 0
    last_seen: float | None = None
    for d in portfolio_dates:
        while j < len(bench_dates) and bench_dates[j] <= d:
            last_seen = bench_vals[j]
            j += 1
        if last_seen is None:
            # Portfolio date is before the earliest benchmark price; fall back
            # to the earliest available so the series isn't broken.
            last_seen = bench_vals[0]
        aligned.append(last_seen)

    first = aligned[0]
    if first <= 0:
        raise ValueError(f"benchmark first price must be positive, got {first}")
    scale = initial_cash / first
    return [v * scale for v in aligned]
