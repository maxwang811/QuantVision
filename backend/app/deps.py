from fastapi import Header, HTTPException, status

from app.config import get_settings


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    """Gate /api/admin/* endpoints behind a shared secret."""
    settings = get_settings()
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")
