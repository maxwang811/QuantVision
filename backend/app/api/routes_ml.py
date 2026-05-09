from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db import get_db
from app.models.asset import Asset
from app.models.model_prediction import ModelPrediction
from app.schemas.ml import (
    ModelPredictionOut,
    ModelPredictionsOut,
    ModelRunCreate,
    ModelRunOut,
)
from app.services.ml.runner import get_model_run_or_404, run_model_training

router = APIRouter()


@router.post("/model-runs", response_model=ModelRunOut)
def create_model_run(req: ModelRunCreate, db: Session = Depends(get_db)) -> ModelRunOut:
    run = run_model_training(db, req)
    return ModelRunOut.model_validate(run)


@router.get("/model-runs/{model_run_id}", response_model=ModelRunOut)
def get_model_run(model_run_id: UUID, db: Session = Depends(get_db)) -> ModelRunOut:
    run = get_model_run_or_404(db, model_run_id)
    return ModelRunOut.model_validate(run)


@router.get("/model-runs/{model_run_id}/predictions", response_model=ModelPredictionsOut)
def get_model_predictions(
    model_run_id: UUID,
    model_name: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ModelPredictionsOut:
    run = get_model_run_or_404(db, model_run_id)
    if model_name is not None and model_name not in {"logistic_regression", "xgboost"}:
        raise ValidationError(f"unknown model_name: {model_name}", code="unknown_model")

    stmt = (
        select(ModelPrediction, Asset.ticker)
        .join(Asset, Asset.id == ModelPrediction.asset_id)
        .where(ModelPrediction.model_run_id == run.id)
    )
    if model_name is not None:
        stmt = stmt.where(ModelPrediction.model_name == model_name)
    rows = list(
        db.execute(
            stmt.order_by(
                ModelPrediction.date,
                ModelPrediction.model_name,
                ModelPrediction.rank,
            )
        )
    )
    predictions = [
        ModelPredictionOut(
            id=p.id,
            date=p.date,
            ticker=ticker,
            model_name=p.model_name,
            score=float(p.score),
            rank=p.rank,
            label=p.label,
            forward_return=float(p.forward_return) if p.forward_return is not None else None,
            benchmark_forward_return=(
                float(p.benchmark_forward_return)
                if p.benchmark_forward_return is not None
                else None
            ),
        )
        for p, ticker in rows
    ]
    return ModelPredictionsOut(model_run_id=run.id, predictions=predictions)
