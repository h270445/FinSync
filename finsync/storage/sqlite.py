from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import sqlite3
from typing import Any, Iterator

SCHEMA_VERSION = 2


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
    event_id: int | None = None
    direction: str = "expense"
    happened_at_precision: str = "minute"
    duplicate_of_id: int | None = None
    source_ref: str | None = None
    import_batch_id: str | None = None


@dataclass(frozen=True)
class EventRecord:
    id: int
    group_id: str
    amount: Decimal
    currency: str
    direction: str
    happened_at: datetime
    merchant: str | None
    category: str
    primary_transaction_id: int | None
    review_state: str
    transactions: tuple[TransactionRecord, ...]


# A needs_review decision nobody has answered yet (no later decision supersedes it).
_OPEN_REVIEW = """
    d.outcome = 'needs_review'
    AND NOT EXISTS (SELECT 1 FROM match_decisions later WHERE later.supersedes_id = d.id)
"""

_TRANSACTION_COLUMNS = """
    id, user_id, group_id, amount, currency, description, merchant, category, source,
    happened_at, created_at, event_id, direction, happened_at_precision, duplicate_of_id,
    source_ref, import_batch_id
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FinSyncStorage:
    def __init__(self, db_path: str = "finsync.db") -> None:
        self._db_path = db_path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        connection = self._connect()
        connection.isolation_level = None
        try:
            connection.execute("BEGIN IMMEDIATE")
            _execute_script(
                connection,
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

                CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
                """,
            )
            row = connection.execute("SELECT MAX(version) AS version FROM schema_version").fetchone()
            if (row["version"] or 1) < 2:
                self._migrate_to_2(connection)
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    @staticmethod
    def _migrate_to_2(connection: sqlite3.Connection) -> None:
        """Add events and match decisions; every existing row becomes its own event, nothing is merged."""
        for column, definition in (
            ("event_id", "INTEGER REFERENCES events(id)"),
            ("direction", "TEXT"),
            ("happened_at_precision", "TEXT NOT NULL DEFAULT 'minute'"),
            ("fingerprint", "TEXT"),
            ("duplicate_of_id", "INTEGER REFERENCES transactions(id)"),
            ("raw_payload", "TEXT"),
            ("source_ref", "TEXT"),
            ("import_batch_id", "TEXT"),
        ):
            connection.execute(f"ALTER TABLE transactions ADD COLUMN {column} {definition}")
        _execute_script(
            connection,
            """
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                amount TEXT NOT NULL,
                currency TEXT NOT NULL,
                direction TEXT NOT NULL,
                happened_at TEXT NOT NULL,
                merchant TEXT,
                category TEXT NOT NULL,
                primary_transaction_id INTEGER REFERENCES transactions(id),
                review_state TEXT NOT NULL DEFAULT 'clear',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE match_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                transaction_id INTEGER NOT NULL REFERENCES transactions(id),
                candidate_event_id INTEGER REFERENCES events(id),
                outcome TEXT NOT NULL,
                score REAL,
                features TEXT,
                matcher_version TEXT NOT NULL,
                decided_by TEXT NOT NULL,
                supersedes_id INTEGER REFERENCES match_decisions(id),
                created_at TEXT NOT NULL
            );

            CREATE INDEX idx_transactions_candidates ON transactions (group_id, currency, happened_at);
            CREATE INDEX idx_transactions_fingerprint ON transactions (group_id, fingerprint);
            CREATE INDEX idx_match_decisions_outcome ON match_decisions (group_id, outcome);
            """,
        )
        connection.execute(
            "UPDATE transactions SET direction = CASE WHEN CAST(amount AS REAL) < 0 THEN 'expense' ELSE 'income' END"
        )
        legacy = connection.execute("SELECT * FROM transactions ORDER BY id").fetchall()
        for row in legacy:
            session = StorageSession(connection)
            event_id = session.create_event(
                group_id=row["group_id"],
                amount=Decimal(row["amount"]),
                currency=row["currency"],
                direction=row["direction"],
                happened_at=row["happened_at"],
                merchant=row["merchant"],
                category=row["category"],
                review_state="clear",
            )
            connection.execute("UPDATE transactions SET event_id = ? WHERE id = ?", (event_id, row["id"]))
            session.refresh_event(event_id)
            session.insert_decision(
                group_id=row["group_id"],
                transaction_id=row["id"],
                candidate_event_id=event_id,
                outcome="separate",
                features=None,
                matcher_version="migration-2",
                decided_by="migration",
            )
        connection.execute("INSERT INTO schema_version (version) VALUES (2)")

    @contextmanager
    def transaction(self) -> Iterator["StorageSession"]:
        """One write unit: everything inside is committed together or rolled back.

        BEGIN IMMEDIATE takes the write lock up front, so two matching runs cannot both
        read the same candidates and link conflicting records.
        """
        connection = self._connect()
        connection.isolation_level = None
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield StorageSession(connection)
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

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

    def list_transactions(self, group_id: str) -> list[TransactionRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT {_TRANSACTION_COLUMNS}
                FROM transactions
                WHERE group_id = ?
                ORDER BY happened_at DESC, id DESC
                """,
                (group_id,),
            ).fetchall()
        return [_row_to_transaction(row) for row in rows]

    def list_events(self, group_id: str) -> list[EventRecord]:
        transactions_by_event: dict[int, list[TransactionRecord]] = {}
        for record in sorted(self.list_transactions(group_id), key=lambda tx: tx.id):
            if record.event_id is not None:
                transactions_by_event.setdefault(record.event_id, []).append(record)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM events WHERE group_id = ? AND review_state != 'empty'
                ORDER BY happened_at DESC, id DESC
                """,
                (group_id,),
            ).fetchall()
        return [
            EventRecord(
                id=int(row["id"]),
                group_id=str(row["group_id"]),
                amount=Decimal(str(row["amount"])),
                currency=str(row["currency"]),
                direction=str(row["direction"]),
                happened_at=datetime.fromisoformat(str(row["happened_at"])),
                merchant=row["merchant"],
                category=str(row["category"]),
                primary_transaction_id=row["primary_transaction_id"],
                review_state=str(row["review_state"]),
                transactions=tuple(transactions_by_event.get(int(row["id"]), ())),
            )
            for row in rows
        ]

    def list_decisions(self, group_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM match_decisions WHERE group_id = ? ORDER BY id", (group_id,)
            ).fetchall()
        return [_decision_dict(row) for row in rows]

    def list_open_reviews(self, group_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM match_decisions d WHERE d.group_id = ? AND {_OPEN_REVIEW} ORDER BY d.id",
                (group_id,),
            ).fetchall()
        return [_decision_dict(row) for row in rows]


