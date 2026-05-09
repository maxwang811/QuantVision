from app.services.backtest.context import BacktestContext
from app.services.backtest.order import TargetWeightOrder
from app.services.backtest.strategies import register


@register("buy_and_hold")
class BuyAndHold:
    def __init__(self, target_weights: dict[str, float]):
        self.target_weights = target_weights
        self._fired = False

    def on_day(self, _ctx: BacktestContext) -> list[TargetWeightOrder]:
        if self._fired:
            return []
        self._fired = True
        return [TargetWeightOrder(t, w) for t, w in self.target_weights.items()]
