from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.optimization import (
    FrontierPointOut,
    OptimizationRequest,
    OptimizationResultOut,
)
from app.services.optimization.optimizer import FrontierPoint
from app.services.optimization.runner import run_optimization

router = APIRouter()


@router.post("/optimize", response_model=OptimizationResultOut)
def create_optimization(
    req: OptimizationRequest, db: Session = Depends(get_db)
) -> OptimizationResultOut:
    """Run mean-variance + max-Sharpe portfolio optimization synchronously.

    Stateless: no rows are persisted. Errors raised by the runner become 422
    via the global handler.
    """
    result, lookback_start, lookback_end = run_optimization(db, req)
    return OptimizationResultOut(
        tickers=result.tickers,
        risk_free_rate=result.risk_free_rate,
        n_observations=result.n_observations,
        lookback_start=lookback_start,
        lookback_end=lookback_end,
        min_variance=_to_out(result.min_variance),
        max_sharpe=_to_out(result.max_sharpe),
        target_return=_to_out(result.target_return) if result.target_return else None,
        frontier=[_to_out(p) for p in result.frontier],
    )


def _to_out(p: FrontierPoint) -> FrontierPointOut:
    return FrontierPointOut(
        expected_return=p.ret,
        volatility=p.vol,
        sharpe_ratio=p.sharpe,
        weights=[float(w) for w in p.weights],
    )