class StorageSession:
    """Reads and writes inside one open database transaction."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def find_original_by_fingerprint(self, group_id: str, fingerprint: str) -> TransactionRecord | None:
        row = self._connection.execute(
            f"""
            SELECT {_TRANSACTION_COLUMNS} FROM transactions
            WHERE group_id = ? AND fingerprint = ? AND duplicate_of_id IS NULL
            ORDER BY id LIMIT 1
            """,
            (group_id, fingerprint),
        ).fetchone()
        return _row_to_transaction(row) if row else None

    def candidate_records(
        self, group_id: str, currency: str, start: datetime, end: datetime
    ) -> list[TransactionRecord]:
        """Original records of one group and currency whose time falls in [start, end]."""
        rows = self._connection.execute(
            f"""
            SELECT {_TRANSACTION_COLUMNS} FROM transactions
            WHERE group_id = ? AND currency = ? AND duplicate_of_id IS NULL
              AND happened_at BETWEEN ? AND ?
            ORDER BY id
            """,
            (group_id, currency, start.isoformat(), end.isoformat()),
        ).fetchall()
        return [_row_to_transaction(row) for row in rows]

    def event_originals(self, event_id: int) -> list[TransactionRecord]:
        rows = self._connection.execute(
            f"""
            SELECT {_TRANSACTION_COLUMNS} FROM transactions
            WHERE event_id = ? AND duplicate_of_id IS NULL ORDER BY id
            """,
            (event_id,),
        ).fetchall()
        return [_row_to_transaction(row) for row in rows]

    def create_event(
        self,
        *,
        group_id: str,
        amount: Decimal,
        currency: str,
        direction: str,
        happened_at: datetime | str,
        merchant: str | None,
        category: str,
        review_state: str,
    ) -> int:
        now = _now()
        happened = happened_at.isoformat() if isinstance(happened_at, datetime) else happened_at
        cursor = self._connection.execute(
            """
            INSERT INTO events (
                group_id, amount, currency, direction, happened_at, merchant, category,
                review_state, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (group_id, str(amount), currency, direction, happened, merchant, category, review_state, now, now),
        )
        return int(cursor.lastrowid)

    def insert_record(
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
        event_id: int,
        direction: str,
        happened_at_precision: str,
        fingerprint: str,
        raw_payload: str,
        duplicate_of_id: int | None = None,
        source_ref: str | None = None,
        import_batch_id: str | None = None,
    ) -> int:
        cursor = self._connection.execute(
            """
            INSERT INTO transactions (
                user_id, group_id, amount, currency, description, merchant, category, source,
                happened_at, created_at, event_id, direction, happened_at_precision, fingerprint,
                duplicate_of_id, raw_payload, source_ref, import_batch_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                _now(),
                event_id,
                direction,
                happened_at_precision,
                fingerprint,
                duplicate_of_id,
                raw_payload,
                source_ref,
                import_batch_id,
            ),
        )
        return int(cursor.lastrowid)

    def refresh_event(self, event_id: int) -> None:
        """Copy display values from the primary record: a notification first, then the earliest."""
        originals = self.event_originals(event_id)
        if not originals:
            return
        primary = min(originals, key=lambda record: (record.source != "android_notification", record.id))
        self._connection.execute(
            """
            UPDATE events SET amount = ?, currency = ?, direction = ?, happened_at = ?, merchant = ?,
                category = ?, primary_transaction_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                str(primary.amount),
                primary.currency,
                primary.direction,
                primary.happened_at.isoformat(),
                primary.merchant,
                primary.category,
                primary.id,
                _now(),
                event_id,
            ),
        )

    def refresh_review_state(self, event_id: int) -> None:
        """needs_review while a record of the event has an undecided review, or a later record contests one of
        its automatic links; empty once all records left."""
        if not self._connection.execute("SELECT 1 FROM transactions WHERE event_id = ?", (event_id,)).fetchone():
            state = "empty"
        elif self._connection.execute(
            f"""
            SELECT 1 FROM match_decisions d JOIN transactions t ON t.id = d.transaction_id
            WHERE t.event_id = ? AND {_OPEN_REVIEW}
            UNION ALL
            SELECT 1 FROM match_decisions d
            WHERE d.candidate_event_id = ? AND json_extract(d.features, '$.contested') = 1 AND {_OPEN_REVIEW}
            """,
            (event_id, event_id),
        ).fetchone():
            state = "needs_review"
        else:
            state = "clear"
        self._connection.execute(
            "UPDATE events SET review_state = ?, updated_at = ? WHERE id = ?", (state, _now(), event_id)
        )

    def get_transaction(self, group_id: str, transaction_id: int) -> TransactionRecord | None:
        row = self._connection.execute(
            f"SELECT {_TRANSACTION_COLUMNS} FROM transactions WHERE group_id = ? AND id = ?",
            (group_id, transaction_id),
        ).fetchone()
        return _row_to_transaction(row) if row else None

    def get_decision(self, group_id: str, decision_id: int) -> dict[str, Any] | None:
        row = self._connection.execute(
            "SELECT * FROM match_decisions d WHERE group_id = ? AND id = ?", (group_id, decision_id)
        ).fetchone()
        return _decision_dict(row) if row else None

    def is_superseded(self, decision_id: int) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM match_decisions WHERE supersedes_id = ?", (decision_id,)
        ).fetchone()
        return row is not None

    def automatic_link_scores(self, event_id: int) -> list[float]:
        """Scores of the automatic links that put a current record into this event and no person has decided."""
        rows = self._connection.execute(
            """
            SELECT d.score FROM match_decisions d JOIN transactions t ON t.id = d.transaction_id
            WHERE t.event_id = ? AND t.duplicate_of_id IS NULL
              AND d.candidate_event_id = ? AND d.outcome = 'auto_linked'
              AND NOT EXISTS (SELECT 1 FROM match_decisions later WHERE later.supersedes_id = d.id)
            """,
            (event_id, event_id),
        ).fetchall()
        return [float(row["score"]) for row in rows if row["score"] is not None]

    def link_decision_id(self, transaction_id: int, event_id: int) -> int | None:
        """The latest decision that put this record into this event, if the record's own decision did."""
        row = self._connection.execute(
            """
            SELECT MAX(id) AS id FROM match_decisions
            WHERE transaction_id = ? AND candidate_event_id = ?
              AND outcome IN ('auto_linked', 'confirmed', 'exact_duplicate')
            """,
            (transaction_id, event_id),
        ).fetchone()
        return row["id"]

    def open_reviews_for_event(self, event_id: int) -> list[dict[str, Any]]:
        rows = self._connection.execute(
            f"SELECT * FROM match_decisions d WHERE d.candidate_event_id = ? AND {_OPEN_REVIEW} ORDER BY d.id",
            (event_id,),
        ).fetchall()
        return [_decision_dict(row) for row in rows]

    def rejected_event_ids(self, group_id: str, fingerprint: str) -> set[int]:
        """Events a member has already rejected for a record with this fingerprint."""
        rows = self._connection.execute(
            """
            SELECT d.candidate_event_id FROM match_decisions d JOIN transactions t ON t.id = d.transaction_id
            WHERE d.group_id = ? AND d.outcome = 'rejected' AND t.fingerprint = ?
            """,
            (group_id, fingerprint),
        ).fetchall()
        return {int(row["candidate_event_id"]) for row in rows if row["candidate_event_id"] is not None}

    def move_record(self, transaction_id: int, event_id: int, duplicate_of_id: int | None = None) -> None:
        """Move an original record and its re-deliveries to another event (review and split only)."""
        self._connection.execute(
            "UPDATE transactions SET event_id = ? WHERE id = ? OR duplicate_of_id = ?",
            (event_id, transaction_id, transaction_id),
        )
        if duplicate_of_id is not None:
            self._connection.execute(
                "UPDATE transactions SET duplicate_of_id = ? WHERE id = ? OR duplicate_of_id = ?",
                (duplicate_of_id, transaction_id, transaction_id),
            )

    def insert_decision(
        self,
        *,
        group_id: str,
        transaction_id: int,
        candidate_event_id: int | None,
        outcome: str,
        features: dict[str, Any] | None,
        matcher_version: str,
        decided_by: str = "system",
        supersedes_id: int | None = None,
    ) -> int:
        cursor = self._connection.execute(
            """
            INSERT INTO match_decisions (
                group_id, transaction_id, candidate_event_id, outcome, score, features,
                matcher_version, decided_by, supersedes_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                group_id,
                transaction_id,
                candidate_event_id,
                outcome,
                features.get("score") if features else None,
                json.dumps(features) if features else None,
                matcher_version,
                decided_by,
                supersedes_id,
                _now(),
            ),
        )
        return int(cursor.lastrowid)


def _execute_script(connection: sqlite3.Connection, script: str) -> None:
    # executescript() would commit first; separate statements keep the schema change in one transaction.
    for statement in script.split(";"):
        if statement.strip():
            connection.execute(statement)


def candidate_time_range(happened_at: datetime, days: int) -> tuple[datetime, datetime]:
    return happened_at - timedelta(days=days), happened_at + timedelta(days=days)


def _decision_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {**dict(row), "features": json.loads(row["features"]) if row["features"] else None}


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
        event_id=row["event_id"],
        direction=str(row["direction"]),
        happened_at_precision=str(row["happened_at_precision"]),
        duplicate_of_id=row["duplicate_of_id"],
        source_ref=row["source_ref"],
        import_batch_id=row["import_batch_id"],
    )
