"""End-to-end tests for /api/health, /api/assets, /api/prices."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.models.asset import Asset
from app.models.price import PriceHistory


def test_health_returns_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["db"] is True


def test_assets_search_empty_returns_all(client, db):
    db.add_all([Asset(ticker="AAPL", name="Apple"), Asset(ticker="MSFT", name="Microsoft")])
    db.commit()

    r = client.get("/api/assets")
    assert r.status_code == 200
    tickers = {a["ticker"] for a in r.json()}
    assert {"AAPL", "MSFT"}.issubset(tickers)


def test_assets_search_by_ticker_prefix(client, db):
    db.add_all(
        [
            Asset(ticker="AAPL", name="Apple"),
            Asset(ticker="AMZN", name="Amazon"),
            Asset(ticker="MSFT", name="Microsoft"),
        ]
    )
    db.commit()

    r = client.get("/api/assets?q=A")
    assert r.status_code == 200
    tickers = {a["ticker"] for a in r.json()}
    assert tickers == {"AAPL", "AMZN"}


def test_assets_search_by_name_substring(client, db):
    db.add(Asset(ticker="AAPL", name="Apple Inc."))
    db.commit()

    r = client.get("/api/assets?q=apple")
    assert r.status_code == 200
    assert any(a["ticker"] == "AAPL" for a in r.json())


def test_prices_returns_404_for_unknown(client):
    r = client.get("/api/prices/UNKNOWN")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_prices_returns_series(client, db):
    asset = Asset(ticker="AAPL", name="Apple")
    db.add(asset)
    db.flush()
    db.add_all(
        [
            PriceHistory(
                asset_id=asset.id,
                date=date(2024, 1, 2),
                adj_close=Decimal("100.5"),
                close=Decimal("100.5"),
                volume=1000,
            ),
            PriceHistory(
                asset_id=asset.id,
                date=date(2024, 1, 3),
                adj_close=Decimal("101.5"),
                close=Decimal("101.5"),
                volume=1100,
            ),
        ]
    )
    db.commit()

    r = client.get("/api/prices/AAPL")
    assert r.status_code == 200
    payload = r.json()
    assert payload["ticker"] == "AAPL"
    assert len(payload["points"]) == 2
    assert payload["points"][0]["adj_close"] == 100.5
