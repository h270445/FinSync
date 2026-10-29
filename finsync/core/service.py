from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re
from typing import Any
import uuid

from finsync.categorization import categorize_transaction
from finsync.ingestion import parse_notification
from finsync.matching import (
    MATCHER_VERSION,
    MatchRecord,
    canonical_row,
    decide,
    direction_of,
    fingerprint,
    score,
)
from finsync.matching import decision as decision_rules
from finsync.matching.scoring import DAY_WINDOW_DAYS
from finsync.storage import (
    EventRecord,
    FinSyncStorage,
    StorageSession,
    TransactionRecord,
    candidate_time_range,
)

_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class AuthorizationError(PermissionError):
    """Raised when user is not authorized for group access."""


class NotFoundError(LookupError):
    """Raised when an id does not exist in the requested group."""


class ConflictError(ValueError):
    """Raised when a review action no longer fits the current state, such as a decision already answered."""


@dataclass(frozen=True)
class TransactionInput:
    amount: Decimal
    currency: str
    description: str
    merchant: str | None
    happened_at: datetime
    precision: str = "minute"
    direction: str = "expense"
    source_ref: str | None = None


@dataclass(frozen=True)
class StoreResult:
    """What happened to one incoming record."""

    transaction_id: int
    event_id: int
    match_outcome: str


@dataclass(frozen=True)
class ReviewItem:
    """One uncertain match waiting for a member: the record, the event it may belong to, and why."""

    decision_id: int
    transaction: TransactionRecord
    candidate_event: EventRecord
    score: float | None
    features: dict[str, Any] | None


