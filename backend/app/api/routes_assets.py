from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.common import AssetOut
from app.services.data.price_repo import search_assets

router = APIRouter()


@router.get("/assets", response_model=list[AssetOut])
def list_assets(
    q: str = Query("", description="Ticker prefix or name substring"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[AssetOut]:
    """Autocomplete by ticker prefix (case-insensitive) or company name substring."""
    rows = search_assets(db, q, limit=limit)
    return [AssetOut.model_validate(r) for r in rows]
