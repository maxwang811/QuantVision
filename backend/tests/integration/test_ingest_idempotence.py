"""End-to-end ingest idempotence test against a real Postgres.

Skipped unless QV_TEST_DATABASE_URL points at a Postgres instance.
Run with:
    QV_TEST_DATABASE_URL=postgresql+psycopg://... pytest tests/integration -m integration
"""

from __future__ import annotations

import os
from datetime import date

import pandas as pd
import pytest
from sqlalchemy import select

from app.models.price import PriceHistory
from app.services.data.ingest import ingest_ticker

pytestmark = pytest.mark.integration

if "postgres" not in os.getenv("QV_TEST_DATABASE_URL", ""):
    pytest.skip("integration tests require Postgres", allow_module_level=True)


class StaticFetcher:
    def __init__(self, frame: pd.DataFrame):
        self.frame = frame
        self.calls = 0

    def fetch(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        self.calls += 1
        return self.frame


def _make_frame() -> pd.DataFrame:
    idx = pd.date_range("2024-01-02", periods=5, freq="B")
    return pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "high": [101.0, 102.0, 103.0, 104.0, 105.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "close": [100.5, 101.5, 102.5, 103.5, 104.5],
            "adj_close": [100.5, 101.5, 102.5, 103.5, 104.5],
            "volume": [1000, 1100, 1200, 1300, 1400],
        },
        index=idx,
    )


def test_ingest_is_idempotent(db):
    """Running ingest twice with the same data yields the same row count."""
    frame = _make_frame()
    fetcher = StaticFetcher(frame)

    r1 = ingest_ticker(db, "TEST", date(2024, 1, 1), date(2024, 2, 1), fetcher=fetcher)
    assert r1.rows_upserted == 5
    n1 = db.scalar(select(PriceHistory).where(PriceHistory.adj_close == 100.5))
    assert n1 is not None

    # Second run on same range — rows are upserted but count of distinct rows stays 5.
    r2 = ingest_ticker(db, "TEST", date(2024, 1, 1), date(2024, 2, 1), fetcher=fetcher)
    rows = list(db.scalars(select(PriceHistory)))
    assert len(rows) == 5
    assert r2.rows_upserted >= 0  # equal-valued upsert may report 0 or len(rows)


def test_ingest_updates_existing_rows_on_conflict(db):
    """Upsert behavior: re-ingesting a date with a new adj_close updates the row."""
    fetcher_v1 = StaticFetcher(_make_frame())
    ingest_ticker(db, "TEST", date(2024, 1, 1), date(2024, 2, 1), fetcher=fetcher_v1)

    revised = _make_frame().copy()
    revised["adj_close"] = revised["adj_close"] * 1.10

    fetcher_v2 = StaticFetcher(revised)
    ingest_ticker(db, "TEST", date(2024, 1, 1), date(2024, 2, 1), fetcher=fetcher_v2)

    rows = sorted(db.scalars(select(PriceHistory)), key=lambda r: r.date)
    assert pytest.approx(float(rows[0].adj_close), rel=1e-6) == 100.5 * 1.10
