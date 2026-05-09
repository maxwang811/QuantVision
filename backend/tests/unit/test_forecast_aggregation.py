"""Tests for services/forecast/aggregation.py."""

from __future__ import annotations

import numpy as np
import pytest

from app.services.forecast.aggregation import (
    build_histogram,
    prob_beat_benchmark,
    select_sample_paths,
    summarize_distribution,
)


def test_summarize_distribution_percentiles_ordered():
    rng = np.random.default_rng(0)
    terminals = rng.lognormal(mean=0.1, sigma=0.3, size=10_000) * 10_000
    s = summarize_distribution(terminals, initial_value=10_000.0, horizon_years=1.0)
    assert s.p5 <= s.p10 <= s.p25 <= s.median_value <= s.p75 <= s.p90 <= s.p95


def test_summarize_distribution_probability_in_unit_interval():
    rng = np.random.default_rng(0)
    terminals = rng.lognormal(0, 0.3, size=5000) * 10_000
    s = summarize_distribution(terminals, initial_value=10_000.0, horizon_years=1.0)
    assert 0.0 <= s.probability_of_loss <= 1.0


def test_summarize_distribution_known_values():
    # All sims terminate at exactly 2x the initial — every simulation is a win.
    terminals = np.full(1000, 20_000.0)
    s = summarize_distribution(terminals, initial_value=10_000.0, horizon_years=1.0)
    assert s.expected_value == pytest.approx(20_000.0)
    assert s.median_value == pytest.approx(20_000.0)
    assert s.probability_of_loss == 0.0
    # ddof=1 std on identical values is 0.
    assert s.annualized_volatility == pytest.approx(0.0, abs=1e-9)
    assert s.expected_return == pytest.approx(np.log(2.0), rel=1e-9)


def test_summarize_distribution_loss_probability_correct():
    # Half above, half below initial.
    terminals = np.array([5_000.0] * 500 + [15_000.0] * 500)
    s = summarize_distribution(terminals, initial_value=10_000.0, horizon_years=1.0)
    assert s.probability_of_loss == pytest.approx(0.5)


def test_summarize_distribution_validates_input():
    with pytest.raises(ValueError):
        summarize_distribution(np.array([]), 100.0, 1.0)
    with pytest.raises(ValueError):
        summarize_distribution(np.array([100.0]), 0.0, 1.0)
    with pytest.raises(ValueError):
        summarize_distribution(np.array([100.0]), 100.0, 0.0)
    with pytest.raises(ValueError):
        summarize_distribution(np.array([[100.0]]), 100.0, 1.0)


def test_select_sample_paths_includes_extremes():
    rng = np.random.default_rng(0)
    paths = rng.uniform(50, 200, size=(500, 11))
    paths[:, 0] = 100.0
    sampled, labels = select_sample_paths(paths, n_sample=20)
    assert sampled.shape == (20, 11)
    assert "worst" in labels
    assert "best" in labels
    assert "median" in labels


def test_select_sample_paths_labels_correct():
    paths = np.array(
        [[100, 90], [100, 110], [100, 120], [100, 80], [100, 100]],
        dtype=float,
    )
    # Terminals: 90, 110, 120, 80, 100 → worst=80 (idx 3), best=120 (idx 2), median=100 (idx 4)
    sampled, labels = select_sample_paths(paths, n_sample=5)
    # Worst row should have terminal 80; best 120; median 100.
    worst_row = sampled[labels.index("worst")]
    best_row = sampled[labels.index("best")]
    median_row = sampled[labels.index("median")]
    assert worst_row[-1] == 80.0
    assert best_row[-1] == 120.0
    assert median_row[-1] == 100.0


def test_select_sample_paths_clips_to_available():
    paths = np.array([[100, 90], [100, 110], [100, 120]], dtype=float)
    sampled, _labels = select_sample_paths(paths, n_sample=100)
    assert sampled.shape[0] == 3


def test_select_sample_paths_validates_input():
    with pytest.raises(ValueError):
        select_sample_paths(np.array([1, 2, 3]), 10)
    with pytest.raises(ValueError):
        select_sample_paths(np.empty((0, 5)), 10)


def test_build_histogram_count_sums_to_total():
    rng = np.random.default_rng(0)
    terminals = rng.lognormal(0, 0.3, size=5000)
    bins = build_histogram(terminals, n_bins=50)
    assert len(bins) == 50
    assert sum(b.count for b in bins) == 5000


def test_build_histogram_bin_edges_monotonic():
    terminals = np.linspace(100, 200, 1000)
    bins = build_histogram(terminals, n_bins=10)
    for i, b in enumerate(bins):
        assert b.index == i
        assert b.lower < b.upper
        if i > 0:
            assert bins[i - 1].upper == pytest.approx(b.lower)


def test_build_histogram_validates_input():
    with pytest.raises(ValueError):
        build_histogram(np.array([[1.0]]))
    with pytest.raises(ValueError):
        build_histogram(np.array([1.0, 2.0]), n_bins=0)


def test_prob_beat_benchmark_basic():
    port = np.array([10.0, 20.0, 30.0, 40.0])
    bench = np.array([15.0, 15.0, 15.0, 15.0])
    # 3 of 4 wins (20, 30, 40 > 15).
    assert prob_beat_benchmark(port, bench) == pytest.approx(0.75)


def test_prob_beat_benchmark_shape_check():
    with pytest.raises(ValueError):
        prob_beat_benchmark(np.array([1.0, 2.0]), np.array([1.0, 2.0, 3.0]))


def test_prob_beat_benchmark_unit_interval():
    rng = np.random.default_rng(0)
    a = rng.normal(100, 20, size=1000)
    b = rng.normal(100, 20, size=1000)
    p = prob_beat_benchmark(a, b)
    assert 0.0 <= p <= 1.0
