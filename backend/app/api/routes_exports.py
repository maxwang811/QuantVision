from __future__ import annotations

import csv
import json
from io import StringIO
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db import get_db
from app.models.asset import Asset
from app.models.backtest import Backtest
from app.models.experiment_sweep import ExperimentSweep
from app.models.experiment_sweep_run import ExperimentSweepRun
from app.models.forecast import Forecast
from app.models.forecast_distribution_bin import ForecastDistributionBin
from app.models.forecast_path import ForecastPath
from app.models.portfolio_value import PortfolioValue
from app.models.trade import Trade
from app.schemas.backtest import BacktestOut
from app.schemas.experiments import (
    ExperimentCompareRequest,
    ExperimentSweepOut,
    ExperimentSweepRunOut,
)
from app.schemas.forecast import ForecastOut
from app.services.experiments import compare_experiments

router = APIRouter()

ExportFormat = Literal["json", "csv"]


@router.get("/exports/backtests/{backtest_id}")
def export_backtest(
    backtest_id: UUID,
    export_format: ExportFormat = Query(default="json", alias="format"),
    artifact: Literal["summary", "portfolio_values", "trades"] = Query(default="summary"),
    db: Session = Depends(get_db),
):
    bundle = _backtest_bundle(db, backtest_id)
    if export_format == "json":
        return _json(bundle)
    return _csv_response(
        _rows_for_artifact(bundle, artifact),
        filename=f"backtest-{backtest_id}-{artifact}.csv",
    )


@router.get("/exports/forecasts/{forecast_id}")
def export_forecast(
    forecast_id: UUID,
    export_format: ExportFormat = Query(default="json", alias="format"),
    artifact: Literal["summary", "distribution", "paths"] = Query(default="summary"),
    db: Session = Depends(get_db),
):
    bundle = _forecast_bundle(db, forecast_id)
    if export_format == "json":
        return _json(bundle)
    return _csv_response(
        _rows_for_artifact(bundle, artifact),
        filename=f"forecast-{forecast_id}-{artifact}.csv",
    )


@router.get("/exports/sweeps/{sweep_id}")
def export_sweep(
    sweep_id: UUID,
    export_format: ExportFormat = Query(default="json", alias="format"),
    db: Session = Depends(get_db),
):
    bundle = _sweep_bundle(db, sweep_id)
    if export_format == "json":
        return _json(bundle)
    return _csv_response(bundle["runs"], filename=f"sweep-{sweep_id}.csv")


@router.post("/exports/compare")
def export_compare(
    req: ExperimentCompareRequest,
    export_format: ExportFormat = Query(default="json", alias="format"),
    db: Session = Depends(get_db),
):
    comparison = compare_experiments(db, req).model_dump(mode="json")
    if export_format == "json":
        return _json(comparison)

    rows: list[dict[str, Any]] = []
    for item in comparison["backtests"]:
        rows.append(
            {
                "kind": "backtest",
                "id": item["id"],
                "name": item["name"],
                "label": item["strategy"],
                "status": item["status"],
                "primary_metric": item["final_value"],
                "secondary_metric": item["total_return"],
                "sharpe_ratio": item["sharpe_ratio"],
                "max_drawdown": item["max_drawdown"],
                "created_at": item["created_at"],
            }
        )
    for item in comparison["forecasts"]:
        rows.append(
            {
                "kind": "forecast",
                "id": item["id"],
                "name": item["name"],
                "label": item["method"],
                "status": item["status"],
                "primary_metric": item["expected_value"],
                "secondary_metric": item["probability_of_loss"],
                "p10_value": item["p10_value"],
                "p90_value": item["p90_value"],
                "created_at": item["created_at"],
            }
        )
    return _csv_response(rows, filename="experiment-comparison.csv")


