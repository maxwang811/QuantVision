"""Runner: validation + DB lookup for portfolio optimization.

Stateless — no rows persisted. Mirrors the shape of forecast/runner.py for
consistency.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.models.asset import Asset
from app.models.price import PriceHistory
from app.schemas.optimization import OptimizationRequest
from app.services.data.returns import build_log_returns_matrix
from app.services.optimization.optimizer import (
    OptimizationResult,
    optimize_portfolio,
)

_TRADING_DAYS_PER_YEAR = 252


def run_optimization(db: Session, req: OptimizationRequest) -> tuple[
    OptimizationResult, date, date
]:
    """Validate tickers, fetch lookback prices, compute log-returns, optimize.

    Returns (result, lookback_start, lookback_end).
    """
    asset_map = _load_assets(db, req.tickers)
    assets = [asset_map[t] for t in req.tickers]

    as_of_date = req.as_of_date or _latest_common_price_date(db, assets)
    if as_of_date is None:
        raise ValidationError(
            "no overlapping price coverage across the requested tickers",
            code="insufficient_history",
        )

    lookback_start_calendar = as_of_date - _calendar_days_for_lookback(req.lookback_days)
    returns_matrix, common_dates = build_log_returns_matrix(
        db, assets, lookback_start_calendar, as_of_date
    )
    min_required = max(req.lookback_days // 2, len(req.tickers) + 5)
    if returns_matrix.shape[0] < min_required:
        raise ValidationError(
            f"insufficient overlapping history: got {returns_matrix.shape[0]} return "
            f"observations, need at least {min_required}",
            code="insufficient_history",
        )

    try:
        result = optimize_portfolio(
            returns_matrix,
            tickers=list(req.tickers),
            risk_free_rate=req.risk_free_rate,
            target_return=req.target_return,
            n_frontier_points=req.n_frontier_points,
        )
    except ValueError as e:
        raise ValidationError(str(e), code="optimization_failed") from e

    return result, common_dates[0], common_dates[-1]


# ---------------------------------------------------------------------------
# Internal helpers (mirror forecast/runner.py)
# ---------------------------------------------------------------------------


def _load_assets(db: Session, tickers: list[str]) -> dict[str, Asset]:
    rows = list(db.scalars(select(Asset).where(Asset.ticker.in_(tickers))))
    found = {a.ticker: a for a in rows}
    missing = [t for t in tickers if t not in found]
    if missing:
        raise ValidationError(
            f"unknown tickers: {', '.join(missing)}", code="unknown_tickers"
        )
    return found


def _calendar_days_for_lookback(lookback_days: int) -> timedelta:
    return timedelta(days=int(lookback_days * 365 / 252) + 30)


def _latest_common_price_date(db: Session, assets: list[Asset]) -> date | None:
    if not assets:
        return None
    latest_dates = []
    for asset in assets:
        d = db.scalar(
            select(func.max(PriceHistory.date)).where(PriceHistory.asset_id == asset.id)
        )
        if d is None:
            return None
        latest_dates.append(d)
    return min(latest_dates)
