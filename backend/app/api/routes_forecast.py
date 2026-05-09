from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.db import get_db
from app.models.forecast_distribution_bin import ForecastDistributionBin
from app.models.forecast_path import ForecastPath
from app.schemas.forecast import (
    ForecastCreate,
    ForecastDistributionBinOut,
    ForecastDistributionOut,
    ForecastOut,
    ForecastPathPoint,
    ForecastPathsOut,
    ForecastPercentiles,
)
from app.services.forecast.runner import (
    compute_step_dates,
    get_forecast_or_404,
    run_forecast,
)

router = APIRouter()


@router.post("/forecasts", response_model=ForecastOut)
def create_forecast(req: ForecastCreate, db: Session = Depends(get_db)) -> ForecastOut:
    """Run a forecast synchronously and return the persisted summary row."""
    fc = run_forecast(db, req)
    return ForecastOut.model_validate(fc)


@router.get("/forecasts/{forecast_id}", response_model=ForecastOut)
def get_forecast(forecast_id: UUID, db: Session = Depends(get_db)) -> ForecastOut:
    fc = get_forecast_or_404(db, forecast_id)
    return ForecastOut.model_validate(fc)


@router.get("/forecasts/{forecast_id}/paths", response_model=ForecastPathsOut)
def get_forecast_paths(
    forecast_id: UUID, db: Session = Depends(get_db)
) -> ForecastPathsOut:
    fc = get_forecast_or_404(db, forecast_id)
    _require_completed_forecast(fc.status, "paths")

    rows = list(
        db.scalars(
            select(ForecastPath)
            .where(ForecastPath.forecast_id == forecast_id)
            .order_by(ForecastPath.path_index)
        )
    )
    if not rows:
        raise ValidationError(
            f"forecast {forecast_id} has no persisted paths",
            code="forecast_paths_unavailable",
        )

    return ForecastPathsOut(
        forecast_id=forecast_id,
        as_of_date=fc.as_of_date,
        horizon_trading_days=fc.horizon_trading_days,
        initial_value=float(fc.initial_value),
        step_dates=compute_step_dates(fc.as_of_date, fc.horizon_trading_days),
        paths=[
            ForecastPathPoint(
                index=r.path_index,
                rank_label=r.rank_label,
                values=[float(v) for v in r.values],
            )
            for r in rows
        ],
    )


@router.get(
    "/forecasts/{forecast_id}/distribution", response_model=ForecastDistributionOut
)
def get_forecast_distribution(
    forecast_id: UUID, db: Session = Depends(get_db)
) -> ForecastDistributionOut:
    fc = get_forecast_or_404(db, forecast_id)
    _require_completed_forecast(fc.status, "distribution")

    required = [
        fc.p5_value,
        fc.p10_value,
        fc.p25_value,
        fc.median_value,
        fc.p75_value,
        fc.p90_value,
        fc.p95_value,
    ]
    if any(v is None for v in required):
        raise ValidationError(
            f"forecast {forecast_id} has no persisted percentiles",
            code="forecast_distribution_unavailable",
        )

    rows = list(
        db.scalars(
            select(ForecastDistributionBin)
            .where(ForecastDistributionBin.forecast_id == forecast_id)
            .order_by(ForecastDistributionBin.bin_index)
        )
    )
    if not rows:
        raise ValidationError(
            f"forecast {forecast_id} has no persisted distribution bins",
            code="forecast_distribution_unavailable",
        )

    return ForecastDistributionOut(
        forecast_id=forecast_id,
        initial_value=float(fc.initial_value),
        bin_count=len(rows),
        bins=[
            ForecastDistributionBinOut(
                index=r.bin_index,
                lower=float(r.bin_lower),
                upper=float(r.bin_upper),
                count=r.count,
            )
            for r in rows
        ],
        percentiles=ForecastPercentiles(
            p5=float(fc.p5_value),
            p10=float(fc.p10_value),
            p25=float(fc.p25_value),
            p50=float(fc.median_value),
            p75=float(fc.p75_value),
            p90=float(fc.p90_value),
            p95=float(fc.p95_value),
        ),
    )


def _require_completed_forecast(status: str, resource: str) -> None:
    if status != "completed":
        raise ValidationError(
            f"forecast {resource} are only available for completed forecasts "
            f"(status={status})",
            code="forecast_not_completed",
        )
