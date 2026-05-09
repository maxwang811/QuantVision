from __future__ import annotations

from datetime import date

import pytest

from app.core.time import trading_days
from app.services.ml.runner import (
    FeatureRow,
    build_feature_rows,
    monthly_signal_dates,
    walk_forward_predict,
)


def _panel(dates: list[date]) -> dict[str, dict[date, tuple[float, float]]]:
    panel: dict[str, dict[date, tuple[float, float]]] = {"A": {}, "B": {}, "SPY": {}}
    for i, d in enumerate(dates):
        panel["A"][d] = (100.0 * (1.002**i), 1_000_000.0 + i)
        panel["B"][d] = (100.0 * (0.999**i), 900_000.0 + i)
        panel["SPY"][d] = (100.0 * (1.0005**i), 950_000.0 + i)
    return panel


def test_build_feature_rows_aligns_forward_outperformance_label():
    dates = trading_days(date(2023, 1, 2), date(2023, 8, 31))
    rows = build_feature_rows(
        tickers=["A", "B"],
        benchmark_ticker="SPY",
        common_dates=dates,
        price_panel=_panel(dates),
        label_horizon_days=20,
    )

    row = next(r for r in rows if r.ticker == "A" and r.index == 120)
    fill_index = 121
    end_index = 141
    a_start = _panel(dates)["A"][dates[fill_index]][0]
    a_end = _panel(dates)["A"][dates[end_index]][0]
    spy_start = _panel(dates)["SPY"][dates[fill_index]][0]
    spy_end = _panel(dates)["SPY"][dates[end_index]][0]

    assert row.forward_return == pytest.approx(a_end / a_start - 1.0)
    assert row.benchmark_forward_return == pytest.approx(spy_end / spy_start - 1.0)
    assert row.label == 1
    assert row.label_end_index == end_index
    assert row.label_end_date == dates[end_index]


def test_walk_forward_training_ignores_labels_that_end_after_prediction_date():
    dates = trading_days(date(2024, 1, 2), date(2024, 1, 12))
    rows = [
        FeatureRow(
            index=0,
            date=dates[0],
            ticker="A",
            features=(10.0,) * 10,
            label=1,
            label_end_index=4,
            label_end_date=dates[4],
            forward_return=0.2,
            benchmark_forward_return=0.0,
        ),
        FeatureRow(
            index=2,
            date=dates[2],
            ticker="A",
            features=(10.0,) * 10,
            label=None,
            label_end_index=None,
            label_end_date=None,
            forward_return=None,
            benchmark_forward_return=None,
        ),
    ]

    predictions = walk_forward_predict(
        rows=rows,
        signal_dates=[dates[2]],
        tickers=["A"],
        training_lookback_days=20,
        random_seed=1,
    )

    assert {p.model_name for p in predictions} == {"logistic_regression", "xgboost"}
    assert all(p.score == pytest.approx(0.5) for p in predictions)


def test_monthly_signal_dates_includes_first_day_and_month_ends():
    dates = trading_days(date(2024, 1, 2), date(2024, 3, 15))
    signals = monthly_signal_dates(dates)
    assert signals[0] == dates[0]
    assert date(2024, 1, 31) in signals
    assert date(2024, 2, 29) in signals
