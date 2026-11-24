"""Application core: every use case (ingest, manual and bulk entry, review, split) as one `FinSyncService`.

Each public method first checks that the member belongs to the group, then runs its writes in one
storage transaction, so a refused or failing request leaves the database unchanged. Every record goes
through the same matching pipeline whatever its source ([matching design](../../docs/design/transaction-matching.md)).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any
import uuid

from finsync.categorization import (
    CATEGORIES,
    TRANSFER,
    MerchantRule,
    OwnAccount,
    categorize_record,
    is_transfer,
    merchant_key,
    own_account_key,
    validate_rule,
)
from finsync.categorization.dictionary import find_merchant
from finsync.categorization.hybrid import HIGH
from finsync.core.overview import Overview, build_overview, is_uncertain, lines_add_up, parse_month
from finsync.ingestion import ColumnMapping, ImportRow, RowError, parse_export, parse_notification, parse_xlsx
from finsync.ingestion.csv_import import normalize_content
from finsync.ingestion.local_time import local_to_utc
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
from finsync.matching.normalize import local_date
from finsync.matching.scoring import DAY_WINDOW_DAYS
from finsync.storage import (
    ADMIN,
    CategoryLineRecord,
    ROLES,
    EventRecord,
    FinSyncStorage,
    MerchantCategoryRecord,
    OwnAccountRecord,
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


# A category a member decided: never overwritten by automation (categorization design, order of precedence).
SOURCE_USER = "user"
# A record naming one of the group's own accounts (W8) is a transfer.
SOURCE_OWN_ACCOUNT = "own_account"
# At most this many category lines per event: a receipt split by hand, not an itemised import.
MAX_CATEGORY_LINES = 20


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


@dataclass(frozen=True)
class CategoryCorrection:
    """A member's category decision on an event, and what it did to the group's merchant rules.

    `merchant_rule_outcome` is None when the member did not ask to remember the category, otherwise
    `created`, `confirmed`, `updated` (an admin changed the rule) or `kept` (a member cannot change an
    existing rule; an admin does that on W8)."""

    event: EventRecord
    merchant_rule_outcome: str | None = None
    merchant_rule: MerchantCategoryRecord | None = None


@dataclass(frozen=True)
class ImportResult:
    """A file import or its preview. `results` is empty for a preview or a file that was already imported."""

    import_batch_id: str
    already_imported: bool
    rows: list[ImportRow]
    errors: list[RowError]
    results: list[StoreResult]


class FinSyncService:
    def __init__(self, storage: FinSyncStorage) -> None:
        self._storage = storage

    def ensure_authorized(self, user_id: str, group_id: str) -> None:
        if not self._storage.is_user_in_group(user_id, group_id):
            raise AuthorizationError("User is not authorized for this group")

    def ensure_admin(self, user_id: str, group_id: str) -> None:
        """Group settings are changed only by an admin of the group (author's decision, 2026-11-19)."""
        role = self._storage.member_role(user_id, group_id)
        if role is None:
            raise AuthorizationError("User is not authorized for this group")
        if role != ADMIN:
            raise AuthorizationError("Only an admin of the group can change this setting")

    def ingest_notification(
        self,
        user_id: str,
        group_id: str,
        message: str,
        *,
        title: str | None = None,
        posted_at: str | None = None,
        source_ref: str | None = None,
        device_zone: str | None = None,
    ) -> StoreResult:
        """Store one bank notification.

        The Android app also sends the notification's title, ``posted_at`` (the phone's post time,
        an ISO 8601 instant with offset, ADR 0008) and ``source_ref`` (the bank's transaction id
        when the notification carries one). Their canonical JSON is the raw payload, so a retry of
        the same notification is recognised as a re-delivery, while two identical texts with
        different times or references stay two records.

        ``device_zone`` (the phone's zone id when it captured the notification) is kept in
        the raw payload for diagnosis only (ADR 0008, point 6): it decides neither the time nor the
        calendar day, and it is not part of the identity, so a retry still counts once.
        """
        self.ensure_authorized(user_id, group_id)
        raw = message.strip()
        parsed = parse_notification(raw)
        happened_at = _instant(posted_at) if posted_at is not None else parsed.happened_at
        if happened_at is None:
            raise ValueError("posted_at is required: the notification text has no time")
        source_ref = (source_ref or "").strip() or None
        device_zone = _zone_name(device_zone)
        identity = None
        if title is not None or posted_at is not None or source_ref is not None:
            fields = {
                "text": raw,
                "title": (title or "").strip() or None,
                "posted_at": happened_at.astimezone(timezone.utc).isoformat() if posted_at is not None else None,
                "source_ref": source_ref,
            }
            identity = json.dumps(fields, sort_keys=True, ensure_ascii=False)
            raw = identity if device_zone is None else json.dumps(
                {**fields, "device_zone": device_zone}, sort_keys=True, ensure_ascii=False
            )
        record = {
            "user_id": user_id,
            "group_id": group_id,
            "amount": parsed.amount,
            "currency": parsed.currency,
            "description": parsed.description,
            "merchant": parsed.merchant_or_counterparty,
            "source": "android_notification",
            "happened_at": happened_at.astimezone(timezone.utc),
            "direction": direction_of(parsed.amount),
            "happened_at_precision": "minute",
            "raw_payload": raw,
            "source_ref": source_ref,
        }
        if identity is not None:
            record["identity"] = identity
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

    def import_file(
        self,
        user_id: str,
        group_id: str,
        content: str | bytes,
        mapping: ColumnMapping | None = None,
        *,
        dry_run: bool = False,
    ) -> ImportResult:
        """Import a spreadsheet export, CSV as text or XLSX as bytes: every row or none, each through the matching pipeline.

        The batch id is the SHA-256 of the file, so importing the same file again is refused (409) before
        anything is stored. A row's `source_ref` is the bank's reference when the export has one, otherwise
        a hash of the row and how many identical rows came before it in the file: an overlapping later
        export repeats the same references, so its known rows become re-deliveries. A second identical row
        within one file may be a second purchase (two equal tickets) or an error in the export, so it gets its
        own event and goes to review against the first (author's decision, 2026-11-12: better to ask than to
        be wrong). With `dry_run`, nothing is written and the rows and errors are returned for the preview.
        """
        self.ensure_authorized(user_id, group_id)
        if isinstance(content, bytes):
            batch_id = "file-" + hashlib.sha256(content).hexdigest()
            parsed = parse_xlsx(content, mapping or ColumnMapping())
        else:
            text = normalize_content(content)
            batch_id = "file-" + hashlib.sha256(text.encode("utf-8")).hexdigest()
            parsed = parse_export(text, mapping or ColumnMapping())
        already = self._storage.import_batch_exists(group_id, batch_id)
        if dry_run:
            return ImportResult(batch_id, already, parsed.rows, parsed.errors, [])
        if already:
            raise ConflictError("This file was already imported")
        if parsed.errors:
            listed = "; ".join(f"Line {error.line}: {error.error}" for error in parsed.errors[:5])
            more = f" (and {len(parsed.errors) - 5} more)" if len(parsed.errors) > 5 else ""
            raise ValueError(f"Nothing was imported. {listed}{more}")
        seen: dict[tuple[str, ...], int] = {}
        records: list[tuple[dict[str, Any], tuple[str, ...] | None]] = []
        for row in parsed.rows:
            reference = row.reference
            key = None
            if reference is None:
                key = (row.happened_on.isoformat(), str(row.amount), row.currency, row.description, row.merchant or "")
                seen[key] = seen.get(key, 0) + 1
                reference = "row-" + hashlib.sha256(json.dumps([*key, seen[key]]).encode("utf-8")).hexdigest()[:24]
            records.append((self._file_record(user_id, group_id, row, reference, batch_id), key))
        with self._storage.transaction() as session:
            # Checked again inside the write unit: two uploads of one file at the same time import it once.
            if session.import_batch_exists(group_id, batch_id):
                raise ConflictError("This file was already imported")
            first_of: dict[tuple[str, ...], StoreResult] = {}
            results = []
            for record, key in records:
                first = first_of.get(key) if key is not None else None
                if first is None:
                    result = self._store_and_match(session, record)
                    if key is not None:
                        first_of[key] = result
                else:
                    result = _store_identical_row(session, record, first)
                results.append(result)
        return ImportResult(batch_id, False, parsed.rows, [], results)

    @staticmethod
    def _file_record(user_id: str, group_id: str, row: ImportRow, reference: str, batch_id: str) -> dict[str, Any]:
        # An export's date is the booking date, a calendar day: stored as that date at 00:00 UTC with day
        # precision, like a date-only manual entry (ADR 0008, point 4).
        happened_at = datetime(row.happened_on.year, row.happened_on.month, row.happened_on.day, tzinfo=timezone.utc)
        if row.reference is not None:
            # The bank's id names the booking: a later export that words the description differently is
            # still the same row. Amount and currency stay in, so a reused id with another amount is not.
            fields: dict[str, Any] = {"amount": str(row.amount), "currency": row.currency, "source_ref": reference}
        else:
            fields = {
                "amount": str(row.amount),
                "currency": row.currency,
                "description": row.description,
                "merchant": row.merchant,
                "happened_at": row.happened_on.isoformat(),
                "source_ref": reference,
            }
        return {
            "user_id": user_id,
            "group_id": group_id,
            "amount": row.amount,
            "currency": row.currency,
            "description": row.description,
            "merchant": row.merchant,
            "source": "file_import",
            "happened_at": happened_at,
            "direction": direction_of(row.amount),
            "happened_at_precision": "day",
            "raw_payload": canonical_row(fields),
            "source_ref": reference,
            "import_batch_id": batch_id,
        }

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
        _classify(session, record)
        channel = _channel(record["source"], record["user_id"])
        # The identity is the raw payload unless the caller set a narrower one (the notification
        # without its diagnostic device zone).
        record["fingerprint"] = fingerprint(group_id, channel, record.pop("identity", record["raw_payload"]))

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

    # W8 merchant → category rules. Every member reads them; only an admin of the group changes them
    # (author's decision, 2026-11-19). A rule applies to records stored after it, not to existing
    # events; changing those is the category correction's job (logged).

    def list_merchant_rules(self, user_id: str, group_id: str) -> list[MerchantCategoryRecord]:
        self.ensure_authorized(user_id, group_id)
        return self._storage.list_merchant_categories(group_id)

    def create_merchant_rule(self, user_id: str, group_id: str, merchant: str, category: str) -> MerchantCategoryRecord:
        self.ensure_admin(user_id, group_id)
        label, key, category = validate_rule(merchant, category)
        try:
            rule_id = self._storage.insert_merchant_category(group_id, key, label, category, user_id)
        except ValueError as error:
            raise ConflictError(f"The group already has a rule for this merchant ({key})") from error
        return self._merchant_rule(group_id, rule_id)

    def update_merchant_rule(
        self, user_id: str, group_id: str, rule_id: int, merchant: str, category: str
    ) -> MerchantCategoryRecord:
        self.ensure_admin(user_id, group_id)
        label, key, category = validate_rule(merchant, category)
        try:
            updated = self._storage.update_merchant_category(group_id, rule_id, key, label, category)
        except ValueError as error:
            raise ConflictError(f"The group already has a rule for this merchant ({key})") from error
        if not updated:
            raise NotFoundError("Rule not found")
        return self._merchant_rule(group_id, rule_id)

    def delete_merchant_rule(self, user_id: str, group_id: str, rule_id: int) -> MerchantCategoryRecord:
        self.ensure_admin(user_id, group_id)
        rule = self._merchant_rule(group_id, rule_id)
        self._storage.delete_merchant_category(group_id, rule_id)
        return rule

    def _merchant_rule(self, group_id: str, rule_id: int) -> MerchantCategoryRecord:
        rule = self._storage.get_merchant_category(group_id, rule_id)
        if rule is None:
            raise NotFoundError("Rule not found")
        return rule

    # W8 own accounts and counterparties: records naming one are transfers within the group. Every
    # member reads the list; only an admin changes it. Like rules, it applies to records stored after it.

    def list_own_accounts(self, user_id: str, group_id: str) -> list[OwnAccountRecord]:
        self.ensure_authorized(user_id, group_id)
        return self._storage.list_own_accounts(group_id)

    def create_own_account(self, user_id: str, group_id: str, label: str) -> OwnAccountRecord:
        self.ensure_admin(user_id, group_id)
        label, kind, key = own_account_key(label)
        try:
            return self._storage.insert_own_account(group_id, label, kind, key, user_id)
        except ValueError as error:
            raise ConflictError("The group already lists this account or name") from error

    def delete_own_account(self, user_id: str, group_id: str, account_id: int) -> OwnAccountRecord:
        self.ensure_admin(user_id, group_id)
        deleted = self._storage.delete_own_account(group_id, account_id)
        if deleted is None:
            raise NotFoundError("Own account not found")
        return deleted

    def list_members(self, user_id: str, group_id: str) -> list[tuple[str, str | None, str]]:
        """W8: the group's members (id, sign-in e-mail address, role)."""
        self.ensure_authorized(user_id, group_id)
        return self._storage.list_group_members(group_id)

    def set_member_role(self, user_id: str, group_id: str, member_id: str, role: str) -> None:
        """W8: an admin makes another member admin or member. The group always keeps one admin."""
        self.ensure_admin(user_id, group_id)
        if role not in ROLES:
            raise ValueError(f"role must be one of: {', '.join(ROLES)}")
        try:
            changed = self._storage.set_member_role(member_id, group_id, role)
        except ValueError as error:
            raise ConflictError(str(error)) from error
        if not changed:
            raise NotFoundError("Member not found")

    def overview(self, user_id: str, group_id: str, month: str | None = None) -> Overview:
        """W2: the month's totals over deduplicated events (see finsync/core/overview.py for the rules)."""
        self.ensure_authorized(user_id, group_id)
        today = local_date(datetime.now(timezone.utc), "minute")
        return build_overview(self._storage.list_events(group_id), parse_month(month, today))

    # Category correction (categorization design: mixed baskets, money transfers, review in the web app).
    # Every member of the group may correct an event; each change is logged in category_changes in the
    # same transaction, and a member's decision (`user`) is never overwritten by automation.

    def set_event_category(
        self, user_id: str, group_id: str, event_id: int, category: str, *, remember: bool = False
    ) -> CategoryCorrection:
        """Confirm or change an event's category; it becomes the member's decision (`user`, `high`).

        With `remember`, the group's merchant memory learns it (merchant_rule_offer() says when that is
        allowed; otherwise 400 and nothing changes). A member creates or confirms a rule; only an admin
        changes an existing rule to another category, for a member it is `kept`."""
        self.ensure_authorized(user_id, group_id)
        if category not in CATEGORIES:
            raise ValueError(f"category must be one of: {', '.join(CATEGORIES)}")
        is_admin = self._storage.member_role(user_id, group_id) == ADMIN
        with self._storage.transaction() as session:
            event = _event_in_group(session, group_id, event_id)
            if event.direction == TRANSFER:
                raise ConflictError("The event is a transfer; unmark it as a transfer first")
            if event.lines:
                raise ConflictError("The event is split into category lines; change or remove the lines instead")
            offer = merchant_rule_offer(event) if remember else None
            if remember and offer is None:
                raise ValueError(
                    "This category cannot be remembered for the merchant: it sells many kinds of goods, "
                    "the event is mixed, or it has no merchant name"
                )
            old = _category_state(event)
            session.set_event_category(group_id, event_id, category, SOURCE_USER, HIGH)
            new: dict[str, Any] = {"category": category, "source": SOURCE_USER, "confidence": HIGH}
            outcome = rule_id = None
            if offer is not None:
                label, key, _ = validate_rule(offer, category)
                outcome, rule_id = session.remember_merchant_category(
                    group_id, key, label, category, user_id, may_change=is_admin
                )
                new["merchant_rule"] = {"outcome": outcome, "merchant_key": key}
            session.insert_category_change(group_id, event_id, "category", old, new, user_id)
            updated = _event_in_group(session, group_id, event_id)
        rule = self._storage.get_merchant_category(group_id, rule_id) if rule_id is not None else None
        return CategoryCorrection(updated, outcome, rule)

    def set_event_mixed(self, user_id: str, group_id: str, event_id: int, mixed: bool) -> EventRecord:
        """Mark the event as a mixed purchase (several kinds, no amounts given), or unmark it."""
        self.ensure_authorized(user_id, group_id)
        if not isinstance(mixed, bool):
            raise ValueError("mixed must be true or false")
        with self._storage.transaction() as session:
            event = _event_in_group(session, group_id, event_id)
            if event.direction == TRANSFER:
                raise ConflictError("A transfer is not a purchase; it cannot be mixed")
            if event.mixed != mixed:
                session.set_event_mixed(group_id, event_id, mixed)
                session.insert_category_change(group_id, event_id, "mixed", event.mixed, mixed, user_id)
            return _event_in_group(session, group_id, event_id)

    def set_category_lines(self, user_id: str, group_id: str, event_id: int, lines: Any) -> EventRecord:
        """Split the event's amount into category lines, replacing the previous set as one logged change.

        The event's category becomes the category of its largest line, as the member's decision, so the
        list shows the main category; no lines removes the split and keeps that category."""
        self.ensure_authorized(user_id, group_id)
        with self._storage.transaction() as session:
            event = _event_in_group(session, group_id, event_id)
            if event.direction == TRANSFER:
                raise ConflictError("A transfer is not a purchase; it cannot be split into categories")
            parsed = _validate_lines(event, lines)
            old = _lines_state(event.lines)
            if old == _lines_state(parsed):
                return event
            session.replace_category_lines(group_id, event_id, parsed, user_id)
            if parsed:
                main = max(parsed, key=lambda line: abs(line[1]))[0]  # the first of equal lines
                session.set_event_category(group_id, event_id, main, SOURCE_USER, HIGH)
            session.insert_category_change(group_id, event_id, "lines", old, _lines_state(parsed), user_id)
            return _event_in_group(session, group_id, event_id)

    def set_event_transfer(self, user_id: str, group_id: str, event_id: int, transfer: bool) -> EventRecord:
        """Mark the event as a transfer within the group, or undo it (categorization design, money transfers).

        Marking gives the event and its records the direction and category `transfer` as the member's
        decision, so the overview leaves it out and matching never links it to a purchase. Undoing gives the
        records the direction of their amount's sign again and the category the categorizer gives them
        (without the own-accounts list, which the member has just overruled)."""
        self.ensure_authorized(user_id, group_id)
        if not isinstance(transfer, bool):
            raise ValueError("transfer must be true or false")
        with self._storage.transaction() as session:
            event = _event_in_group(session, group_id, event_id)
            if (event.direction == TRANSFER) == transfer:
                return event
            old = {"direction": event.direction, **_category_state(event), "mixed": event.mixed}
            if transfer:
                if event.lines:
                    raise ConflictError("The event is split into category lines; remove the lines first")
                session.classify_event_records(group_id, event_id, TRANSFER, TRANSFER, SOURCE_USER, HIGH)
                session.set_event_category(group_id, event_id, TRANSFER, SOURCE_USER, HIGH)
                session.set_event_mixed(group_id, event_id, False)
            else:
                primary = next(tx for tx in event.transactions if tx.id == event.primary_transaction_id)
                decision = _categorize(session, group_id, primary.merchant, primary.description)
                session.classify_event_records(
                    group_id, event_id, None, decision.category, decision.source, decision.confidence
                )
                session.set_event_category(group_id, event_id, decision.category, decision.source, decision.confidence)
            session.refresh_event(event_id)
            updated = _event_in_group(session, group_id, event_id)
            new = {"direction": updated.direction, **_category_state(updated), "mixed": updated.mixed}
            session.insert_category_change(group_id, event_id, "transfer", old, new, user_id)
            return updated

    def list_category_changes(self, user_id: str, group_id: str, event_id: int) -> list[dict[str, Any]]:
        """The event's category change log (category, mixed, lines, transfer), oldest first."""
        self.ensure_authorized(user_id, group_id)
        changes = self._storage.list_category_changes(group_id, event_id)
        if changes is None:
            raise NotFoundError("Event not found")
        return changes

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

    def list_event_decisions(self, user_id: str, group_id: str, event_id: int) -> list[dict[str, Any]]:
        """The event's decision history: how its records were linked, reviewed and split, oldest first."""
        self.ensure_authorized(user_id, group_id)
        decisions = self._storage.list_event_decisions(group_id, event_id)
        if decisions is None:
            raise NotFoundError("Event not found")
        return decisions

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
                category_source=record.category_source,
                category_confidence=record.category_confidence,
            )
            # The category lines and the mixed flag stay on the original event (categorization design,
            # mixed baskets); the event's lines_match_amount tells the member when they need checking.
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
        # and marked day-precision, so matching compares days instead of hours. A time without an
        # offset is Budapest wall-clock time (ADR 0008).
        precision = "day" if _DATE_ONLY.match(happened_at_raw) else "minute"
        if precision == "day":
            happened_at = happened_at.replace(tzinfo=timezone.utc)
        else:
            happened_at = local_to_utc(happened_at)

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


