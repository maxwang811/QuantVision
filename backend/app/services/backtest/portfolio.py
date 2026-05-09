from dataclasses import dataclass, field

from app.services.backtest.order import Fill


@dataclass
class Portfolio:
    """In-memory cash + share-holdings state. Float math; Decimal at the DB boundary."""

    cash: float
    holdings: dict[str, float] = field(default_factory=dict)

    def position_value(self, ticker: str, price: float) -> float:
        return self.holdings.get(ticker, 0.0) * price

    def equity(self, prices: dict[str, float]) -> float:
        total = self.cash
        for ticker, shares in self.holdings.items():
            if shares == 0.0:
                continue
            total += shares * prices[ticker]
        return total

    def apply_fill(self, fill: Fill) -> None:
        signed_qty = fill.quantity if fill.side == "buy" else -fill.quantity
        self.holdings[fill.ticker] = self.holdings.get(fill.ticker, 0.0) + signed_qty
        # Cash decreases on buy, increases on sell; tx cost is always charged.
        self.cash -= signed_qty * fill.price
        self.cash -= fill.transaction_cost

    def snapshot(self, prices: dict[str, float]) -> tuple[float, float, float]:
        """Return (cash, holdings_value, total_value)."""
        holdings_value = sum(
            shares * prices[t] for t, shares in self.holdings.items() if shares != 0.0
        )
        return self.cash, holdings_value, self.cash + holdings_value
