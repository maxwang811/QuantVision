from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db import get_db
from app.schemas.common import PricePoint, PriceSeriesOut
from app.services.data.price_repo import get_asset_by_ticker, get_prices

router = APIRouter()


@router.get("/prices/{ticker}", response_model=PriceSeriesOut)
def prices(
    ticker: str,
    start: date | None = Query(None),
    end: date | None = Query(None),
    db: Session = Depends(get_db),
) -> PriceSeriesOut:
    asset = get_asset_by_ticker(db, ticker)
    if asset is None:
        raise NotFoundError(f"unknown ticker: {ticker}")

    rows = get_prices(db, ticker, start=start, end=end)
    return PriceSeriesOut(
        ticker=asset.ticker,
        points=[
            PricePoint(
                date=r.date,
                open=float(r.open) if r.open is not None else None,
                high=float(r.high) if r.high is not None else None,
                low=float(r.low) if r.low is not None else None,
                close=float(r.close) if r.close is not None else None,
                adj_close=float(r.adj_close),
                volume=r.volume,
            )
            for r in rows
        ],
    )
