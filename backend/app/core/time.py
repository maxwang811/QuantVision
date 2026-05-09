from datetime import date, timedelta

import pandas as pd


def trading_days(start: date, end: date) -> list[date]:
    """Return US-equity-style trading days between start and end inclusive.

    Uses pandas business-day calendar; does not account for early closes or
    market holidays beyond standard NYSE weekends. Good enough for daily-bar
    backtests where execution is at close.
    """
    rng = pd.bdate_range(start=start, end=end)
    return [d.date() for d in rng]


def add_trading_days(base: date, n: int) -> date:
    """Add n business days (positive or negative) to a date."""
    return (pd.Timestamp(base) + pd.tseries.offsets.BDay(n)).date()


def year_fraction(start: date, end: date) -> float:
    """Year fraction between two dates using ACT/365."""
    return (end - start).days / 365.0


def is_month_end(d: date, all_days: list[date]) -> bool:
    """True if d is the last trading day of its month within all_days."""
    next_day = d + timedelta(days=1)
    while next_day not in all_days:
        if next_day.month != d.month:
            return True
        next_day += timedelta(days=1)
        if (next_day - d).days > 7:
            return True
    return next_day.month != d.month