class FinSyncService:
    def __init__(self, storage: FinSyncStorage) -> None:
        self._storage = storage

    def bootstrap_demo_membership(self) -> None:
        self._storage.add_group_membership("demo-user", "demo-group")

    def ensure_authorized(self, user_id: str, group_id: str) -> None:
        if not self._storage.is_user_in_group(user_id, group_id):
            raise AuthorizationError("User is not authorized for this group")

    def ingest_notification(self, user_id: str, group_id: str, message: str) -> StoreResult:
        self.ensure_authorized(user_id, group_id)
        raw = message.strip()
        parsed = parse_notification(raw)
        record = {
            "user_id": user_id,
            "group_id": group_id,
            "amount": parsed.amount,
            "currency": parsed.currency,
            "description": parsed.description,
            "merchant": parsed.merchant_or_counterparty,
            "category": categorize_transaction(parsed.description + " " + parsed.merchant_or_counterparty),
            "source": "android_notification",
            "happened_at": parsed.happened_at.astimezone(timezone.utc),
            "direction": direction_of(parsed.amount),
            "happened_at_precision": "minute",
            "raw_payload": raw,
        }
        with self._storage.transaction() as session:
            return self._store_and_match(session, record)

    def create_manual_transaction(self, user_id: str, group_id: str, payload: dict[str, Any]) -> StoreResult:
        self.ensure_authorized(user_id, group_id)
        tx = self._validate_transaction_payload(payload)
        with self._storage.transaction() as session:
            return self._store_and_match(session, self._manual_record(user_id, group_id, tx))

    def bulk_create_manual_transactions(
        self,
        user_id: str,
        group_id: str,
        rows: list[dict[str, Any]],
    ) -> list[StoreResult]:
        self.ensure_authorized(user_id, group_id)
        # Validate every row before writing anything, so one bad row rejects the whole batch.
        validated: list[TransactionInput] = []
        for index, row in enumerate(rows):
            try:
                validated.append(self._validate_transaction_payload(row))
            except ValueError as error:
                raise ValueError(f"Row {index}: {error}") from error
        batch_id = uuid.uuid4().hex
        with self._storage.transaction() as session:
            return [
                self._store_and_match(session, self._manual_record(user_id, group_id, tx, batch_id))
                for tx in validated
            ]

    @staticmethod
    def _manual_record(
        user_id: str, group_id: str, tx: TransactionInput, import_batch_id: str | None = None
    ) -> dict[str, Any]:
        fields = {
            "amount": str(tx.amount),
            "currency": tx.currency,
            "description": tx.description,
            "merchant": tx.merchant,
            "happened_at": tx.happened_at.isoformat(),
            "precision": tx.precision,
            "source_ref": tx.source_ref,
        }
        return {
            "user_id": user_id,
            "group_id": group_id,
            "amount": tx.amount,
            "currency": tx.currency,
            "description": tx.description,
            "merchant": tx.merchant,
            "category": categorize_transaction(f"{tx.description} {tx.merchant or ''}"),
            "source": "manual",
            "happened_at": tx.happened_at,
            "direction": tx.direction,
            "happened_at_precision": tx.precision,
            "raw_payload": canonical_row(fields),
            "source_ref": tx.source_ref,
            "import_batch_id": import_batch_id,
        }

    @staticmethod
    def _store_and_match(session: StorageSession, record: dict[str, Any]) -> StoreResult:
        """Store one record and link it to an event, writing the decision that explains the link."""
        group_id = record["group_id"]
        channel = _channel(record["source"], record["user_id"])
        record["fingerprint"] = fingerprint(group_id, channel, record["raw_payload"])

        # Step 2: exact re-delivery. A manual row without a client reference may be a second,
        # identical purchase (two bus tickets), so it goes to review instead.
        original = session.find_original_by_fingerprint(group_id, record["fingerprint"])
        rejected = session.rejected_event_ids(group_id, record["fingerprint"])
        if original is not None and original.event_id is not None and original.event_id not in rejected:
            if record["source"] != "manual" or record.get("source_ref"):
                transaction_id = session.insert_record(
                    **record, event_id=original.event_id, duplicate_of_id=original.id
                )
                session.insert_decision(
                    group_id=group_id,
                    transaction_id=transaction_id,
                    candidate_event_id=original.event_id,
                    outcome="exact_duplicate",
                    features={"duplicate_of_id": original.id},
                    matcher_version=MATCHER_VERSION,
                )
                return StoreResult(transaction_id, original.event_id, "exact_duplicate")
            return _store_new_event(
                session, record, "needs_review", original.event_id, {"identical_row_of_id": original.id}
            )

        # Steps 3-5: candidates, score, decide.
        new = _match_record(record, channel)
        start, end = candidate_time_range(record["happened_at"], DAY_WINDOW_DAYS + 1)
        best_by_event: dict[int, Any] = {}
        blocked_by_event: dict[int, Any] = {}
        channels_by_event: dict[int, set[str]] = {}
        for existing in session.candidate_records(group_id, record["currency"], start, end):
            if existing.event_id is None or existing.event_id in rejected:
                continue
            if existing.event_id not in channels_by_event:
                channels_by_event[existing.event_id] = {
                    _channel(item.source, item.user_id) for item in session.event_originals(existing.event_id)
                }
            blocked = channel in channels_by_event[existing.event_id]
            if blocked and (not decision_rules.REOPEN_CONTESTED or _channel(existing.source, existing.user_id) == channel):
                continue
            features = score(new, _match_record_of(existing))
            if features is None:
                continue
            target = blocked_by_event if blocked else best_by_event
            current = target.get(existing.event_id)
            if current is None or features.score > current.score:
                target[existing.event_id] = features

        contested = _contested(session, blocked_by_event)
        decision = decide(best_by_event, contested)
        details = None
        if decision.features is not None:
            details = {**decision.features.as_dict(), "runner_up": decision.runner_up}
        if decision.event_id in contested:
            details["contested"] = True
            result = _store_new_event(session, record, decision.outcome, decision.event_id, details)
            session.refresh_review_state(decision.event_id)
            return result
        if decision.outcome == "auto_linked" and decision.event_id is not None:
            transaction_id = session.insert_record(**record, event_id=decision.event_id)
            session.refresh_event(decision.event_id)
            session.insert_decision(
                group_id=group_id,
                transaction_id=transaction_id,
                candidate_event_id=decision.event_id,
                outcome="auto_linked",
                features=details,
                matcher_version=MATCHER_VERSION,
            )
            return StoreResult(transaction_id, decision.event_id, "auto_linked")
        return _store_new_event(session, record, decision.outcome, decision.event_id, details)

    def list_group_transactions(self, user_id: str, group_id: str) -> list[TransactionRecord]:
        self.ensure_authorized(user_id, group_id)
        return self._storage.list_transactions(group_id)

    def list_group_events(self, user_id: str, group_id: str) -> list[EventRecord]:
        self.ensure_authorized(user_id, group_id)
        return self._storage.list_events(group_id)

    def list_open_reviews(self, user_id: str, group_id: str) -> list[ReviewItem]:
        """Undecided needs_review decisions, each with the record and the event it may belong to."""
        self.ensure_authorized(user_id, group_id)
        events = {event.id: event for event in self._storage.list_events(group_id)}
        transactions = {tx.id: tx for tx in self._storage.list_transactions(group_id)}
        items = []
        for decision in self._storage.list_open_reviews(group_id):
            candidate = events.get(decision["candidate_event_id"])
            record = transactions.get(decision["transaction_id"])
            if candidate is None or record is None:
                continue
            items.append(ReviewItem(decision["id"], record, candidate, decision["score"], decision["features"]))
        return items

    def confirm_match(self, user_id: str, group_id: str, decision_id: int) -> StoreResult:
        """The member says the record is the same purchase as the candidate event: link them."""
        self.ensure_authorized(user_id, group_id)
        with self._storage.transaction() as session:
            decision, record = self._open_review(session, group_id, decision_id)
            target = int(decision["candidate_event_id"])
            features = decision["features"] or {}
            originals = session.event_originals(target)
            if not originals:
                raise ConflictError("The proposed event no longer holds any record")
            channel = _channel(record.source, record.user_id)
            same_channel = [item for item in originals if _channel(item.source, item.user_id) == channel]
            duplicate_of_id = None
            if same_channel:
                # Only an identical row from the same channel can join: it becomes a re-delivery of the original.
                if features.get("identical_row_of_id") != same_channel[0].id:
                    raise ConflictError("The event already holds a record from this channel; split it first")
                duplicate_of_id = same_channel[0].id
            previous_event = int(record.event_id) if record.event_id is not None else None
            session.move_record(record.id, target, duplicate_of_id)
            session.insert_decision(
                group_id=group_id,
                transaction_id=record.id,
                candidate_event_id=target,
                outcome="confirmed",
                features=decision["features"],
                matcher_version=decision["matcher_version"],
                decided_by=user_id,
                supersedes_id=decision_id,
            )
            for event_id in {target, previous_event} - {None}:
                session.refresh_event(event_id)
                session.refresh_review_state(event_id)
            if previous_event is not None and not session.event_originals(previous_event):
                _retarget_reviews(session, group_id, previous_event, target)
        return StoreResult(record.id, target, "confirmed")

    def reject_match(self, user_id: str, group_id: str, decision_id: int) -> StoreResult:
        """The member says the record is a separate purchase: keep it apart and never propose the pair again."""
        self.ensure_authorized(user_id, group_id)
        with self._storage.transaction() as session:
            decision, record = self._open_review(session, group_id, decision_id)
            session.insert_decision(
                group_id=group_id,
                transaction_id=record.id,
                candidate_event_id=decision["candidate_event_id"],
                outcome="rejected",
                features=decision["features"],
                matcher_version=decision["matcher_version"],
                decided_by=user_id,
                supersedes_id=decision_id,
            )
            # A contested review also flags the event it points at.
            for event_id in {record.event_id, decision["candidate_event_id"]} - {None}:
                session.refresh_review_state(int(event_id))
        return StoreResult(record.id, int(record.event_id or 0), "rejected")

    def split_event(self, user_id: str, group_id: str, event_id: int, transaction_id: int) -> StoreResult:
        """Undo a wrong link: move one original record (with its re-deliveries) to a new event of its own."""
        self.ensure_authorized(user_id, group_id)
        with self._storage.transaction() as session:
            record = session.get_transaction(group_id, transaction_id)
            if record is None or record.event_id != event_id:
                raise NotFoundError("Transaction not found in this event")
            if record.duplicate_of_id is not None:
                raise ValueError("A re-delivery moves with its original; split the original record instead")
            if len(session.event_originals(event_id)) < 2:
                raise ConflictError("The event holds only this record; there is nothing to split")
            new_event_id = session.create_event(
                group_id=group_id,
                amount=record.amount,
                currency=record.currency,
                direction=record.direction,
                happened_at=record.happened_at,
                merchant=record.merchant,
                category=record.category,
                review_state="clear",
            )
            session.move_record(record.id, new_event_id)
            session.insert_decision(
                group_id=group_id,
                transaction_id=record.id,
                candidate_event_id=event_id,
                outcome="split",
                features=None,
                matcher_version=MATCHER_VERSION,
                decided_by=user_id,
                # Only the decision that made this link is undone; an open review of the record stays open.
                supersedes_id=session.link_decision_id(record.id, event_id),
            )
            for affected in (event_id, new_event_id):
                session.refresh_event(affected)
                session.refresh_review_state(affected)
        return StoreResult(record.id, new_event_id, "split")

    @staticmethod
    def _open_review(
        session: StorageSession, group_id: str, decision_id: int
    ) -> tuple[dict[str, Any], TransactionRecord]:
        decision = session.get_decision(group_id, decision_id)
        if decision is None:
            raise NotFoundError("Decision not found")
        if decision["outcome"] != "needs_review" or session.is_superseded(decision_id):
            raise ConflictError("This decision is not waiting for review")
        record = session.get_transaction(group_id, int(decision["transaction_id"]))
        if record is None or decision["candidate_event_id"] is None:
            raise NotFoundError("Decision not found")
        return decision, record

    @staticmethod
    def _validate_transaction_payload(payload: dict[str, Any]) -> TransactionInput:
        if not isinstance(payload, dict):
            raise ValueError("Transaction must be a JSON object")
        required = {"amount", "currency", "description", "happened_at"}
        missing = required - payload.keys()
        if missing:
            raise ValueError(f"Missing fields: {', '.join(sorted(missing))}")

        try:
            amount = Decimal(str(payload["amount"]))
        except (InvalidOperation, ValueError) as error:
            raise ValueError("Invalid amount") from error
        if not amount.is_finite():
            raise ValueError("Invalid amount")
        if amount == 0:
            raise ValueError("Amount cannot be zero")

        currency = str(payload["currency"]).upper().strip()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("Currency must be a 3-letter code")

        description = str(payload["description"]).strip()
        if not description:
            raise ValueError("Description cannot be empty")

        merchant = payload.get("merchant")
        if merchant is not None:
            merchant = str(merchant).strip() or None

        happened_at_raw = str(payload["happened_at"]).strip()
        try:
            happened_at = datetime.fromisoformat(happened_at_raw)
        except ValueError as error:
            raise ValueError("Invalid happened_at; use ISO format") from error

        # A date without a time is a calendar day, not midnight: it is kept as that date at 00:00 UTC
        # and marked day-precision, so matching compares days instead of hours.
        precision = "day" if _DATE_ONLY.match(happened_at_raw) else "minute"
        if happened_at.tzinfo is None:
            happened_at = happened_at.replace(tzinfo=timezone.utc)
        happened_at = happened_at.astimezone(timezone.utc)

        direction = payload.get("direction")
        if direction is None:
            direction = direction_of(amount)
        elif direction == "expense":
            amount = -abs(amount)
        elif direction == "income":
            amount = abs(amount)
        else:
            raise ValueError("direction must be 'expense' or 'income'")

        source_ref = payload.get("source_ref")
        if source_ref is not None:
            source_ref = str(source_ref).strip() or None

        return TransactionInput(
            amount=amount,
            currency=currency,
            description=description,
            merchant=merchant,
            happened_at=happened_at,
            precision=precision,
            direction=direction,
            source_ref=source_ref,
        )


