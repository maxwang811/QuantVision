from app.services.backtest.context import BacktestContext
from app.services.backtest.order import TargetWeightOrder
from app.services.backtest.strategies import register


@register("ma_crossover")
class MACrossover:
    """Per-ticker moving-average crossover overlay on user-specified weights.

    A ticker is "long" on a given day when its short SMA > long SMA over the
    trailing `short_window` and `long_window` bars in `prices_so_far`. Active
    tickers retain their user-specified target weight; inactive tickers go to
    zero and the freed allocation is held as cash. Orders are emitted only on
    signal-state changes to avoid redundant turnover.
    """

    def __init__(
        self,
        target_weights: dict[str, float],
        short_window: int = 50,
        long_window: int = 200,
    ):
        if short_window >= long_window:
            raise ValueError("short_window must be < long_window")
        self.target_weights = dict(target_weights)
        self.universe = list(self.target_weights)
        self.short_window = int(short_window)
        self.long_window = int(long_window)
        self._last_signals: dict[str, bool] | None = None

    def on_day(self, ctx: BacktestContext) -> list[TargetWeightOrder]:
        current_signals: dict[str, bool] = {}
        for ticker in self.universe:
            bars = ctx.prices_so_far.get(ticker, [])
            if len(bars) < self.long_window:
                current_signals[ticker] = False
                continue
            short_slice = bars[-self.short_window :]
            long_slice = bars[-self.long_window :]
            short_ma = sum(b.adj_close for b in short_slice) / self.short_window
            long_ma = sum(b.adj_close for b in long_slice) / self.long_window
            current_signals[ticker] = short_ma > long_ma

        if self._last_signals == current_signals:
            return []
        self._last_signals = current_signals

        return [
            TargetWeightOrder(
                ticker,
                self.target_weights[ticker] if current_signals[ticker] else 0.0,
            )
            for ticker in self.universe
        ]
