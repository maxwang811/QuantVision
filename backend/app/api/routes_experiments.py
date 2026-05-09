from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.experiments import (
    ExperimentCompareOut,
    ExperimentCompareRequest,
    ExperimentListOut,
    ExperimentSweepCreate,
    ExperimentSweepOut,
    ExperimentSweepRunOut,
    ExperimentSweepRunsOut,
)
from app.services.experiments import (
    compare_experiments,
    create_and_run_sweep,
    get_sweep_or_404,
    list_experiment_summaries,
    list_sweep_runs,
)

router = APIRouter()


@router.get("/experiments", response_model=ExperimentListOut)
def list_experiments(
    kind: Literal["backtest", "forecast", "model_run", "sweep"] | None = Query(
        default=None
    ),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ExperimentListOut:
    items, total = list_experiment_summaries(
        db, kind=kind, status=status, q=q, limit=limit, offset=offset
    )
    return ExperimentListOut(items=items, total=total, limit=limit, offset=offset)


@router.post("/experiments/compare", response_model=ExperimentCompareOut)
def compare(req: ExperimentCompareRequest, db: Session = Depends(get_db)) -> ExperimentCompareOut:
    return compare_experiments(db, req)


@router.post("/experiment-sweeps", response_model=ExperimentSweepOut)
def create_sweep(
    req: ExperimentSweepCreate, db: Session = Depends(get_db)
) -> ExperimentSweepOut:
    sweep = create_and_run_sweep(db, req)
    return ExperimentSweepOut.model_validate(sweep)


@router.get("/experiment-sweeps/{sweep_id}", response_model=ExperimentSweepOut)
def get_sweep(sweep_id: UUID, db: Session = Depends(get_db)) -> ExperimentSweepOut:
    sweep = get_sweep_or_404(db, sweep_id)
    return ExperimentSweepOut.model_validate(sweep)


@router.get("/experiment-sweeps/{sweep_id}/runs", response_model=ExperimentSweepRunsOut)
def get_sweep_runs(sweep_id: UUID, db: Session = Depends(get_db)) -> ExperimentSweepRunsOut:
    runs = list_sweep_runs(db, sweep_id)
    return ExperimentSweepRunsOut(
        sweep_id=sweep_id,
        runs=[ExperimentSweepRunOut.model_validate(run) for run in runs],
    )
