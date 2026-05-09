"""Seed the assets table with a curated list of liquid US tickers + major ETFs.

Idempotent: existing tickers are left as-is; new ones are inserted.

Run: python scripts/seed_assets.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.dialects.postgresql import insert

from app.core.logging import configure_logging
from app.db import SessionLocal
from app.models.asset import Asset

log = logging.getLogger(__name__)

ETFS: list[tuple[str, str, str]] = [
    ("SPY", "SPDR S&P 500 ETF Trust", "etf"),
    ("QQQ", "Invesco QQQ Trust (Nasdaq-100)", "etf"),
    ("DIA", "SPDR Dow Jones Industrial Average ETF", "etf"),
    ("IWM", "iShares Russell 2000 ETF", "etf"),
    ("VTI", "Vanguard Total Stock Market ETF", "etf"),
    ("AGG", "iShares Core US Aggregate Bond ETF", "etf"),
    ("TLT", "iShares 20+ Year Treasury Bond ETF", "etf"),
    ("GLD", "SPDR Gold Shares", "etf"),
    ("XLK", "Technology Select Sector SPDR", "etf"),
    ("XLF", "Financial Select Sector SPDR", "etf"),
    ("XLE", "Energy Select Sector SPDR", "etf"),
    ("XLV", "Health Care Select Sector SPDR", "etf"),
    ("VNQ", "Vanguard Real Estate ETF", "etf"),
    ("EFA", "iShares MSCI EAFE ETF", "etf"),
    ("EEM", "iShares MSCI Emerging Markets ETF", "etf"),
]

EQUITIES: list[tuple[str, str]] = [
    ("AAPL", "Apple Inc."),
    ("MSFT", "Microsoft Corporation"),
    ("GOOGL", "Alphabet Inc. Class A"),
    ("AMZN", "Amazon.com Inc."),
    ("NVDA", "NVIDIA Corporation"),
    ("META", "Meta Platforms Inc."),
    ("TSLA", "Tesla Inc."),
    ("BRK-B", "Berkshire Hathaway Inc. Class B"),
    ("JPM", "JPMorgan Chase & Co."),
    ("V", "Visa Inc."),
    ("MA", "Mastercard Incorporated"),
    ("UNH", "UnitedHealth Group Incorporated"),
    ("HD", "The Home Depot Inc."),
    ("PG", "Procter & Gamble Company"),
    ("XOM", "Exxon Mobil Corporation"),
    ("CVX", "Chevron Corporation"),
    ("KO", "The Coca-Cola Company"),
    ("PEP", "PepsiCo Inc."),
    ("WMT", "Walmart Inc."),
    ("COST", "Costco Wholesale Corporation"),
    ("DIS", "The Walt Disney Company"),
    ("NFLX", "Netflix Inc."),
    ("ADBE", "Adobe Inc."),
    ("CRM", "Salesforce Inc."),
    ("ORCL", "Oracle Corporation"),
    ("AMD", "Advanced Micro Devices Inc."),
    ("INTC", "Intel Corporation"),
    ("CSCO", "Cisco Systems Inc."),
    ("PFE", "Pfizer Inc."),
    ("MRK", "Merck & Co. Inc."),
    ("ABBV", "AbbVie Inc."),
    ("LLY", "Eli Lilly and Company"),
    ("BAC", "Bank of America Corporation"),
    ("WFC", "Wells Fargo & Company"),
    ("GS", "The Goldman Sachs Group Inc."),
    ("MS", "Morgan Stanley"),
    ("BA", "The Boeing Company"),
    ("CAT", "Caterpillar Inc."),
    ("GE", "General Electric Company"),
    ("F", "Ford Motor Company"),
    ("GM", "General Motors Company"),
    ("NKE", "NIKE Inc."),
    ("MCD", "McDonald's Corporation"),
    ("SBUX", "Starbucks Corporation"),
    ("BKNG", "Booking Holdings Inc."),
    ("UBER", "Uber Technologies Inc."),
    ("PYPL", "PayPal Holdings Inc."),
    ("SHOP", "Shopify Inc."),
    ("SQ", "Block Inc."),
    ("ABNB", "Airbnb Inc."),
]


def main() -> None:
    configure_logging()
    rows: list[dict] = []
    for ticker, name, asset_class in ETFS:
        rows.append({"ticker": ticker, "name": name, "asset_class": asset_class, "currency": "USD"})
    for ticker, name in EQUITIES:
        rows.append({"ticker": ticker, "name": name, "asset_class": "equity", "currency": "USD"})

    with SessionLocal() as db:
        stmt = insert(Asset.__table__).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["ticker"])
        result = db.execute(stmt)
        db.commit()
        log.info("Seeded %d new assets (total provided: %d)", result.rowcount or 0, len(rows))


if __name__ == "__main__":
    main()
