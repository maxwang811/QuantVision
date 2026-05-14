"""Unit tests for the ingest pipeline.

The actual upsert uses Postgres-specific INSERT ... ON CONFLICT, so the
end-to-end idempotence test lives in tests/integration/. These unit tests
cover the pure-logic pieces: row conversion, the full-coverage short-circuit,
and the backfill case where the DB is missing earlier history.
"""

from __future__ import annotations

from datetime import date

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


def test_ingest_skips_when_coverage_already_spans_window(monkeypatch, sample_frame):
    """If stored [earliest, latest] already spans [start, end], fetcher is never called."""
    fake_asset = type("A", (), {"id": "abc", "ticker": "FOO"})()
    monkeypatch.setattr(ingest_module, "get_asset_by_ticker", lambda db, t: fake_asset)
    monkeypatch.setattr(ingest_module, "latest_price_date", lambda db, _id: date(2025, 1, 10))
    monkeypatch.setattr(ingest_module, "earliest_price_date", lambda db, _id: date(2023, 6, 1))

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


def test_ingest_backfills_when_start_is_before_stored_earliest(monkeypatch, sample_frame):
    """Requesting an earlier start than what's stored must trigger a full-window fetch."""
    fake_asset = type("A", (), {"id": "abc", "ticker": "FOO"})()
    monkeypatch.setattr(ingest_module, "get_asset_by_ticker", lambda db, t: fake_asset)
    monkeypatch.setattr(ingest_module, "latest_price_date", lambda db, _id: date(2025, 1, 10))
    monkeypatch.setattr(ingest_module, "earliest_price_date", lambda db, _id: date(2024, 6, 1))
    monkeypatch.setattr(ingest_module, "_upsert", lambda db, rows: len(rows))

    fetcher = FakeFetcher(sample_frame)
    ingest_module.ingest_ticker(
        db=None,
        ticker="FOO",
        start=date(2020, 1, 1),
        end=date(2025, 1, 1),
        fetcher=fetcher,
    )
    assert fetcher.last_call is not None
    assert fetcher.last_call["start"] == date(2020, 1, 1)
    assert fetcher.last_call["end"] == date(2025, 1, 1)


def test_ingest_fetches_full_window_when_db_is_empty(monkeypatch, sample_frame):
    fake_asset = type("A", (), {"id": "abc", "ticker": "FOO"})()
    monkeypatch.setattr(ingest_module, "get_asset_by_ticker", lambda db, t: fake_asset)
    monkeypatch.setattr(ingest_module, "latest_price_date", lambda db, _id: None)
    monkeypatch.setattr(ingest_module, "earliest_price_date", lambda db, _id: None)
    monkeypatch.setattr(ingest_module, "_upsert", lambda db, rows: len(rows))

    fetcher = FakeFetcher(sample_frame)
    ingest_module.ingest_ticker(
        db=None,
        ticker="FOO",
        start=date(2020, 1, 1),
        end=date(2025, 1, 1),
        fetcher=fetcher,
    )
    assert fetcher.last_call is not None
    assert fetcher.last_call["start"] == date(2020, 1, 1)
    assert fetcher.last_call["end"] == date(2025, 1, 1)
