"""Shared helper for building log-return matrices from persisted price history.

Used by both the forecast runner and the optimization runner. Pulling this into
its own module avoids drift and keeps the DB-touching code in one place per asset.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.price import PriceHistory


def build_log_returns_matrix(
    db: Session,
    assets: list[Asset],
    start: date,
    end: date,
) -> tuple[np.ndarray, list[date]]:
    """Pull adj_close per asset, intersect on common dates, compute log-returns.

    Returns (log_returns shape (T-1, A), common_dates length T).

    Returns (empty, []) when there is no overlap or when prices are degenerate;
    callers should treat that as an "insufficient history" failure.
    """
    asset_ids = [a.id for a in assets]
    rows = list(
        db.scalars(
            select(PriceHistory)
            .where(PriceHistory.asset_id.in_(asset_ids))
            .where(PriceHistory.date >= start)
            .where(PriceHistory.date <= end)
            .order_by(PriceHistory.date)
        )
    )

    by_asset: dict[uuid.UUID, dict[date, float]] = defaultdict(dict)
    for r in rows:
        by_asset[r.asset_id][r.date] = float(r.adj_close)

    if not by_asset or any(a.id not in by_asset for a in assets):
        return np.empty((0, len(assets))), []

    common = set(by_asset[assets[0].id].keys())
    for a in assets[1:]:
        common &= set(by_asset[a.id].keys())
    if not common:
        return np.empty((0, len(assets))), []

    common_dates = sorted(common)
    price_matrix = np.array(
        [[by_asset[a.id][d] for a in assets] for d in common_dates],
        dtype=np.float64,
    )
    if price_matrix.shape[0] < 2 or np.any(price_matrix <= 0):
        return np.empty((0, len(assets))), []
    log_returns = np.diff(np.log(price_matrix), axis=0)
    return log_returns, common_dates
