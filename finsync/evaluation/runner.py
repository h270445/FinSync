"""Replays the labelled matching dataset through the service and measures the result.

The metrics are the ones in docs/evaluation/evaluation-plan.md. Labels (`true_event`, `scenario`,
`kind`) are read here only, after the replay; the matcher sees the same fields the API would.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from itertools import combinations
import os
import tempfile
from typing import Iterator, Sequence

from finsync.core import FinSyncService
from finsync.evaluation.generate import GROUP_ID, MEMBERS, Row
from finsync.matching import decision as decision_rules
from finsync.storage import FinSyncStorage

SWEEP = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)
ORDERS = ("arrival", "reverse")
# The two candidate fixes for the reverse-order case (decision.STRICT_POOR_GATE, decision.REOPEN_CONTESTED).
OPTIONS = {"rules-2": (False, False), "A strict gate": (True, False), "B reopen": (False, True),
           "A+B": (True, True)}


@dataclass(frozen=True)
class FalseMerge:
    """One predicted event that holds records of two or more purchases."""

    record_ids: tuple[str, ...]
    true_events: tuple[str, ...]
    scenarios: tuple[str, ...]
    outcomes: tuple[str, ...]
    in_review: bool = False


@dataclass(frozen=True)
class Result:
    system: str
    split: str
    order: str
    records: int
    true_events: int
    predicted_events: int
    true_pairs: int
    merged_pairs: int
    correct_pairs: int
    missed: tuple[tuple[str, str], ...]
    review_records: int
    false_merges: tuple[FalseMerge, ...] = field(default=())
    outcomes: dict[str, str] = field(default_factory=dict)

    @property
    def precision(self) -> float | None:
        return self.correct_pairs / self.merged_pairs if self.merged_pairs else None

    @property
    def recall(self) -> float | None:
        return self.correct_pairs / self.true_pairs if self.true_pairs else None

    @property
    def false_merge_rate(self) -> float:
        return len(self.false_merges) / self.predicted_events if self.predicted_events else 0.0

    @property
    def missed_rate(self) -> float | None:
        return len(self.missed) / self.true_pairs if self.true_pairs else None

    @property
    def review_rate(self) -> float:
        return self.review_records / self.records if self.records else 0.0

    @property
    def double_counted(self) -> int:
        """Purchases counted more than once: predicted events beyond one per true event, ignoring false merges."""
        return self.predicted_events - self.true_events + self._absorbed

    @property
    def _absorbed(self) -> int:
        # Each false merge hides len(true_events) - 1 purchases inside another one's event.
        return sum(len(merge.true_events) - 1 for merge in self.false_merges)


def ordered(rows: Sequence[Row], order: str) -> list[Row]:
    """The rows in replay order: `arrival` is the dataset order, `reverse` the opposite."""
    by_arrival = sorted(rows, key=lambda row: (row.arrives_at, row.record_id))
    if order == "arrival":
        return by_arrival
    if order == "reverse":
        return by_arrival[::-1]
    raise ValueError(f"Unknown order: {order}")


@contextmanager
def thresholds(auto_link: float | None = None, review: float | None = None) -> Iterator[None]:
    """Temporarily replace the decision thresholds; `decide` reads them on every call."""
    saved = decision_rules.AUTO_LINK_THRESHOLD, decision_rules.REVIEW_THRESHOLD
    if auto_link is not None:
        decision_rules.AUTO_LINK_THRESHOLD = auto_link
    if review is not None:
        decision_rules.REVIEW_THRESHOLD = review
    try:
        yield
    finally:
        decision_rules.AUTO_LINK_THRESHOLD, decision_rules.REVIEW_THRESHOLD = saved


@contextmanager
def options(strict: bool, reopen: bool) -> Iterator[None]:
    """Temporarily switch the reverse-order options on or off."""
    saved = decision_rules.STRICT_POOR_GATE, decision_rules.REOPEN_CONTESTED
    decision_rules.STRICT_POOR_GATE, decision_rules.REOPEN_CONTESTED = strict, reopen
    try:
        yield
    finally:
        decision_rules.STRICT_POOR_GATE, decision_rules.REOPEN_CONTESTED = saved


def ingest(service: FinSyncService, row: Row) -> int:
    """Send one record the way its channel would and return the stored transaction id."""
    if row.source == "android_notification":
        return service.ingest_notification(row.member, GROUP_ID, row.message).transaction_id
    payload = {
        "amount": row.amount,
        "currency": row.currency,
        "description": row.description,
        "happened_at": row.happened_at,
        "merchant": row.merchant or None,
        "source_ref": row.source_ref or None,
    }
    return service.create_manual_transaction(row.member, GROUP_ID, payload).transaction_id


def run_matcher(rows: Sequence[Row], split: str = "all", order: str = "arrival",
                auto_link: float | None = None, system: str | None = None) -> Result:
    """Replay the rows through a fresh database and score the events it ends with."""
    replay = ordered(rows, order)
    # The storage opens a connection per operation, so a temporary file stands in for :memory:.
    with tempfile.TemporaryDirectory() as tempdir, thresholds(auto_link):
        storage = FinSyncStorage(os.path.join(tempdir, "eval.db"))
        service = FinSyncService(storage)
        for member in MEMBERS:
            storage.add_group_membership(member, GROUP_ID)
        record_of = {ingest(service, row): row.record_id for row in replay}
        event_of = {record_of[tx.id]: tx.event_id for tx in storage.list_transactions(GROUP_ID)}
        outcomes = {}
        for item in storage.list_decisions(GROUP_ID):
            if item["transaction_id"] in record_of:
                outcomes[record_of[item["transaction_id"]]] = item["outcome"]
        flagged = {
            (record_of[item["transaction_id"]], item["candidate_event_id"])
            for item in storage.list_open_reviews(GROUP_ID)
        }
        in_review = {event.id for event in storage.list_events(GROUP_ID) if event.review_state == "needs_review"}
    threshold = decision_rules.AUTO_LINK_THRESHOLD if auto_link is None else auto_link
    return score_events(rows, event_of, flagged, outcomes, system or f"matcher@{threshold:.2f}", split, order,
                        in_review)


def run_baseline(rows: Sequence[Row], split: str = "all", order: str = "arrival") -> Result:
    """The current behaviour without matching: every incoming row is its own expense."""
    event_of = {row.record_id: index for index, row in enumerate(ordered(rows, order))}
    return score_events(rows, event_of, set(), {}, "store-every-row", split, order)


def score_events(rows: Sequence[Row], event_of: dict[str, object], flagged: set[tuple[str, object]],
                 outcomes: dict[str, str], system: str, split: str, order: str,
                 in_review: set[object] = frozenset()) -> Result:
    """Compare predicted events with the labels.

    `flagged` holds (record_id, candidate event) for every open review: a true pair split across
    two events still counts as caught when one record waits for review against the other's event.
    `in_review` holds the predicted events flagged for review, so a false merge can say whether a
    person will see it.
    """
    label = {row.record_id: row for row in rows}
    by_true_event: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        by_true_event[row.true_event].append(row.record_id)
    true_pairs = {pair for ids in by_true_event.values() for pair in _pairs(ids)}
    members: dict[object, list[str]] = defaultdict(list)
    for record_id, event in event_of.items():
        members[event].append(record_id)
    merged_pairs = {pair for ids in members.values() for pair in _pairs(ids)}
    missed = {
        (left, right) for left, right in true_pairs - merged_pairs
        if (left, event_of[right]) not in flagged and (right, event_of[left]) not in flagged
    }
    false_merges = []
    for event, ids in members.items():
        records = sorted(ids)
        events = sorted({label[record_id].true_event for record_id in records})
        if len(events) > 1:
            false_merges.append(FalseMerge(
                record_ids=tuple(records),
                true_events=tuple(events),
                scenarios=tuple(label[record_id].scenario for record_id in records),
                outcomes=tuple(outcomes.get(record_id, "") for record_id in records),
                in_review=event in in_review,
            ))
    return Result(
        system=system,
        split=split,
        order=order,
        records=len(rows),
        true_events=len({row.true_event for row in rows}),
        predicted_events=len(members),
        true_pairs=len(true_pairs),
        merged_pairs=len(merged_pairs),
        correct_pairs=len(merged_pairs & true_pairs),
        missed=tuple(sorted(missed)),
        review_records=sum(1 for outcome in outcomes.values() if outcome == "needs_review"),
        false_merges=tuple(sorted(false_merges, key=lambda merge: merge.record_ids)),
        outcomes=outcomes,
    )


def choose_threshold(results: Sequence[Result]) -> Result:
    """Fewest false merges first (a hidden expense is worse than a double count), then recall, then review rate.

    Ties go to the higher threshold, the more cautious one.
    """
    return min(results, key=lambda result: (
        len(result.false_merges), -(result.recall or 0.0), result.review_rate, -_threshold_of(result),
    ))


def _threshold_of(result: Result) -> float:
    return float(result.system.rsplit("@", 1)[1])


def _pairs(ids) -> set[tuple[str, str]]:
    return set(combinations(sorted(ids), 2))
