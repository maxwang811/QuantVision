from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssetOut(BaseModel):
    """Public asset representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticker: str
    name: str | None
    asset_class: str
    exchange: str | None
    currency: str
    created_at: datetime


class PricePoint(BaseModel):
    """One day of OHLCV for a ticker."""

    date: date
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    adj_close: float = Field(..., description="Split- and dividend-adjusted close")
    volume: int | None = None


class PriceSeriesOut(BaseModel):
    ticker: str
    points: list[PricePoint]


class HealthOut(BaseModel):
    status: str
    db: bool