def _backtest_bundle(db: Session, backtest_id: UUID) -> dict[str, Any]:
    bt = db.get(Backtest, backtest_id)
    if bt is None:
        raise NotFoundError(f"backtest not found: {backtest_id}")

    portfolio_values = [
        {
            "date": row.date,
            "cash": row.cash,
            "holdings_value": row.holdings_value,
            "total_value": row.total_value,
        }
        for row in db.scalars(
            select(PortfolioValue)
            .where(PortfolioValue.backtest_id == backtest_id)
            .order_by(PortfolioValue.date)
        )
    ]
    trade_rows = list(
        db.execute(
            select(Trade, Asset.ticker)
            .join(Asset, Asset.id == Trade.asset_id)
            .where(Trade.backtest_id == backtest_id)
            .order_by(Trade.date, Trade.id)
        )
    )
    trades = [
        {
            "id": trade.id,
            "date": trade.date,
            "ticker": ticker,
            "side": trade.side,
            "quantity": trade.quantity,
            "price": trade.price,
            "transaction_cost": trade.transaction_cost,
            "notional": trade.notional,
        }
        for trade, ticker in trade_rows
    ]
    summary = BacktestOut.model_validate(bt).model_dump(mode="json")
    summary["params"] = bt.params
    return {
        "summary": summary,
        "portfolio_values": portfolio_values,
        "trades": trades,
    }


def _forecast_bundle(db: Session, forecast_id: UUID) -> dict[str, Any]:
    fc = db.get(Forecast, forecast_id)
    if fc is None:
        raise NotFoundError(f"forecast not found: {forecast_id}")

    distribution = [
        {
            "index": row.bin_index,
            "lower": row.bin_lower,
            "upper": row.bin_upper,
            "count": row.count,
        }
        for row in db.scalars(
            select(ForecastDistributionBin)
            .where(ForecastDistributionBin.forecast_id == forecast_id)
            .order_by(ForecastDistributionBin.bin_index)
        )
    ]
    paths = [
        {
            "index": row.path_index,
            "rank_label": row.rank_label,
            "values": row.values,
        }
        for row in db.scalars(
            select(ForecastPath)
            .where(ForecastPath.forecast_id == forecast_id)
            .order_by(ForecastPath.path_index)
        )
    ]
    summary = ForecastOut.model_validate(fc).model_dump(mode="json")
    summary["params"] = fc.params
    return {"summary": summary, "distribution": distribution, "paths": paths}


def _sweep_bundle(db: Session, sweep_id: UUID) -> dict[str, Any]:
    sweep = db.get(ExperimentSweep, sweep_id)
    if sweep is None:
        raise NotFoundError(f"experiment sweep not found: {sweep_id}")
    runs = [
        ExperimentSweepRunOut.model_validate(row).model_dump(mode="json")
        for row in db.scalars(
            select(ExperimentSweepRun)
            .where(ExperimentSweepRun.sweep_id == sweep_id)
            .order_by(ExperimentSweepRun.run_index)
        )
    ]
    return {
        "summary": ExperimentSweepOut.model_validate(sweep).model_dump(mode="json"),
        "runs": runs,
    }


def _rows_for_artifact(bundle: dict[str, Any], artifact: str) -> list[dict[str, Any]]:
    if artifact == "summary":
        return [bundle["summary"]]
    if artifact == "paths":
        rows: list[dict[str, Any]] = []
        for path in bundle["paths"]:
            for step, value in enumerate(path["values"]):
                rows.append(
                    {
                        "path_index": path["index"],
                        "rank_label": path["rank_label"],
                        "step": step,
                        "value": value,
                    }
                )
        return rows
    return list(bundle[artifact])


def _json(data: Any) -> JSONResponse:
    return JSONResponse(content=jsonable_encoder(data))


def _csv_response(rows: list[dict[str, Any]], *, filename: str) -> Response:
    buf = StringIO()
    normalized_rows = [jsonable_encoder(row) for row in rows]
    fieldnames = sorted({key for row in normalized_rows for key in row})
    if not fieldnames:
        fieldnames = ["empty"]
        normalized_rows = [{"empty": ""}]
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in normalized_rows:
        writer.writerow({key: _csv_cell(row.get(key)) for key in fieldnames})
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _csv_cell(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value