def _classify(session: StorageSession, record: dict[str, Any]) -> None:
    """Set the record's direction and category from the group's settings, before it is matched.

    1. A record naming one of the group's own accounts is a transfer: direction and category `transfer`,
       so matching never links it to a purchase and the overview leaves it out.
    2. Otherwise the hybrid categorizer's deterministic layer decides (finsync/categorization/hybrid.py):
       the group's merchant rule, then the built-in Hungarian merchant and keyword dictionary.
    """
    accounts = [OwnAccount(a.id, a.kind, a.match_key) for a in session.own_accounts(record["group_id"])]
    if is_transfer(accounts, record.get("merchant"), record.get("description")):
        record["direction"] = TRANSFER
        record["category"] = TRANSFER
        record["category_source"] = SOURCE_OWN_ACCOUNT
        record["category_confidence"] = HIGH
        return
    decision = _categorize(session, record["group_id"], record.get("merchant"), record.get("description"))
    record["category"] = decision.category
    record["category_source"] = decision.source
    record["category_confidence"] = decision.confidence


def _categorize(session: StorageSession, group_id: str, merchant: str | None, description: str | None):
    rules = [MerchantRule(r.id, r.merchant_key, r.category) for r in session.merchant_categories(group_id)]
    return categorize_record(merchant, description, rules)


