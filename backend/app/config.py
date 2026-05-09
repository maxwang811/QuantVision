from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        default="postgresql+psycopg://quantvision:quantvision@localhost:5432/quantvision",
        alias="DATABASE_URL",
    )
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    admin_token: str = Field(default="dev-only-token", alias="ADMIN_TOKEN")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    risk_free_rate: float = Field(default=0.0, alias="QV_RISK_FREE_RATE")

    forecast_default_lookback_days: int = Field(
        default=1260, alias="QV_FORECAST_DEFAULT_LOOKBACK_DAYS"
    )
    forecast_min_lookback_days: int = Field(
        default=252, alias="QV_FORECAST_MIN_LOOKBACK_DAYS"
    )
    forecast_default_n_simulations: int = Field(
        default=10_000, alias="QV_FORECAST_DEFAULT_N_SIMULATIONS"
    )
    forecast_default_n_sample_paths: int = Field(
        default=100, alias="QV_FORECAST_DEFAULT_N_SAMPLE_PATHS"
    )
    forecast_default_n_bins: int = Field(
        default=50, alias="QV_FORECAST_DEFAULT_N_BINS"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
