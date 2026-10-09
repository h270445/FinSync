from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import sqlite3
from typing import Iterable


@dataclass(frozen=True)
class TransactionRecord:
    id: int
    user_id: str
    group_id: str
    amount: Decimal
    currency: str
    description: str
    merchant: str | None
    category: str
    source: str
    happened_at: datetime
    created_at: datetime


class FinSyncStorage:
    def __init__(self, db_path: str = "finsync.db") -> None:
        self._db_path = db_path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS group_memberships (
                    user_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    PRIMARY KEY (user_id, group_id)
                );

                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    description TEXT NOT NULL,
                    merchant TEXT,
                    category TEXT NOT NULL,
                    source TEXT NOT NULL,
                    happened_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def add_group_membership(self, user_id: str, group_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO group_memberships (user_id, group_id) VALUES (?, ?)",
                (user_id, group_id),
            )

    def is_user_in_group(self, user_id: str, group_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM group_memberships WHERE user_id = ? AND group_id = ?",
                (user_id, group_id),
            ).fetchone()
        return row is not None

    def insert_transaction(
        self,
        *,
        user_id: str,
        group_id: str,
        amount: Decimal,
        currency: str,
        description: str,
        merchant: str | None,
        category: str,
        source: str,
        happened_at: datetime,
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO transactions (
                    user_id, group_id, amount, currency, description,
                    merchant, category, source, happened_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    group_id,
                    str(amount),
                    currency,
                    description,
                    merchant,
                    category,
                    source,
                    happened_at.isoformat(),
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def list_transactions(self, group_id: str) -> list[TransactionRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, user_id, group_id, amount, currency, description,
                       merchant, category, source, happened_at, created_at
                FROM transactions
                WHERE group_id = ?
                ORDER BY happened_at DESC, id DESC
                """,
                (group_id,),
            ).fetchall()

        return [self._row_to_transaction(row) for row in rows]

    @staticmethod
    def _row_to_transaction(row: sqlite3.Row) -> TransactionRecord:
        return TransactionRecord(
            id=int(row["id"]),
            user_id=str(row["user_id"]),
            group_id=str(row["group_id"]),
            amount=Decimal(str(row["amount"])),
            currency=str(row["currency"]),
            description=str(row["description"]),
            merchant=str(row["merchant"]) if row["merchant"] is not None else None,
            category=str(row["category"]),
            source=str(row["source"]),
            happened_at=datetime.fromisoformat(str(row["happened_at"])),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )
