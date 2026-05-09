from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_assets,
    routes_backtest,
    routes_forecast,
    routes_health,
    routes_prices,
)
from app.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="QuantVision API",
        description="Portfolio forecasting and strategy simulation platform.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_origin_regex=r"https://quantvision-.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    app.include_router(routes_health.router, prefix="/api", tags=["health"])
    app.include_router(routes_assets.router, prefix="/api", tags=["assets"])
    app.include_router(routes_prices.router, prefix="/api", tags=["prices"])
    app.include_router(routes_backtest.router, prefix="/api", tags=["backtests"])
    app.include_router(routes_forecast.router, prefix="/api", tags=["forecasts"])

    return app


app = create_app()
