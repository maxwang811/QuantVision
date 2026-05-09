"""Tests for the yfinance client wrapper.

We don't hit the network — we patch yf.download to return canned frames.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from app.core.errors import UpstreamError
from app.services.data import yfinance_client as yc


@pytest.fixture
def fake_ohlcv_frame() -> pd.DataFrame:
    idx = pd.date_range("2024-01-02", periods=3, freq="B")
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [101.0, 102.0, 103.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [100.5, 101.5, 102.5],
            "Adj Close": [100.5, 101.5, 102.5],
            "Volume": [1000, 1100, 1200],
        },
        index=idx,
    )


def test_normalize_renames_columns(fake_ohlcv_frame):
    out = yc._normalize(fake_ohlcv_frame)
    assert list(out.columns) == ["open", "high", "low", "close", "adj_close", "volume"]
    assert len(out) == 3
    assert out["adj_close"].iloc[0] == 100.5


def test_normalize_drops_na_adj_close(fake_ohlcv_frame):
    df = fake_ohlcv_frame.copy()
    df.loc[df.index[1], "Adj Close"] = pd.NA
    out = yc._normalize(df)
    assert len(out) == 2


def test_normalize_handles_multiindex_columns(fake_ohlcv_frame):
    df = fake_ohlcv_frame.copy()
    df.columns = pd.MultiIndex.from_product([df.columns, ["AAPL"]])
    out = yc._normalize(df)
    assert "adj_close" in out.columns
    assert len(out) == 3


def test_normalize_raises_when_adj_close_missing(fake_ohlcv_frame):
    df = fake_ohlcv_frame.drop(columns=["Adj Close"])
    with pytest.raises(UpstreamError, match="adj_close"):
        yc._normalize(df)


def test_fetch_returns_normalized_frame(monkeypatch, fake_ohlcv_frame):
    monkeypatch.setattr(yc.yf, "download", lambda *a, **kw: fake_ohlcv_frame)
    client = yc.YFinanceClient()
    out = client.fetch("AAPL", date(2024, 1, 1), date(2024, 1, 5))
    assert "adj_close" in out.columns
    assert len(out) == 3


def test_fetch_raises_on_empty_frame(monkeypatch):
    monkeypatch.setattr(yc.yf, "download", lambda *a, **kw: pd.DataFrame())
    client = yc.YFinanceClient()
    with pytest.raises(UpstreamError, match="no data"):
        client.fetch("ZZZZ", date(2024, 1, 1), date(2024, 1, 5))


def test_fetch_retries_on_connection_error(monkeypatch, fake_ohlcv_frame):
    """Tenacity should retry ConnectionError up to 3 attempts before succeeding."""
    calls = {"n": 0}

    def flaky_download(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("transient")
        return fake_ohlcv_frame

    monkeypatch.setattr(yc.yf, "download", flaky_download)
    client = yc.YFinanceClient()
    out = client.fetch("AAPL", date(2024, 1, 1), date(2024, 1, 5))
    assert calls["n"] == 3
    assert len(out) == 3


def test_fetch_wraps_arbitrary_exceptions_as_upstream(monkeypatch):
    def boom(*_a, **_kw):
        raise ValueError("yfinance internal weirdness")

    monkeypatch.setattr(yc.yf, "download", boom)
    client = yc.YFinanceClient()
    with pytest.raises(UpstreamError, match="yfinance failed"):
        client.fetch("AAPL", date(2024, 1, 1), date(2024, 1, 5))
