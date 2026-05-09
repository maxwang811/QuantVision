from app.core.time import is_month_end
from app.services.backtest.context import BacktestContext
from app.services.backtest.order import TargetWeightOrder
from app.services.backtest.strategies import register


@register("monthly_rebalance")
class MonthlyRebalance:
    def __init__(self, target_weights: dict[str, float]):
        self.target_weights = target_weights
        self._initialized = False

    def on_day(self, ctx: BacktestContext) -> list[TargetWeightOrder]:
        if not self._initialized:
            self._initialized = True
            return [TargetWeightOrder(t, w) for t, w in self.target_weights.items()]
        if is_month_end(ctx.date, ctx.all_trading_days):
            return [TargetWeightOrder(t, w) for t, w in self.target_weights.items()]
        return []
