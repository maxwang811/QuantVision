"""Unit tests for the ingest pipeline.

The actual upsert uses Postgres-specific INSERT ... ON CONFLICT, so the
end-to-end idempotence test lives in tests/integration/. These unit tests
cover the pure-logic pieces: row conversion, range narrowing on incremental
fetches, and the skip-existing short-circuit.
"""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import pytest

from app.services.data import ingest as ingest_module


class FakeFetcher:
    """Captures the date range the ingestor asked for."""

    def __init__(self, frame: pd.DataFrame):
        self.frame = frame
        self.last_call: dict | None = None

    def fetch(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        self.last_call = {"ticker": ticker, "start": start, "end": end}
        return self.frame


@pytest.fixture
def sample_frame() -> pd.DataFrame:
    idx = pd.date_range("2024-01-02", periods=3, freq="B")
    return pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "adj_close": [100.5, 101.5, 102.5],
            "volume": [1000, 1100, 1200],
        },
        index=idx,
    )


def test_frame_to_rows_basic(sample_frame):
    asset_id = "00000000-0000-0000-0000-000000000001"
    rows = ingest_module._frame_to_rows(asset_id, sample_frame)
    assert len(rows) == 3
    assert rows[0]["asset_id"] == asset_id
    assert rows[0]["adj_close"] == 100.5
    assert rows[0]["date"] == date(2024, 1, 2)


def test_frame_to_rows_handles_nans(sample_frame):
    df = sample_frame.copy()
    df.iloc[0, df.columns.get_loc("volume")] = pd.NA
    df.iloc[1, df.columns.get_loc("open")] = pd.NA
    rows = ingest_module._frame_to_rows("00000000-0000-0000-0000-000000000001", df)
    assert rows[0]["volume"] is None
    assert rows[1]["open"] is None
    assert rows[1]["adj_close"] == 101.5


def test_ingest_skips_when_already_up_to_date(monkeypatch, sample_frame):
    """If latest_price_date >= requested end, fetcher is never called."""
    fake_asset = type("A", (), {"id": "abc", "ticker": "FOO"})()
    monkeypatch.setattr(ingest_module, "get_asset_by_ticker", lambda db, t: fake_asset)
    monkeypatch.setattr(ingest_module, "latest_price_date", lambda db, _id: date(2025, 1, 10))

    fetcher = FakeFetcher(sample_frame)
    result = ingest_module.ingest_ticker(
        db=None,
        ticker="FOO",
        start=date(2024, 1, 1),
        end=date(2025, 1, 1),
        fetcher=fetcher,
    )
    assert result.skipped_existing is True
    assert result.rows_upserted == 0
    assert fetcher.last_call is None


def test_ingest_narrows_start_to_overlap_window(monkeypatch, sample_frame):
    """If the DB has data through 2024-06-15, we should refetch from 2024-06-10."""
    fake_asset = type("A", (), {"id": "abc", "ticker": "FOO"})()
    monkeypatch.setattr(ingest_module, "get_asset_by_ticker", lambda db, t: fake_asset)
    monkeypatch.setattr(ingest_module, "latest_price_date", lambda db, _id: date(2024, 6, 15))
    monkeypatch.setattr(ingest_module, "_upsert", lambda db, rows: len(rows))

    fetcher = FakeFetcher(sample_frame)
    ingest_module.ingest_ticker(
        db=None,
        ticker="FOO",
        start=date(2024, 1, 1),
        end=date(2024, 7, 1),
        fetcher=fetcher,
        overlap_days=5,
    )
    assert fetcher.last_call is not None
    expected_start = date(2024, 6, 15) - timedelta(days=5)
    assert fetcher.last_call["start"] == expected_start
