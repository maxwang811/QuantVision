"""Pull historical OHLCV from yfinance into Postgres.

Run:
    python scripts/ingest_prices.py --tickers SPY,AAPL,MSFT --years 5
    python scripts/ingest_prices.py --all --years 10
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.core.errors import UpstreamError
from app.core.logging import configure_logging
from app.db import SessionLocal
from app.models.asset import Asset
from app.services.data.ingest import ingest_ticker

log = logging.getLogger(__name__)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ingest historical prices from yfinance.")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--tickers", help="Comma-separated tickers, e.g. SPY,AAPL")
    g.add_argument("--all", action="store_true", help="Ingest every asset in the DB")
    p.add_argument("--years", type=int, default=5, help="Lookback window in years (default 5)")
    p.add_argument("--end", help="End date YYYY-MM-DD (default: today)")
    return p.parse_args(argv)


def resolve_tickers(args: argparse.Namespace) -> list[str]:
    if args.all:
        with SessionLocal() as db:
            return [t for (t,) in db.execute(select(Asset.ticker).order_by(Asset.ticker))]
    return [t.strip().upper() for t in args.tickers.split(",") if t.strip()]


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = parse_args(argv)

    end_date = date.fromisoformat(args.end) if args.end else date.today()
    start_date = end_date - timedelta(days=args.years * 365 + 30)

    tickers = resolve_tickers(args)
    log.info("Ingesting %d tickers from %s to %s", len(tickers), start_date, end_date)

    failures: list[tuple[str, str]] = []
    total_rows = 0

    with SessionLocal() as db:
        for ticker in tickers:
            try:
                result = ingest_ticker(db, ticker, start_date, end_date)
            except UpstreamError as exc:
                log.warning("Failed %s: %s", ticker, exc)
                failures.append((ticker, str(exc)))
                continue
            log.info(
                "  %s: upserted=%d range=%s..%s%s",
                ticker,
                result.rows_upserted,
                result.range_start,
                result.range_end,
                " (no-op)" if result.skipped_existing else "",
            )
            total_rows += result.rows_upserted

    log.info("Done: %d rows upserted across %d tickers, %d failures", total_rows, len(tickers), len(failures))
    if failures:
        log.warning("Failures: %s", failures)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
