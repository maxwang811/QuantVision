"""Idempotent yfinance → Postgres price ingestion.

Strategy: for each ticker, if stored coverage already spans the requested
[start, end] window, short-circuit. Otherwise fetch the full requested
window from yfinance and upsert via INSERT ... ON CONFLICT DO UPDATE — the
(asset_id, date) unique index handles dupes, so re-ingesting is safe and
historical backfill works symmetrically with forward extension.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.price import PriceHistory
from app.services.data.price_repo import (
    earliest_price_date,
    get_asset_by_ticker,
    latest_price_date,
)
from app.services.data.yfinance_client import PriceFetcher, YFinanceClient

log = logging.getLogger(__name__)


@dataclass
class IngestResult:
    ticker: str
    rows_upserted: int
    range_start: date | None
    range_end: date | None
    skipped_existing: bool = False


def ingest_ticker(
    db: Session,
    ticker: str,
    start: date,
    end: date,
    *,
    fetcher: PriceFetcher | None = None,
    overlap_days: int = 5,
) -> IngestResult:
    fetcher = fetcher or YFinanceClient()
    ticker = ticker.upper()

    asset = get_asset_by_ticker(db, ticker)
    if asset is None:
        asset = Asset(ticker=ticker, asset_class="equity", currency="USD")
        db.add(asset)
        db.flush()

    last_date = latest_price_date(db, asset.id)
    first_date = earliest_price_date(db, asset.id)

    if (
        first_date is not None
        and last_date is not None
        and first_date <= start
        and last_date >= end
    ):
        return IngestResult(
            ticker=ticker,
            rows_upserted=0,
            range_start=first_date,
            range_end=last_date,
            skipped_existing=True,
        )

    fetch_start = start
    fetch_end = end

    df = fetcher.fetch(ticker, fetch_start, fetch_end)
    rows = _frame_to_rows(asset.id, df)
    if not rows:
        return IngestResult(ticker=ticker, rows_upserted=0, range_start=None, range_end=None)

    n = _upsert(db, rows)
    return IngestResult(
        ticker=ticker,
        rows_upserted=n,
        range_start=rows[0]["date"],
        range_end=rows[-1]["date"],
    )


def _frame_to_rows(asset_id, df: pd.DataFrame) -> list[dict]:
    rows: list[dict] = []
    for ts, row in df.iterrows():
        rows.append(
            {
                "asset_id": asset_id,
                "date": pd.Timestamp(ts).date(),
                "open": _f(row.get("open")),
                "high": _f(row.get("high")),
                "low": _f(row.get("low")),
                "close": _f(row.get("close")),
                "adj_close": _f(row["adj_close"]),
                "volume": _i(row.get("volume")),
            }
        )
    return rows


def _f(v) -> float | None:
    if v is None or pd.isna(v):
        return None
    return float(v)


def _i(v) -> int | None:
    if v is None or pd.isna(v):
        return None
    return int(v)


def _upsert(db: Session, rows: list[dict]) -> int:
    stmt = insert(PriceHistory.__table__).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["asset_id", "date"],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "adj_close": stmt.excluded.adj_close,
            "volume": stmt.excluded.volume,
        },
    )
    db.execute(stmt)
    db.commit()
    return len(rows)


__all__ = ["IngestResult", "ingest_ticker"]