def merchant_rule_offer(event: EventRecord) -> str | None:
    """The merchant name to offer "always use this for …" with, or None when no rule may be learned.

    Merchant memory learns a rule only for a clear merchant (supervisor, 2026-11-23): never for a merchant
    on the dictionary's mixed-assortment list, an event marked mixed or split into lines, or a transfer.
    The name is the event's merchant, or its primary record's description when it has none, the same text
    a rule is matched against."""
    if event.direction == TRANSFER or event.mixed or event.lines:
        return None
    primary = next((tx for tx in event.transactions if tx.id == event.primary_transaction_id), None)
    name = (event.merchant or (primary.description if primary else "") or "").strip()
    if not name or len(name) > 80 or not merchant_key(name):
        return None
    entry = find_merchant(name)
    if entry is not None and entry.mixed:
        return None
    return name


def _category_state(event: EventRecord) -> dict[str, str]:
    return {
        "category": event.category,
        "source": event.category_source,
        "confidence": event.category_confidence,
    }


def _lines_state(lines: tuple[CategoryLineRecord, ...] | list[tuple[str, Decimal]]) -> list[dict[str, str]]:
    pairs = [(line.category, line.amount) if isinstance(line, CategoryLineRecord) else line for line in lines]
    return [{"category": category, "amount": str(amount)} for category, amount in pairs]


