from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from finsync.categorization import categorize_transaction
from finsync.ingestion import parse_notification
from finsync.storage import FinSyncStorage, TransactionRecord


class AuthorizationError(PermissionError):
    """Raised when user is not authorized for group access."""


@dataclass(frozen=True)
class TransactionInput:
    amount: Decimal
    currency: str
    description: str
    merchant: str | None
    happened_at: datetime


class FinSyncService:
    def __init__(self, storage: FinSyncStorage) -> None:
        self._storage = storage

    def bootstrap_demo_membership(self) -> None:
        self._storage.add_group_membership("demo-user", "demo-group")

    def ensure_authorized(self, user_id: str, group_id: str) -> None:
        if not self._storage.is_user_in_group(user_id, group_id):
            raise AuthorizationError("User is not authorized for this group")

    def ingest_notification(self, user_id: str, group_id: str, message: str) -> int:
        self.ensure_authorized(user_id, group_id)
        parsed = parse_notification(message)
        category = categorize_transaction(parsed.description + " " + parsed.merchant_or_counterparty)
        return self._storage.insert_transaction(
            user_id=user_id,
            group_id=group_id,
            amount=parsed.amount,
            currency=parsed.currency,
            description=parsed.description,
            merchant=parsed.merchant_or_counterparty,
            category=category,
            source="android_notification",
            happened_at=parsed.happened_at,
        )

    def create_manual_transaction(self, user_id: str, group_id: str, payload: dict[str, Any]) -> int:
        self.ensure_authorized(user_id, group_id)
        tx = self._validate_transaction_payload(payload)
        category = categorize_transaction(f"{tx.description} {tx.merchant or ''}")
        return self._storage.insert_transaction(
            user_id=user_id,
            group_id=group_id,
            amount=tx.amount,
            currency=tx.currency,
            description=tx.description,
            merchant=tx.merchant,
            category=category,
            source="manual",
            happened_at=tx.happened_at,
        )

    def bulk_create_manual_transactions(
        self,
        user_id: str,
        group_id: str,
        rows: list[dict[str, Any]],
    ) -> list[int]:
        self.ensure_authorized(user_id, group_id)
        created: list[int] = []
        for row in rows:
            created.append(self.create_manual_transaction(user_id, group_id, row))
        return created

    def list_group_transactions(self, user_id: str, group_id: str) -> list[TransactionRecord]:
        self.ensure_authorized(user_id, group_id)
        return self._storage.list_transactions(group_id)

    @staticmethod
    def _validate_transaction_payload(payload: dict[str, Any]) -> TransactionInput:
        required = {"amount", "currency", "description", "happened_at"}
        missing = required - payload.keys()
        if missing:
            raise ValueError(f"Missing fields: {', '.join(sorted(missing))}")

        try:
            amount = Decimal(str(payload["amount"]))
        except (InvalidOperation, ValueError) as error:
            raise ValueError("Invalid amount") from error
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

        if happened_at.tzinfo is None:
            happened_at = happened_at.replace(tzinfo=timezone.utc)

        return TransactionInput(
            amount=amount,
            currency=currency,
            description=description,
            merchant=merchant,
            happened_at=happened_at,
        )
