from typing import Protocol

from app.services.backtest.context import BacktestContext
from app.services.backtest.order import TargetWeightOrder


class Strategy(Protocol):
    """Strategy interface.

    The engine calls `on_day` once per trading day. Returned orders are queued
    and execute at the next trading day's close (T+1 fill convention).
    """

    def on_day(self, ctx: BacktestContext) -> list[TargetWeightOrder]: ...
