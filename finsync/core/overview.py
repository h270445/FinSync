"""Month totals for the W2 overview, computed from deduplicated events.

One event is one real purchase or income, however many sources reported it, so totals are summed over
events, never over source records. The rules ([user interface](../../docs/design/user-interface.md#web-app)):

- An event belongs to the Europe/Budapest calendar month of its primary record (ADR 0008).
- An event is counted for the member whose primary record it is.
- Expense and income are summed separately, as positive amounts, and every currency on its own.
- Events with the direction `transfer` (money moved between the group's own accounts) are left out
  of the totals and only counted.
- Events still waiting for review are included in the totals and also counted and summed separately,
  so the screen can show how much of a total is not settled yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
import re

from finsync.matching.normalize import local_date
from finsync.storage import EventRecord

_MONTH = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")
TRANSFER = "transfer"


@dataclass
class Bucket:
    """Totals of one group of events (the whole month, one category or one member) in one currency."""

    key: str
    currency: str
    expense: Decimal = Decimal("0")
    income: Decimal = Decimal("0")
    event_count: int = 0
    review_count: int = 0
    review_amount: Decimal = Decimal("0")


@dataclass
class Overview:
    month: str
    months: list[str]
    totals: list[Bucket] = field(default_factory=list)
    categories: list[Bucket] = field(default_factory=list)
    members: list[Bucket] = field(default_factory=list)
    transfer_count: int = 0


def parse_month(value: str | None, today: date) -> str:
    """``YYYY-MM``; without a value, the current month."""
    if value is None or value == "":
        return f"{today.year:04d}-{today.month:02d}"
    if not _MONTH.match(value):
        raise ValueError("month must be YYYY-MM, for example 2026-11")
    return value


def event_month(event: EventRecord) -> str:
    primary = next((tx for tx in event.transactions if tx.id == event.primary_transaction_id), None)
    precision = primary.happened_at_precision if primary else "minute"
    day = local_date(event.happened_at, precision)
    return f"{day.year:04d}-{day.month:02d}"


def event_member(event: EventRecord) -> str:
    primary = next((tx for tx in event.transactions if tx.id == event.primary_transaction_id), None)
    if primary is not None:
        return primary.user_id
    return event.transactions[0].user_id if event.transactions else ""


def build_overview(events: list[EventRecord], month: str) -> Overview:
    months = sorted({event_month(event) for event in events}, reverse=True)
    overview = Overview(month=month, months=months)
    totals: dict[tuple[str, str], Bucket] = {}
    categories: dict[tuple[str, str], Bucket] = {}
    members: dict[tuple[str, str], Bucket] = {}
    for event in events:
        if event_month(event) != month:
            continue
        if event.direction == TRANSFER:
            overview.transfer_count += 1
            continue
        for buckets, key in ((totals, "all"), (categories, event.category), (members, event_member(event))):
            bucket = buckets.setdefault((key, event.currency), Bucket(key, event.currency))
            _add(bucket, event)
    overview.totals = sorted(totals.values(), key=lambda b: b.currency)
    overview.categories = sorted(categories.values(), key=lambda b: (b.currency, -b.expense, -b.income, b.key))
    overview.members = sorted(members.values(), key=lambda b: (b.currency, b.key))
    return overview


def _add(bucket: Bucket, event: EventRecord) -> None:
    amount = abs(event.amount)
    if event.direction == "income":
        bucket.income += amount
    else:
        bucket.expense += amount
    bucket.event_count += 1
    if event.review_state == "needs_review":
        bucket.review_count += 1
        bucket.review_amount += amount
