"""Unit tests for the metrics module — pure functions over numeric arrays."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.backtest import metrics


def test_total_return_simple():
    m = metrics.core_metrics(
        daily_total_values=[100.0, 110.0],
        initial_cash=100.0,
        period_start=date(2024, 1, 2),
        period_end=date(2024, 1, 3),
        risk_free_rate=0.0,
    )
    assert m.total_return == pytest.approx(0.10)


def test_annualized_return_one_year_flat_10pct():
    """A 10% gain over exactly 365 days annualizes to 10% (ACT/365)."""
    m = metrics.core_metrics(
        daily_total_values=[100.0, 110.0],
        initial_cash=100.0,
        period_start=date(2025, 1, 1),
        period_end=date(2026, 1, 1),  # 365-day, non-leap span
        risk_free_rate=0.0,
    )
    assert m.annualized_return == pytest.approx(0.10, rel=1e-4)


def test_volatility_constant_returns_is_zero():
    """Constant geometric growth → daily returns all equal → std == 0."""
    values = [100.0 * (1.001 ** i) for i in range(50)]
    m = metrics.core_metrics(
        daily_total_values=values,
        initial_cash=100.0,
        period_start=date(2024, 1, 2),
        period_end=date(2024, 3, 12),
        risk_free_rate=0.0,
    )
    assert m.volatility == pytest.approx(0.0, abs=1e-10)
    # Sharpe should not blow up to inf when vol is zero.
    assert m.sharpe_ratio == 0.0


def test_max_drawdown_known_path():
    """100 → 110 → 80 → 120: peak 110, trough 80 → drawdown -27.27%."""
    mdd = metrics.max_drawdown([100.0, 110.0, 80.0, 120.0])
    assert mdd == pytest.approx(-30.0 / 110.0, rel=1e-6)


def test_max_drawdown_monotonic_up_is_zero():
    mdd = metrics.max_drawdown([100.0, 110.0, 120.0, 130.0])
    assert mdd == 0.0


def test_max_drawdown_single_point_safe():
    assert metrics.max_drawdown([100.0]) == 0.0
    assert metrics.max_drawdown([]) == 0.0


def test_daily_returns_correct_length_and_values():
    rets = metrics.daily_returns([100.0, 110.0, 99.0])
    assert len(rets) == 2
    assert rets[0] == pytest.approx(0.10)
    assert rets[1] == pytest.approx(-0.10, rel=1e-6)


def test_beta_against_self_is_one():
    """A series compared to itself has beta exactly 1.0."""
    values = [100.0, 102.0, 99.5, 105.0, 103.0, 108.0]
    bench = metrics.benchmark_metrics(
        portfolio_values=values,
        benchmark_values=values,
        period_start=date(2024, 1, 2),
        period_end=date(2024, 1, 9),
        risk_free_rate=0.0,
    )
    assert bench.beta == pytest.approx(1.0, rel=1e-6)


def test_alpha_against_self_is_zero():
    """A series compared to itself has alpha exactly 0.0."""
    values = [100.0, 102.0, 99.5, 105.0, 103.0, 108.0]
    bench = metrics.benchmark_metrics(
        portfolio_values=values,
        benchmark_values=values,
        period_start=date(2024, 1, 2),
        period_end=date(2024, 1, 9),
        risk_free_rate=0.0,
    )
    assert bench.alpha == pytest.approx(0.0, abs=1e-10)


def test_information_ratio_against_self_is_zero():
    """Identical series: excess returns are all zero, IR safely returns 0."""
    values = [100.0, 102.0, 99.5, 105.0]
    bench = metrics.benchmark_metrics(
        portfolio_values=values,
        benchmark_values=values,
        period_start=date(2024, 1, 2),
        period_end=date(2024, 1, 5),
        risk_free_rate=0.0,
    )
    assert bench.tracking_error == pytest.approx(0.0, abs=1e-10)
    assert bench.information_ratio == 0.0


def test_benchmark_total_return_matches_first_to_last():
    values = [100.0] * 5
    bench_values = [100.0, 105.0, 110.0, 108.0, 115.0]
    bench = metrics.benchmark_metrics(
        portfolio_values=values,
        benchmark_values=bench_values,
        period_start=date(2024, 1, 2),
        period_end=date(2024, 1, 8),
        risk_free_rate=0.0,
    )
    assert bench.benchmark_total_return == pytest.approx(0.15)


def test_build_benchmark_series_forward_fill_and_scale():
    """Forward-fills missing trading days and scales so first point == initial_cash."""
    bench_prices = [
        (date(2024, 1, 2), 400.0),
        (date(2024, 1, 4), 410.0),
        (date(2024, 1, 5), 412.0),
    ]
    portfolio_dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5)]
    series = metrics.build_benchmark_series(
        benchmark_prices=bench_prices,
        portfolio_dates=portfolio_dates,
        initial_cash=10_000.0,
    )
    assert len(series) == 4
    assert series[0] == pytest.approx(10_000.0)
    # 1/3 was forward-filled from 1/2's 400.
    assert series[1] == pytest.approx(10_000.0)
    # 1/4 jumps to 410/400 * 10_000 = 10_250.
    assert series[2] == pytest.approx(10_250.0)
    assert series[3] == pytest.approx(10_300.0, rel=1e-6)


def test_build_benchmark_series_empty_dates_returns_empty():
    series = metrics.build_benchmark_series(
        benchmark_prices=[(date(2024, 1, 2), 100.0)],
        portfolio_dates=[],
        initial_cash=10_000.0,
    )
    assert series == []


def test_build_benchmark_series_empty_prices_raises():
    with pytest.raises(ValueError):
        metrics.build_benchmark_series(
            benchmark_prices=[],
            portfolio_dates=[date(2024, 1, 2)],
            initial_cash=10_000.0,
        )


def test_core_metrics_two_point_window_safe():
    """Minimal valid input: 2 points. Should not crash or produce NaN."""
    m = metrics.core_metrics(
        daily_total_values=[100.0, 105.0],
        initial_cash=100.0,
        period_start=date(2024, 1, 2),
        period_end=date(2024, 1, 3),
        risk_free_rate=0.0,
    )
    assert m.total_return == pytest.approx(0.05)
    # With a single return observation, sample std is undefined → vol == 0.0.
    assert m.volatility == 0.0
    assert m.sharpe_ratio == 0.0


def test_benchmark_metrics_mismatched_lengths_returns_zeros():
    bench = metrics.benchmark_metrics(
        portfolio_values=[100.0, 101.0, 102.0],
        benchmark_values=[100.0, 101.0],
        period_start=date(2024, 1, 2),
        period_end=date(2024, 1, 5),
        risk_free_rate=0.0,
    )
    assert bench.alpha == 0.0
    assert bench.beta == 0.0


def test_sharpe_with_nonzero_risk_free_rate_lowers_value():
    """Same series, higher risk-free rate → lower Sharpe."""
    values = [100.0 + i for i in range(10)]
    period = (date(2024, 1, 2), date(2024, 1, 16))
    a = metrics.core_metrics(values, 100.0, *period, risk_free_rate=0.0)
    b = metrics.core_metrics(values, 100.0, *period, risk_free_rate=0.05)
    assert b.sharpe_ratio < a.sharpe_ratio