def _contested(session: StorageSession, blocked_by_event: dict[int, Any]) -> dict[int, Any]:
    """Events whose channel slot is taken but which the record fits as well as their weakest automatic link.

    Only links made by the matcher can be contested: an event holding a link a person confirmed is never reopened.
    """
    contested = {}
    for event_id, features in blocked_by_event.items():
        scores = session.automatic_link_scores(event_id)
        if not scores or features.score < decision_rules.REVIEW_THRESHOLD:
            continue
        if round(min(scores) - features.score, 4) < decision_rules.RUNNER_UP_MARGIN:
            contested[event_id] = features
    return contested


def _channel(source: str, user_id: str) -> str:
    """A channel is one source type used by one member."""
    return f"{source}:{user_id}"


def _match_record(record: dict[str, Any], channel: str) -> MatchRecord:
    return MatchRecord(
        group_id=record["group_id"],
        channel=channel,
        amount=record["amount"],
        currency=record["currency"],
        direction=record["direction"],
        happened_at=record["happened_at"],
        precision=record["happened_at_precision"],
        merchant_text=record["merchant"] or record["description"],
    )


def _match_record_of(existing: TransactionRecord) -> MatchRecord:
    # A notification's description is "card_purchase:<merchant>", so the merchant is always set there.
    return MatchRecord(
        group_id=existing.group_id,
        channel=_channel(existing.source, existing.user_id),
        amount=existing.amount,
        currency=existing.currency,
        direction=existing.direction,
        happened_at=existing.happened_at,
        precision=existing.happened_at_precision,
        merchant_text=existing.merchant or existing.description,
        id=existing.id,
        event_id=existing.event_id,
    )


