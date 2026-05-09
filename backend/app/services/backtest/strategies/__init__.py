"""Strategy registry.

Strategies register themselves with `@register("name")`. The runner constructs
them via `build_strategy(name, params)`. New strategies (Stage 3+) plug in here.
"""

from typing import Any

from app.core.errors import ValidationError
from app.services.backtest.strategies.base import Strategy

STRATEGY_REGISTRY: dict[str, type[Strategy]] = {}


def register(name: str):
    def deco(cls: type[Strategy]) -> type[Strategy]:
        STRATEGY_REGISTRY[name] = cls
        return cls

    return deco


def build_strategy(name: str, params: dict[str, Any]) -> Strategy:
    if name not in STRATEGY_REGISTRY:
        raise ValidationError(f"unknown strategy: {name}", code="unknown_strategy")
    return STRATEGY_REGISTRY[name](**params)


# Eager-import strategy modules so their @register decorators run at import time.
from app.services.backtest.strategies import buy_hold, rebalance  # noqa: E402,F401
