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
        if original is not None and original.event_id is not None:
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
        channels_by_event: dict[int, set[str]] = {}
        for existing in session.candidate_records(group_id, record["currency"], start, end):
            if existing.event_id is None:
                continue
            if existing.event_id not in channels_by_event:
                channels_by_event[existing.event_id] = {
                    _channel(item.source, item.user_id) for item in session.event_originals(existing.event_id)
                }
            if channel in channels_by_event[existing.event_id]:
                continue
            features = score(new, _match_record_of(existing))
            if features is None:
                continue
            current = best_by_event.get(existing.event_id)
            if current is None or features.score > current.score:
                best_by_event[existing.event_id] = features

        decision = decide(best_by_event)
        details = None
        if decision.features is not None:
            details = {**decision.features.as_dict(), "runner_up": decision.runner_up}
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
        review_state="needs_review" if outcome == "needs_review" else "clear",
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
    return StoreResult(transaction_id, event_id, outcome)