def _retarget_reviews(session: StorageSession, group_id: str, emptied_event: int, new_event: int) -> None:
    """Open reviews that pointed at an event whose records all moved now point where they went."""
    for review in session.open_reviews_for_event(emptied_event):
        session.insert_decision(
            group_id=group_id,
            transaction_id=int(review["transaction_id"]),
            candidate_event_id=new_event,
            outcome="needs_review",
            features={**(review["features"] or {}), "retargeted_from_event_id": emptied_event},
            matcher_version=review["matcher_version"],
            decided_by="system",
            supersedes_id=int(review["id"]),
        )
    # A retargeted contested review flags its new candidate event too.
    session.refresh_review_state(new_event)


def _store_new_event(
    session: StorageSession,
    record: dict[str, Any],
    outcome: str,
    candidate_event_id: int | None,
    details: dict[str, Any] | None,
) -> StoreResult:
    """Give the record its own event; under needs_review it stays flagged until a member decides."""
    event_id = session.create_event(
        group_id=record["group_id"],
        amount=record["amount"],
        currency=record["currency"],
        direction=record["direction"],
        happened_at=record["happened_at"],
        merchant=record["merchant"],
        category=record["category"],
        review_state="clear",
    )
    transaction_id = session.insert_record(**record, event_id=event_id)
    session.refresh_event(event_id)
    session.insert_decision(
        group_id=record["group_id"],
        transaction_id=transaction_id,
        candidate_event_id=candidate_event_id,
        outcome=outcome,
        features=details,
        matcher_version=MATCHER_VERSION,
    )
    session.refresh_review_state(event_id)
    return StoreResult(transaction_id, event_id, outcome)