def _validate_lines(event: EventRecord, lines: Any) -> list[tuple[str, Decimal]]:
    """(category, signed amount) pairs, checked against the event; ValueError with the reason otherwise.

    No lines removes the split. Otherwise two to MAX_CATEGORY_LINES lines, each an allowed category once,
    each amount non-zero with the event's sign, adding up to the event's amount exactly."""
    if not isinstance(lines, list):
        raise ValueError("lines must be a list")
    if not lines:
        return []
    if len(lines) < 2:
        raise ValueError("A split needs at least two lines; send no lines to remove the split")
    if len(lines) > MAX_CATEGORY_LINES:
        raise ValueError(f"At most {MAX_CATEGORY_LINES} lines")
    parsed: list[tuple[str, Decimal]] = []
    for index, line in enumerate(lines):
        if not isinstance(line, dict) or not {"category", "amount"} <= line.keys():
            raise ValueError(f"Line {index}: needs category and amount")
        category = line["category"]
        if category not in CATEGORIES:
            raise ValueError(f"Line {index}: category must be one of: {', '.join(CATEGORIES)}")
        if category in (c for c, _ in parsed):
            raise ValueError(f"Line {index}: {category} is already a line; put its amount on one line")
        try:
            amount = Decimal(str(line["amount"]))
        except (InvalidOperation, ValueError) as error:
            raise ValueError(f"Line {index}: invalid amount") from error
        if not amount.is_finite() or amount == 0:
            raise ValueError(f"Line {index}: amount must be a non-zero number")
        if (amount < 0) != (event.amount < 0):
            raise ValueError(f"Line {index}: amount must have the event's sign ({event.amount})")
        parsed.append((category, amount))
    total = sum((amount for _, amount in parsed), Decimal("0"))
    if total != event.amount:
        raise ValueError(f"The lines add up to {total}, not to the event's amount {event.amount}")
    return parsed


