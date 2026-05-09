from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

ModelName = Literal["logistic_regression", "xgboost"]


class ModelRunCreate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    tickers: list[str] = Field(min_length=1, max_length=50)
    benchmark_ticker: str = Field(default="SPY", max_length=16)
    start_date: date
    end_date: date
    label_horizon_days: int = Field(default=20, ge=5, le=126)
    training_lookback_days: int = Field(default=756, ge=126, le=5040)
    selected_model: ModelName = "xgboost"
    random_seed: int = Field(default=7, ge=0)

    @model_validator(mode="after")
    def _check(self) -> "ModelRunCreate":
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        normalized = [t.upper() for t in self.tickers]
        if len(set(normalized)) != len(normalized):
            raise ValueError("tickers must be unique")
        self.tickers = normalized
        self.benchmark_ticker = self.benchmark_ticker.upper()
        return self


class ModelRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str | None
    tickers: list[str]
    benchmark_ticker: str
    start_date: date
    end_date: date
    label_horizon_days: int
    training_lookback_days: int
    selected_model: str
    params: dict
    metrics: dict | None
    status: str
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class ModelPredictionOut(BaseModel):
    id: UUID
    date: date
    ticker: str
    model_name: str
    score: float
    rank: int
    label: int | None
    forward_return: float | None
    benchmark_forward_return: float | None


class ModelPredictionsOut(BaseModel):
    model_run_id: UUID
    predictions: list[ModelPredictionOut]
