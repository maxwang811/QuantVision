"""Runner: validation, persistence, orchestration.

The only layer that touches the DB. The engine is pure; the runner wraps it
in a transaction lifecycle, persists trades and daily portfolio values, and
records the final result on the `backtests` row.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.core.time import trading_days
from app.models.asset import Asset
from app.models.backtest import Backtest
from app.models.portfolio_value import PortfolioValue
from app.models.price import PriceHistory
from app.models.trade import Trade
from app.schemas.backtest import BacktestCreate
from app.services.backtest import engine
from app.services.backtest.context import PriceBar
from app.services.backtest.strategies import build_strategy
from app.services.data.price_repo import earliest_price_date, latest_price_date

log = logging.getLogger(__name__)

PRE_BUFFER_DAYS = 14


def run_backtest(db: Session, req: BacktestCreate) -> Backtest:
    """Validate, run, persist. Always returns a Backtest row (status reflects outcome)."""
    asset_map = _validate(db, req)

    prices_master = _load_prices(
        db, asset_map, req.start_date - timedelta(days=PRE_BUFFER_DAYS), req.end_date
    )

    backtest = Backtest(
        id=uuid.uuid4(),
        name=req.name,
        strategy=req.strategy,
        params={"target_weights": dict(zip(req.tickers, req.weights, strict=True))},
        initial_cash=Decimal(str(req.initial_cash)),
        start_date=req.start_date,
        end_date=req.end_date,
        benchmark_ticker=req.benchmark_ticker,
        transaction_cost_bps=req.transaction_cost_bps,
        status="running",
    )
    db.add(backtest)
    db.commit()

    try:
        target_weights = dict(zip(req.tickers, req.weights, strict=True))
        strategy = build_strategy(req.strategy, {"target_weights": target_weights})

        result = engine.run(
            start_date=req.start_date,
            end_date=req.end_date,
            prices_master=prices_master,
            strategy=strategy,
            initial_cash=req.initial_cash,
            transaction_cost_bps=req.transaction_cost_bps,
        )

        _persist_trades(db, backtest.id, result.fills, asset_map)
        _persist_portfolio_values(db, backtest.id, result.daily_values)

        final_value = result.daily_values[-1].total_value
        total_return = (final_value - req.initial_cash) / req.initial_cash
        backtest.final_value = Decimal(str(final_value))
        backtest.total_return = Decimal(str(total_return))
        backtest.status = "completed"
        backtest.completed_at = _utc_now(db)
    except Exception as e:
        log.exception("backtest %s failed", backtest.id)
        backtest.status = "failed"
        backtest.error_message = str(e)[:1000]
    finally:
        db.commit()
        db.refresh(backtest)

    return backtest


def _validate(db: Session, req: BacktestCreate) -> dict[str, Asset]:
    """Returns ticker → Asset map for the validated input."""
    rows = list(
        db.scalars(select(Asset).where(Asset.ticker.in_(req.tickers)))
    )
    found = {a.ticker: a for a in rows}
    missing = [t for t in req.tickers if t not in found]
    if missing:
        raise ValidationError(
            f"unknown tickers: {', '.join(missing)}", code="unknown_tickers"
        )

    insufficient: list[str] = []
    for ticker in req.tickers:
        asset = found[ticker]
        earliest = earliest_price_date(db, asset.id)
        latest = latest_price_date(db, asset.id)
        if (
            earliest is None
            or latest is None
            or earliest > req.start_date
            or latest < req.end_date
        ):
            insufficient.append(ticker)
    if insufficient:
        raise ValidationError(
            f"insufficient price coverage for: {', '.join(insufficient)}",
            code="insufficient_coverage",
        )

    if req.benchmark_ticker and req.benchmark_ticker not in found:
        log.warning(
            "benchmark_ticker %s has no asset row; persisting anyway "
            "(Stage 3 will require coverage)",
            req.benchmark_ticker,
        )

    if len(trading_days(req.start_date, req.end_date)) < 2:
        raise ValidationError(
            "backtest window must span at least 2 trading days",
            code="window_too_short",
        )

    return found


def _load_prices(
    db: Session,
    asset_map: dict[str, Asset],
    fetch_start: date,
    fetch_end: date,
) -> dict[str, list[PriceBar]]:
    """Pull adj_close series for each ticker, including pre-buffer for forward-fill."""
    asset_ids = [a.id for a in asset_map.values()]
    rows = list(
        db.scalars(
            select(PriceHistory)
            .where(PriceHistory.asset_id.in_(asset_ids))
            .where(PriceHistory.date >= fetch_start)
            .where(PriceHistory.date <= fetch_end)
            .order_by(PriceHistory.date)
        )
    )
    id_to_ticker = {a.id: t for t, a in asset_map.items()}
    out: dict[str, list[PriceBar]] = {t: [] for t in asset_map}
    for r in rows:
        out[id_to_ticker[r.asset_id]].append(PriceBar(r.date, float(r.adj_close)))
    return out


def _persist_trades(
    db: Session,
    backtest_id: uuid.UUID,
    fills: list,
    asset_map: dict[str, Asset],
) -> None:
    if not fills:
        return
    payload = [
        {
            "id": uuid.uuid4(),
            "backtest_id": backtest_id,
            "asset_id": asset_map[f.ticker].id,
            "date": f.date,
            "side": f.side,
            "quantity": Decimal(str(f.quantity)),
            "price": Decimal(str(f.price)),
            "transaction_cost": Decimal(str(f.transaction_cost)),
            "notional": Decimal(str(f.notional)),
        }
        for f in fills
    ]
    db.execute(Trade.__table__.insert(), payload)


def _persist_portfolio_values(
    db: Session, backtest_id: uuid.UUID, daily_values: list
) -> None:
    if not daily_values:
        return
    payload = [
        {
            "backtest_id": backtest_id,
            "date": dv.date,
            "cash": Decimal(str(dv.cash)),
            "holdings_value": Decimal(str(dv.holdings_value)),
            "total_value": Decimal(str(dv.total_value)),
        }
        for dv in daily_values
    ]
    db.execute(PortfolioValue.__table__.insert(), payload)


def _utc_now(db: Session):
    """Wall-clock timestamp via the DB so timezone semantics match `created_at`."""
    return db.scalar(select(func.now()))
