from __future__ import annotations

from bisect import bisect_right
from datetime import date

from app.core.time import is_month_end
from app.services.backtest.context import BacktestContext
from app.services.backtest.order import TargetWeightOrder
from app.services.backtest.strategies import register


def _should_rebalance(ctx: BacktestContext, initialized: bool, frequency: str) -> bool:
    if not initialized:
        return True
    if frequency == "monthly":
        return is_month_end(ctx.date, ctx.all_trading_days)
    return False


def _target_orders(universe: list[str], selected: list[str]) -> list[TargetWeightOrder]:
    selected_set = set(selected)
    weight = 1.0 / len(selected) if selected else 0.0
    return [
        TargetWeightOrder(ticker, weight if ticker in selected_set else 0.0)
        for ticker in universe
    ]


@register("momentum")
class MomentumRanking:
    def __init__(
        self,
        target_weights: dict[str, float],
        top_n: int = 5,
        lookback_days: int = 63,
        rebalance_frequency: str = "monthly",
    ):
        self.universe = list(target_weights)
        self.top_n = max(1, min(int(top_n), len(self.universe)))
        self.lookback_days = int(lookback_days)
        self.rebalance_frequency = rebalance_frequency
        self._initialized = False

    def on_day(self, ctx: BacktestContext) -> list[TargetWeightOrder]:
        if not _should_rebalance(ctx, self._initialized, self.rebalance_frequency):
            return []
        self._initialized = True

        scores: list[tuple[str, float]] = []
        for ticker in self.universe:
            bars = ctx.prices_so_far.get(ticker, [])
            if len(bars) <= self.lookback_days:
                continue
            start = bars[-1 - self.lookback_days].adj_close
            end = bars[-1].adj_close
            if start > 0:
                scores.append((ticker, end / start - 1.0))

        if not scores:
            selected = self.universe[: self.top_n]
        else:
            scores.sort(key=lambda ts: (-ts[1], ts[0]))
            selected = [ticker for ticker, _score in scores[: self.top_n]]
        return _target_orders(self.universe, selected)


@register("ml_ranking")
class MLRanking:
    def __init__(
        self,
        target_weights: dict[str, float],
        prediction_scores: dict[date, dict[str, float]],
        top_n: int = 5,
        rebalance_frequency: str = "monthly",
    ):
        self.universe = list(target_weights)
        self.prediction_scores = prediction_scores
        self.prediction_dates = sorted(prediction_scores)
        self.top_n = max(1, min(int(top_n), len(self.universe)))
        self.rebalance_frequency = rebalance_frequency
        self._initialized = False

    def on_day(self, ctx: BacktestContext) -> list[TargetWeightOrder]:
        if not _should_rebalance(ctx, self._initialized, self.rebalance_frequency):
            return []
        self._initialized = True

        scores = self._scores_for(ctx.date)
        if not scores:
            return []

        ranked = sorted(
            ((ticker, scores[ticker]) for ticker in self.universe if ticker in scores),
            key=lambda ts: (-ts[1], ts[0]),
        )
        selected = [ticker for ticker, _score in ranked[: self.top_n]]
        return _target_orders(self.universe, selected)

    def _scores_for(self, current_date: date) -> dict[str, float] | None:
        idx = bisect_right(self.prediction_dates, current_date)
        if idx == 0:
            return None
        return self.prediction_scores[self.prediction_dates[idx - 1]]
