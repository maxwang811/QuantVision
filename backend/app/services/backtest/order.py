from dataclasses import dataclass
from datetime import date
from typing import Literal


@dataclass(frozen=True)
class TargetWeightOrder:
    """Strategy intent: rebalance `ticker` to `target_weight` of total equity."""

    ticker: str
    target_weight: float


@dataclass(frozen=True)
class Fill:
    """An executed trade. Always-positive `quantity`; `side` carries direction."""

    date: date
    ticker: str
    side: Literal["buy", "sell"]
    quantity: float
    price: float
    transaction_cost: float
    notional: float
