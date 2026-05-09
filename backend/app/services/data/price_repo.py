from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.price import PriceHistory


def get_asset_by_ticker(db: Session, ticker: str) -> Asset | None:
    return db.scalar(select(Asset).where(Asset.ticker == ticker.upper()))


def search_assets(db: Session, query: str, limit: int = 20) -> list[Asset]:
    q = query.strip().upper()
    if not q:
        return list(db.scalars(select(Asset).order_by(Asset.ticker).limit(limit)))
    pattern = f"{q}%"
    return list(
        db.scalars(
            select(Asset)
            .where((Asset.ticker.like(pattern)) | (Asset.name.ilike(f"%{query}%")))
            .order_by(Asset.ticker)
            .limit(limit)
        )
    )


def get_prices(
    db: Session,
    ticker: str,
    start: date | None = None,
    end: date | None = None,
) -> list[PriceHistory]:
    asset = get_asset_by_ticker(db, ticker)
    if asset is None:
        return []
    stmt = select(PriceHistory).where(PriceHistory.asset_id == asset.id)
    if start is not None:
        stmt = stmt.where(PriceHistory.date >= start)
    if end is not None:
        stmt = stmt.where(PriceHistory.date <= end)
    return list(db.scalars(stmt.order_by(PriceHistory.date)))


def latest_price_date(db: Session, asset_id) -> date | None:
    return db.scalar(
        select(PriceHistory.date)
        .where(PriceHistory.asset_id == asset_id)
        .order_by(PriceHistory.date.desc())
        .limit(1)
    )


def earliest_price_date(db: Session, asset_id) -> date | None:
    return db.scalar(
        select(PriceHistory.date)
        .where(PriceHistory.asset_id == asset_id)
        .order_by(PriceHistory.date.asc())
        .limit(1)
    )
