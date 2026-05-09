"""Thin wrapper around yfinance with retry + backoff and a normalized output frame."""

from __future__ import annotations

import logging
from datetime import date
from typing import Protocol

import pandas as pd
import yfinance as yf
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.errors import UpstreamError

log = logging.getLogger(__name__)

EXPECTED_COLUMNS = ["open", "high", "low", "close", "adj_close", "volume"]


class PriceFetcher(Protocol):
    """Anything that returns a yfinance-shaped DataFrame for tests to substitute."""

    def fetch(self, ticker: str, start: date, end: date) -> pd.DataFrame: ...


class YFinanceClient:
    """Production fetcher backed by yfinance.

    The yfinance library can return:
      * Empty frames (silent failure on bad ticker)
      * MultiIndex columns when group_by='ticker'
      * Single-level columns: Open/High/Low/Close/Adj Close/Volume

    We normalize to lowercase snake_case and drop rows without adj_close.
    """

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def fetch(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        log.info("yfinance fetch %s %s..%s", ticker, start, end)
        try:
            df = yf.download(
                ticker,
                start=start.isoformat(),
                end=end.isoformat(),
                progress=False,
                auto_adjust=False,
                actions=False,
                threads=False,
            )
        except (ConnectionError, TimeoutError):
            # Let tenacity retry; do not wrap.
            raise
        except Exception as exc:  # yfinance raises a grab bag of types
            raise UpstreamError(f"yfinance failed for {ticker}: {exc}") from exc

        if df is None or df.empty:
            raise UpstreamError(f"yfinance returned no data for {ticker}")

        return _normalize(df)


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase columns, snake_case, ensure adj_close is present, drop rows missing it."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)

    rename = {}
    for c in df.columns:
        col = str(c).strip().lower().replace(" ", "_")
        rename[c] = col
    df = df.rename(columns=rename)

    if "adj_close" not in df.columns and "adjclose" in df.columns:
        df = df.rename(columns={"adjclose": "adj_close"})

    if "adj_close" not in df.columns:
        raise UpstreamError("yfinance frame missing adj_close column")

    keep = [c for c in EXPECTED_COLUMNS if c in df.columns]
    df = df[keep]
    df = df.dropna(subset=["adj_close"])
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


__all__ = ["PriceFetcher", "RetryError", "YFinanceClient"]
