from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from finsync.matching.normalize import local_date, merchant_tokens, whole_units

TIME_WINDOW_HOURS = 48
DAY_WINDOW_DAYS = 3
WEIGHT_AMOUNT = 0.4
WEIGHT_TIME = 0.3
WEIGHT_MERCHANT = 0.3


@dataclass(frozen=True)
class MatchRecord:
    """The values matching looks at, for one stored or incoming record."""

    group_id: str
    channel: str
    amount: Decimal
    currency: str
    direction: str
    happened_at: datetime
    precision: str
    merchant_text: str | None
    id: int | None = None
    event_id: int | None = None


@dataclass(frozen=True)
class Features:
    amount: float
    time: float
    merchant: float
    delta: str
    score: float

    def as_dict(self) -> dict[str, float | str]:
        return {"a": self.amount, "t": self.time, "m": self.merchant, "delta": self.delta, "score": self.score}


def amount_score(new: MatchRecord, existing: MatchRecord) -> float | None:
    if new.amount == existing.amount:
        return 1.0
    if whole_units(new.amount) == whole_units(existing.amount):
        return 0.7
    return None


def time_score(new: MatchRecord, existing: MatchRecord) -> tuple[float, str] | None:
    if "day" in (new.precision, existing.precision):
        days = abs((local_date(new.happened_at, new.precision) - local_date(existing.happened_at, existing.precision)).days)
        if days > DAY_WINDOW_DAYS:
            return None
        return 1.0 - days / DAY_WINDOW_DAYS, f"{days}d"
    hours = abs((new.happened_at - existing.happened_at).total_seconds()) / 3600
    if hours > TIME_WINDOW_HOURS:
        return None
    return 1.0 - hours / TIME_WINDOW_HOURS, f"{hours:.2f}h"


def merchant_score(new: MatchRecord, existing: MatchRecord) -> float:
    left, right = merchant_tokens(new.merchant_text), merchant_tokens(existing.merchant_text)
    if not left or not right:
        return 0.5
    return len(left & right) / len(left | right)


def score(new: MatchRecord, existing: MatchRecord) -> Features | None:
    """Features and weighted score of a pair, or None when a blocking gate fails.

    The channel gate (one original record per channel in an event) needs the whole event,
    so the caller applies it.
    """
    if new.group_id != existing.group_id or new.currency != existing.currency or new.direction != existing.direction:
        return None
    a = amount_score(new, existing)
    if a is None:
        return None
    timed = time_score(new, existing)
    if timed is None:
        return None
    t, delta = timed
    m = merchant_score(new, existing)
    total = WEIGHT_AMOUNT * a + WEIGHT_TIME * t + WEIGHT_MERCHANT * m
    return Features(amount=a, time=round(t, 4), merchant=round(m, 4), delta=delta, score=round(total, 4))
