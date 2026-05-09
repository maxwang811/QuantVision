from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db import get_db
from app.models.asset import Asset
from app.models.backtest import Backtest
from app.models.portfolio_value import PortfolioValue
from app.models.trade import Trade
from app.schemas.backtest import (
    BacktestCreate,
    BacktestEquityCurveOut,
    BacktestOut,
    BacktestTradesOut,
    PortfolioValuePoint,
    TradeOut,
)
from app.services.backtest.runner import run_backtest

router = APIRouter()


def _get_backtest_or_404(db: Session, backtest_id: UUID) -> Backtest:
    bt = db.get(Backtest, backtest_id)
    if bt is None:
        raise NotFoundError(f"backtest not found: {backtest_id}")
    return bt


@router.post("/backtests", response_model=BacktestOut)
def create_backtest(req: BacktestCreate, db: Session = Depends(get_db)) -> BacktestOut:
    """Run a backtest synchronously and return the result.

    Validates input, persists a row with `status='running'`, runs the engine
    inline, persists trades + daily portfolio values, and returns the completed
    record. On failure, returns a row with `status='failed'` and `error_message`.
    """
    bt = run_backtest(db, req)
    return BacktestOut.model_validate(bt)


@router.get("/backtests/{backtest_id}", response_model=BacktestOut)
def get_backtest(backtest_id: UUID, db: Session = Depends(get_db)) -> BacktestOut:
    bt = _get_backtest_or_404(db, backtest_id)
    return BacktestOut.model_validate(bt)


@router.get("/backtests/{backtest_id}/trades", response_model=BacktestTradesOut)
def get_backtest_trades(
    backtest_id: UUID, db: Session = Depends(get_db)
) -> BacktestTradesOut:
    _get_backtest_or_404(db, backtest_id)
    rows = list(
        db.execute(
            select(Trade, Asset.ticker)
            .join(Asset, Asset.id == Trade.asset_id)
            .where(Trade.backtest_id == backtest_id)
            .order_by(Trade.date, Trade.id)
        )
    )
    trades = [
        TradeOut(
            id=t.id,
            date=t.date,
            ticker=ticker,
            side=t.side,
            quantity=float(t.quantity),
            price=float(t.price),
            transaction_cost=float(t.transaction_cost),
            notional=float(t.notional),
        )
        for t, ticker in rows
    ]
    return BacktestTradesOut(backtest_id=backtest_id, trades=trades)


@router.get(
    "/backtests/{backtest_id}/portfolio_values",
    response_model=BacktestEquityCurveOut,
)
def get_backtest_portfolio_values(
    backtest_id: UUID, db: Session = Depends(get_db)
) -> BacktestEquityCurveOut:
    _get_backtest_or_404(db, backtest_id)
    rows = list(
        db.scalars(
            select(PortfolioValue)
            .where(PortfolioValue.backtest_id == backtest_id)
            .order_by(PortfolioValue.date)
        )
    )
    points = [
        PortfolioValuePoint(
            date=r.date,
            cash=float(r.cash),
            holdings_value=float(r.holdings_value),
            total_value=float(r.total_value),
        )
        for r in rows
    ]
    return BacktestEquityCurveOut(backtest_id=backtest_id, points=points)