def _event_in_group(session: StorageSession, group_id: str, event_id: int) -> EventRecord:
    event = session.get_event(group_id, event_id)
    if event is None:
        raise NotFoundError("Event not found")
    return event


def _instant(value: str) -> datetime:
    """An ISO 8601 instant with an offset (the phone's post time), as UTC."""
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError as error:
        raise ValueError("posted_at must be an ISO 8601 time with an offset") from error
    if parsed.tzinfo is None:
        raise ValueError("posted_at must be an ISO 8601 time with an offset")
    return parsed.astimezone(timezone.utc)


_ZONE_NAME = re.compile(r"[A-Za-z0-9_+:./-]{1,64}")


def _zone_name(value: str | None) -> str | None:
    """The phone's zone id as sent (``Europe/Budapest``, or ``GMT+01:00`` on some phones), or None.

    The zone is only a diagnostic note, so it is not checked against the zone database and a value
    that does not look like a zone id is left out instead of refusing the notification.
    """
    name = (value or "").strip()
    return name if _ZONE_NAME.fullmatch(name) else None


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


def _store_identical_row(session: StorageSession, record: dict[str, Any], first: StoreResult) -> StoreResult:
    """A row identical to an earlier row of the same file: a re-delivery if a previous export already had
    it, otherwise its own event under review against the first row's event."""
    channel = _channel(record["source"], record["user_id"])
    record["fingerprint"] = fingerprint(record["group_id"], channel, record["raw_payload"])
    if session.find_original_by_fingerprint(record["group_id"], record["fingerprint"]) is not None:
        return FinSyncService._store_and_match(session, record)
    # Confirming the review makes this row a re-delivery of the original from the same channel.
    original = next(
        item for item in session.event_originals(first.event_id) if _channel(item.source, item.user_id) == channel
    )
    # Classified like every other record, so a repeated transfer row is a transfer here too.
    _classify(session, record)
    return _store_new_event(session, record, "needs_review", first.event_id, {"identical_row_of_id": original.id})


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
        category_source=record["category_source"],
        category_confidence=record["category_confidence"],
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
