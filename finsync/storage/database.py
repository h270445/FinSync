"""Storage on SQLAlchemy Core: SQLite or PostgreSQL behind one interface, every query filtered by group.

`FinSyncStorage` takes a file path (SQLite) or a database URL (`postgresql+psycopg://...`), brings the
schema up to date with Alembic and opens one transaction per call; `StorageSession` is one write unit used
by a service method. The SQL is plain text that both databases accept; the few differences are in
`_Dialect`. Instants are stored as UTC ISO strings in text columns on both, so ordering and range queries
behave the same (ADR 0006, step 2).
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
from typing import Any, Iterator, Mapping, Sequence

from functools import cache

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Connection, CursorResult, Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool

# The last version of the hand-written SQLite migrations. A database at this version is handed over to
# Alembic at revision BASELINE_REVISION, which creates the same schema from scratch.
SCHEMA_VERSION = 4
BASELINE_REVISION = "0001"
_MIGRATIONS = Path(__file__).with_name("migrations")
# Member roles (Alembic revision 0003): an admin changes the group's settings, a member does not.
ADMIN = "admin"
MEMBER = "member"
ROLES = (ADMIN, MEMBER)
# Any constant works: the lock only has to be the same for every write unit (see FinSyncStorage.transaction).
_WRITE_LOCK_KEY = 0x46494E53  # "FINS"


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
    # Who decided the category (`merchant_rule`, `dictionary`, `keyword`, `own_account`, `none`, ...) and
    # whether it is settled (`high`) or a suggestion (`low`); Alembic revision 0006.
    category_source: str = "none"
    category_confidence: str = "low"


@dataclass(frozen=True)
class ApiTokenRecord:
    """An API token as stored: its SHA-256 hash, never the token itself."""

    id: int
    user_id: str
    group_id: str
    name: str
    prefix: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


@dataclass(frozen=True)
class MerchantCategoryRecord:
    """A group's merchant → category rule (W8), the first layer of the hybrid categorizer."""

    id: int
    group_id: str
    merchant_key: str
    merchant_label: str
    category: str
    times_confirmed: int
    created_by: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class OwnAccountRecord:
    """One of the group's own accounts or counterparties (W8): records naming it are transfers."""

    id: int
    group_id: str
    label: str
    kind: str
    match_key: str
    created_by: str
    created_at: datetime


@dataclass(frozen=True)
class WebSessionRecord:
    """A web app session as stored: the SHA-256 hash of its id, never the id itself."""

    id: int
    user_id: str
    group_id: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


@dataclass(frozen=True)
class CategoryLineRecord:
    """One line of an event split into categories: a part of its amount, with the event's sign."""

    category: str
    amount: Decimal
    created_by: str
    created_at: datetime


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
    # Where the category came from and how sure it is; `user` is a member's decision and is never
    # overwritten by automation (revision 0006).
    category_source: str = "none"
    category_confidence: str = "low"
    # A member said the purchase was of several kinds, without amounts.
    mixed: bool = False
    # The event's amount split into categories by a member; empty when it is not split.
    lines: tuple[CategoryLineRecord, ...] = ()
    # For an `llm` category: the share of the model's samples that agreed (revision 0007).
    category_agreement: float | None = None
    # When the scheduled LLM run may ask about this uncertain event; None when not scheduled.
    llm_due_at: datetime | None = None


# The group's LLM schedule (revision 0007). `never` is the default: nothing leaves the system.
LLM_MODES = ("never", "after_arrival", "daily", "weekly")


@dataclass(frozen=True)
class LlmSettingsRecord:
    group_id: str
    mode: str = "never"
    hours_after: int = 24
    run_time: str = "20:00"
    weekday: int = 6
    monthly_budget_usd: Decimal = Decimal("1.00")
    updated_by: str | None = None
    updated_at: datetime | None = None


# A needs_review decision nobody has answered yet (no later decision supersedes it).
_OPEN_REVIEW = """
    d.outcome = 'needs_review'
    AND NOT EXISTS (SELECT 1 FROM match_decisions later WHERE later.supersedes_id = d.id)
"""

_TRANSACTION_COLUMNS = """
    id, user_id, group_id, amount, currency, description, merchant, category, source,
    happened_at, created_at, event_id, direction, happened_at_precision, duplicate_of_id,
    source_ref, import_batch_id, category_source, category_confidence
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class _Result:
    """Rows as mappings (`row["column"]`), like the sqlite3.Row the queries were written for."""

    def __init__(self, result: CursorResult[Any]) -> None:
        self._result = result

    def fetchone(self) -> Mapping[str, Any] | None:
        return self._result.mappings().fetchone() if self._result.returns_rows else None

    def fetchall(self) -> Sequence[Mapping[str, Any]]:
        return self._result.mappings().fetchall() if self._result.returns_rows else []

    @property
    def rowcount(self) -> int:
        return self._result.rowcount


class _Connection:
    """One open transaction. Takes `?` placeholders, so the SQL reads the same on both databases."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection
        self.dialect = connection.dialect.name

    def execute(self, sql: str, params: Sequence[Any] = ()) -> _Result:
        parts = sql.split("?")
        if len(parts) - 1 != len(params):
            raise ValueError(f"expected {len(parts) - 1} parameters, got {len(params)}")
        named = parts[0] + "".join(f":p{index}{part}" for index, part in enumerate(parts[1:]))
        return _Result(self._connection.execute(text(named), {f"p{i}": value for i, value in enumerate(params)}))

    def insert(self, sql: str, params: Sequence[Any]) -> int:
        """Run an INSERT and return the new row's id (RETURNING works on SQLite 3.35+ and PostgreSQL)."""
        row = self.execute(sql.rstrip() + " RETURNING id", params).fetchone()
        assert row is not None
        return int(row["id"])

    def contested_condition(self) -> str:
        """SQL that is true when a decision's JSON features mark it as contested."""
        if self.dialect == "postgresql":
            return "(CAST(d.features AS jsonb) ->> 'contested') = 'true'"
        return "json_extract(d.features, '$.contested') = 1"


def database_url(db: str) -> str:
    """A database URL as is; anything else is a SQLite file path."""
    return db if "://" in db else f"sqlite:///{db}"


def _engine(url: str) -> Engine:
    # No pool: each call opens and closes its connection, as before. The SQLite file is then never held
    # open (on Windows an open file stays locked), and the tests can create hundreds of storages.
    engine = create_engine(url, poolclass=NullPool)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def _autocommit_driver(dbapi_connection: Any, _record: Any) -> None:
            # Let SQLAlchemy, not the sqlite3 module, decide where transactions begin.
            dbapi_connection.isolation_level = None

        @event.listens_for(engine, "begin")
        def _begin_immediate(connection: Connection) -> None:
            # Take the write lock up front, so two matching runs cannot read the same candidates.
            connection.exec_driver_sql("BEGIN IMMEDIATE")
    return engine


@cache
def _head_revision() -> str | None:
    config = Config()
    config.set_main_option("script_location", str(_MIGRATIONS))
    return ScriptDirectory.from_config(config).get_current_head()


def _alembic_config(connection: Connection) -> Config:
    config = Config()
    config.set_main_option("script_location", str(_MIGRATIONS))
    config.attributes["connection"] = connection
    return config


class FinSyncStorage:
    def __init__(self, db: str = "finsync.db") -> None:
        """`db` is a SQLite file path or a database URL such as `postgresql+psycopg://user:pw@host/finsync`."""
        self.url = database_url(db)
        self._engine = _engine(self.url)
        self._init_schema()

    @property
    def dialect(self) -> str:
        return self._engine.dialect.name

    @property
    def display_url(self) -> str:
        """The database URL with any password replaced by ***, safe to print or log."""
        return self._engine.url.render_as_string(hide_password=True)

    @contextmanager
    def _session(self) -> Iterator[_Connection]:
        """Commits on success, rolls back on error and always closes the connection."""
        with self._engine.begin() as connection:
            yield _Connection(connection)

    def _init_schema(self) -> None:
        """Alembic upgrade; an older SQLite file first runs the hand-written migrations up to version 4."""
        with self._engine.begin() as raw:
            tables = set(inspect(raw).get_table_names())
            if "alembic_version" not in tables and tables & {"transactions", "schema_version"}:
                self._upgrade_legacy(_Connection(raw))
                command.stamp(_alembic_config(raw), BASELINE_REVISION)
            # Opening an up-to-date database is the common case (every request in the tests); skip Alembic then.
            if MigrationContext.configure(raw).get_current_revision() != _head_revision():
                command.upgrade(_alembic_config(raw), "head")

    def _upgrade_legacy(self, connection: _Connection) -> None:
        """The SQLite migrations from before Alembic (schema versions 1 to 4), kept for existing files."""
        if connection.dialect != "sqlite":
            raise RuntimeError("a database without alembic_version must be a SQLite file from before Alembic")
        if True:  # keeps the original indentation of the migration code below
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
            version = (row["version"] if row else None) or 1
            if version < 2:
                self._migrate_to_2(connection)
            if version < 3:
                self._migrate_to_3(connection)
            if version < SCHEMA_VERSION:
                self._migrate_to_4(connection)

    @staticmethod
    def _migrate_to_2(connection: _Connection) -> None:
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
            # Plain SQL against the version 2 schema: StorageSession's event methods use later columns.
            now = _now()
            event_id = connection.insert(
                """
                INSERT INTO events (
                    group_id, amount, currency, direction, happened_at, merchant, category,
                    primary_transaction_id, review_state, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'clear', ?, ?)
                """,
                (
                    row["group_id"], str(Decimal(row["amount"])), row["currency"], row["direction"],
                    row["happened_at"], row["merchant"], row["category"], row["id"], now, now,
                ),
            )
            connection.execute("UPDATE transactions SET event_id = ? WHERE id = ?", (event_id, row["id"]))
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

    @staticmethod
    def _migrate_to_3(connection: _Connection) -> None:
        """Add API tokens; each token belongs to one member of one group."""
        _execute_script(
            connection,
            """
            CREATE TABLE api_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                group_id TEXT NOT NULL,
                name TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                prefix TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_used_at TEXT,
                revoked_at TEXT
            );
            """,
        )
        connection.execute("INSERT INTO schema_version (version) VALUES (3)")

    @staticmethod
    def _migrate_to_4(connection: _Connection) -> None:
        """Add web sign-in: per member an e-mail address and a password hash, and sessions bound to one member and group."""
        _execute_script(
            connection,
            """
            CREATE TABLE member_accounts (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE,
                password_hash TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE web_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                group_id TEXT NOT NULL,
                session_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                revoked_at TEXT
            );
            """,
        )
        connection.execute("INSERT INTO schema_version (version) VALUES (4)")

    @contextmanager
    def transaction(self) -> Iterator["StorageSession"]:
        """One write unit: everything inside is committed together or rolled back.

        Write units run one at a time, so two matching runs cannot both read the same candidates and
        link conflicting records: SQLite takes its write lock with BEGIN IMMEDIATE, PostgreSQL waits for
        a transaction-scoped advisory lock (released at commit or rollback).
        """
        with self._session() as connection:
            if connection.dialect == "postgresql":
                connection.execute("SELECT pg_advisory_xact_lock(?)", (_WRITE_LOCK_KEY,))
            yield StorageSession(connection)

    def add_group_membership(self, user_id: str, group_id: str, role: str | None = None) -> None:
        """Add a member; an existing membership keeps its role. Without a role, the first member of a
        new group becomes its admin and everyone after is a member."""
        with self._session() as connection:
            if role is None:
                first = connection.execute(
                    "SELECT 1 FROM group_memberships WHERE group_id = ?", (group_id,)
                ).fetchone() is None
                role = ADMIN if first else MEMBER
            connection.execute(
                "INSERT INTO group_memberships (user_id, group_id, role) VALUES (?, ?, ?) ON CONFLICT DO NOTHING",
                (user_id, group_id, role),
            )

    def member_role(self, user_id: str, group_id: str) -> str | None:
        """`admin` or `member`; None when the user is not in the group."""
        with self._session() as connection:
            row = connection.execute(
                "SELECT role FROM group_memberships WHERE user_id = ? AND group_id = ?", (user_id, group_id)
            ).fetchone()
        return str(row["role"]) if row else None

    def set_member_role(self, user_id: str, group_id: str, role: str) -> bool:
        """Change a member's role. Refuses (ValueError) to leave the group without an admin."""
        with self._session() as connection:
            current = connection.execute(
                "SELECT role FROM group_memberships WHERE user_id = ? AND group_id = ?", (user_id, group_id)
            ).fetchone()
            if current is None:
                return False
            if current["role"] == ADMIN and role != ADMIN:
                admins = connection.execute(
                    "SELECT COUNT(*) AS n FROM group_memberships WHERE group_id = ? AND role = ?", (group_id, ADMIN)
                ).fetchone()
                if int(admins["n"]) <= 1:
                    raise ValueError("the group must keep at least one admin")
            connection.execute(
                "UPDATE group_memberships SET role = ? WHERE user_id = ? AND group_id = ?", (role, user_id, group_id)
            )
        return True

    def is_user_in_group(self, user_id: str, group_id: str) -> bool:
        with self._session() as connection:
            row = connection.execute(
                "SELECT 1 FROM group_memberships WHERE user_id = ? AND group_id = ?",
                (user_id, group_id),
            ).fetchone()
        return row is not None

    def remove_group_membership(self, user_id: str, group_id: str) -> None:
        with self._session() as connection:
            connection.execute(
                "DELETE FROM group_memberships WHERE user_id = ? AND group_id = ?", (user_id, group_id)
            )

    def insert_api_token(self, user_id: str, group_id: str, name: str, token_hash: str, prefix: str) -> int:
        with self._session() as connection:
            return connection.insert(
                """
                INSERT INTO api_tokens (user_id, group_id, name, token_hash, prefix, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, group_id, name, token_hash, prefix, _now()),
            )

    def find_api_token(self, token_hash: str) -> ApiTokenRecord | None:
        with self._session() as connection:
            row = connection.execute("SELECT * FROM api_tokens WHERE token_hash = ?", (token_hash,)).fetchone()
        return _row_to_api_token(row) if row else None

    def touch_api_token(self, token_id: int) -> None:
        with self._session() as connection:
            connection.execute("UPDATE api_tokens SET last_used_at = ? WHERE id = ?", (_now(), token_id))

    def revoke_api_token(self, token_id: int) -> bool:
        """Revoke a token; False if it does not exist or was already revoked."""
        with self._session() as connection:
            cursor = connection.execute(
                "UPDATE api_tokens SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL", (_now(), token_id)
            )
        return cursor.rowcount == 1

    def revoke_member_api_token(self, token_id: int, user_id: str, group_id: str) -> ApiTokenRecord | None:
        """Revoke one of a member's own tokens in a group (already revoked is fine); None if it is not theirs."""
        with self._session() as connection:
            connection.execute(
                """
                UPDATE api_tokens SET revoked_at = ?
                WHERE id = ? AND user_id = ? AND group_id = ? AND revoked_at IS NULL
                """,
                (_now(), token_id, user_id, group_id),
            )
            row = connection.execute(
                "SELECT * FROM api_tokens WHERE id = ? AND user_id = ? AND group_id = ?", (token_id, user_id, group_id)
            ).fetchone()
        return _row_to_api_token(row) if row else None

    def list_group_members(self, group_id: str) -> list[tuple[str, str | None, str]]:
        """The group's members with their sign-in e-mail address (if they have one) and role."""
        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT m.user_id, a.email, m.role FROM group_memberships m
                LEFT JOIN member_accounts a ON a.user_id = m.user_id
                WHERE m.group_id = ? ORDER BY m.user_id
                """,
                (group_id,),
            ).fetchall()
        return [(str(row["user_id"]), row["email"], str(row["role"])) for row in rows]

    def list_merchant_categories(self, group_id: str) -> list[MerchantCategoryRecord]:
        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM merchant_categories WHERE group_id = ? ORDER BY merchant_key, id", (group_id,)
            ).fetchall()
        return [_row_to_merchant_category(row) for row in rows]

    def get_merchant_category(self, group_id: str, rule_id: int) -> MerchantCategoryRecord | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM merchant_categories WHERE id = ? AND group_id = ?", (rule_id, group_id)
            ).fetchone()
        return _row_to_merchant_category(row) if row else None

    def insert_merchant_category(self, group_id: str, key: str, label: str, category: str, created_by: str) -> int:
        """Raises ValueError when the group already has a rule for this merchant key."""
        now = _now()
        try:
            with self._session() as connection:
                return connection.insert(
                    """
                    INSERT INTO merchant_categories
                        (group_id, merchant_key, merchant_label, category, created_by, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (group_id, key, label, category, created_by, now, now),
                )
        except IntegrityError as error:
            raise ValueError("duplicate merchant key") from error

    def update_merchant_category(self, group_id: str, rule_id: int, key: str, label: str, category: str) -> bool:
        """False when the rule is not in the group; ValueError when another rule has the key."""
        try:
            with self._session() as connection:
                cursor = connection.execute(
                    """
                    UPDATE merchant_categories SET merchant_key = ?, merchant_label = ?, category = ?, updated_at = ?
                    WHERE id = ? AND group_id = ?
                    """,
                    (key, label, category, _now(), rule_id, group_id),
                )
        except IntegrityError as error:
            raise ValueError("duplicate merchant key") from error
        return cursor.rowcount == 1

    def delete_merchant_category(self, group_id: str, rule_id: int) -> bool:
        with self._session() as connection:
            cursor = connection.execute(
                "DELETE FROM merchant_categories WHERE id = ? AND group_id = ?", (rule_id, group_id)
            )
        return cursor.rowcount == 1

    def list_own_accounts(self, group_id: str) -> list[OwnAccountRecord]:
        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM own_accounts WHERE group_id = ? ORDER BY label, id", (group_id,)
            ).fetchall()
        return [_row_to_own_account(row) for row in rows]

    def insert_own_account(self, group_id: str, label: str, kind: str, key: str, created_by: str) -> OwnAccountRecord:
        """Raises ValueError when the group already lists this account or name."""
        try:
            with self._session() as connection:
                new_id = connection.insert(
                    """
                    INSERT INTO own_accounts (group_id, label, kind, match_key, created_by, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (group_id, label, kind, key, created_by, _now()),
                )
                row = connection.execute("SELECT * FROM own_accounts WHERE id = ?", (new_id,)).fetchone()
        except IntegrityError as error:
            raise ValueError("duplicate own account") from error
        return _row_to_own_account(row)

    def delete_own_account(self, group_id: str, account_id: int) -> OwnAccountRecord | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM own_accounts WHERE id = ? AND group_id = ?", (account_id, group_id)
            ).fetchone()
            if row is None:
                return None
            connection.execute("DELETE FROM own_accounts WHERE id = ? AND group_id = ?", (account_id, group_id))
        return _row_to_own_account(row)

    def list_api_tokens(self, user_id: str | None = None) -> list[ApiTokenRecord]:
        with self._session() as connection:
            if user_id is None:
                rows = connection.execute("SELECT * FROM api_tokens ORDER BY id").fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM api_tokens WHERE user_id = ? ORDER BY id", (user_id,)
                ).fetchall()
        return [_row_to_api_token(row) for row in rows]

    def set_member_password(self, user_id: str, password_hash: str) -> None:
        """Store or replace a member's password hash; every open web session of the member ends."""
        with self._session() as connection:
            connection.execute(
                """
                INSERT INTO member_accounts (user_id, password_hash, updated_at) VALUES (?, ?, ?)
                ON CONFLICT (user_id) DO UPDATE SET password_hash = excluded.password_hash,
                    updated_at = excluded.updated_at
                """,
                (user_id, password_hash, _now()),
            )
            connection.execute(
                "UPDATE web_sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL", (_now(), user_id)
            )

    def set_member_email(self, user_id: str, email: str) -> None:
        """Store or replace a member's sign-in e-mail address (already normalised to lower case).

        Raises ValueError if another member already uses the address.
        """
        try:
            with self._session() as connection:
                connection.execute(
                    """
                    INSERT INTO member_accounts (user_id, email, updated_at) VALUES (?, ?, ?)
                    ON CONFLICT (user_id) DO UPDATE SET email = excluded.email, updated_at = excluded.updated_at
                    """,
                    (user_id, email, _now()),
                )
        except IntegrityError as error:
            raise ValueError("this e-mail address belongs to another member") from error

    def find_member_account(self, login: str) -> tuple[str, str | None] | None:
        """The member id and password hash for a sign-in name: an e-mail address (with "@") or a member id."""
        column = "email" if "@" in login else "user_id"
        with self._session() as connection:
            row = connection.execute(
                f"SELECT user_id, password_hash FROM member_accounts WHERE {column} = ?", (login,)
            ).fetchone()
        if row is None:
            return None
        return str(row["user_id"]), (str(row["password_hash"]) if row["password_hash"] is not None else None)

    def get_member_password(self, user_id: str) -> str | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT password_hash FROM member_accounts WHERE user_id = ?", (user_id,)
            ).fetchone()
        return str(row["password_hash"]) if row and row["password_hash"] is not None else None

    def get_member_email(self, user_id: str) -> str | None:
        with self._session() as connection:
            row = connection.execute("SELECT email FROM member_accounts WHERE user_id = ?", (user_id,)).fetchone()
        return str(row["email"]) if row and row["email"] is not None else None

    def list_member_groups(self, user_id: str) -> list[str]:
        with self._session() as connection:
            rows = connection.execute(
                "SELECT group_id FROM group_memberships WHERE user_id = ? ORDER BY group_id", (user_id,)
            ).fetchall()
        return [str(row["group_id"]) for row in rows]

    def insert_web_session(self, user_id: str, group_id: str, session_hash: str, expires_at: datetime) -> int:
        with self._session() as connection:
            return connection.insert(
                """
                INSERT INTO web_sessions (user_id, group_id, session_hash, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, group_id, session_hash, _now(), expires_at.isoformat()),
            )

    def find_web_session(self, session_hash: str) -> WebSessionRecord | None:
        with self._session() as connection:
            row = connection.execute("SELECT * FROM web_sessions WHERE session_hash = ?", (session_hash,)).fetchone()
        if row is None:
            return None
        return WebSessionRecord(
            id=int(row["id"]),
            user_id=str(row["user_id"]),
            group_id=str(row["group_id"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            expires_at=datetime.fromisoformat(str(row["expires_at"])),
            revoked_at=_optional_time(row["revoked_at"]),
        )

    def revoke_web_session(self, session_id: int) -> bool:
        with self._session() as connection:
            cursor = connection.execute(
                "UPDATE web_sessions SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL", (_now(), session_id)
            )
        return cursor.rowcount == 1

    def import_batch_exists(self, group_id: str, import_batch_id: str) -> bool:
        with self._session() as connection:
            row = connection.execute(
                "SELECT 1 FROM transactions WHERE group_id = ? AND import_batch_id = ? LIMIT 1", (group_id, import_batch_id)
            ).fetchone()
        return row is not None

    def list_transactions(self, group_id: str) -> list[TransactionRecord]:
        with self._session() as connection:
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
        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT * FROM events WHERE group_id = ? AND review_state != 'empty'
                ORDER BY happened_at DESC, id DESC
                """,
                (group_id,),
            ).fetchall()
            lines = _lines_by_event(connection, group_id)
        return [
            _row_to_event(row, tuple(transactions_by_event.get(int(row["id"]), ())), lines.get(int(row["id"]), ()))
            for row in rows
        ]

    # The LLM schedule (revision 0007).

    def get_llm_settings(self, group_id: str) -> LlmSettingsRecord:
        with self._session() as connection:
            return _llm_settings(connection, group_id)

    def llm_cost_since(self, group_id: str, since: datetime) -> Decimal:
        """The group's LLM spending since an instant (the start of the Budapest month)."""
        with self._session() as connection:
            rows = connection.execute(
                "SELECT cost_usd FROM llm_calls WHERE group_id = ? AND created_at >= ?", (group_id, since.isoformat())
            ).fetchall()
        return sum((Decimal(str(row["cost_usd"])) for row in rows), Decimal("0"))

    def due_llm_events(self, now: datetime, limit: int = 100) -> list[tuple[str, int]]:
        """(group, event) pairs whose scheduled LLM time has come, oldest first. Read across groups by the
        server's own runner only; each event is then handled within its own group."""
        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT group_id, id FROM events
                WHERE llm_due_at IS NOT NULL AND llm_due_at <= ? AND review_state != 'empty'
                ORDER BY llm_due_at, id LIMIT ?
                """,
                (now.isoformat(), limit),
            ).fetchall()
        return [(str(row["group_id"]), int(row["id"])) for row in rows]

    def list_category_changes(self, group_id: str, event_id: int) -> list[dict[str, Any]] | None:
        """The event's logged category changes, oldest first; None if the group has no such event."""
        with self._session() as connection:
            if connection.execute(
                "SELECT 1 FROM events WHERE group_id = ? AND id = ?", (group_id, event_id)
            ).fetchone() is None:
                return None
            rows = connection.execute(
                "SELECT * FROM category_changes WHERE group_id = ? AND event_id = ? ORDER BY id",
                (group_id, event_id),
            ).fetchall()
        return [
            {
                **dict(row),
                "old_value": json.loads(row["old_value"]) if row["old_value"] is not None else None,
                "new_value": json.loads(row["new_value"]) if row["new_value"] is not None else None,
            }
            for row in rows
        ]

    def list_decisions(self, group_id: str) -> list[dict[str, Any]]:
        with self._session() as connection:
            rows = connection.execute(
                "SELECT * FROM match_decisions WHERE group_id = ? ORDER BY id", (group_id,)
            ).fetchall()
        return [_decision_dict(row) for row in rows]

    def list_event_decisions(self, group_id: str, event_id: int) -> list[dict[str, Any]] | None:
        """Every decision that names the event or one of its current records, oldest first; None if no such event."""
        with self._session() as connection:
            if connection.execute(
                "SELECT 1 FROM events WHERE group_id = ? AND id = ?", (group_id, event_id)
            ).fetchone() is None:
                return None
            rows = connection.execute(
                """
                SELECT * FROM match_decisions d
                WHERE d.group_id = ?
                  AND (d.candidate_event_id = ?
                       OR d.transaction_id IN (SELECT id FROM transactions WHERE group_id = ? AND event_id = ?))
                ORDER BY d.id
                """,
                (group_id, event_id, group_id, event_id),
            ).fetchall()
        return [_decision_dict(row) for row in rows]

    def list_open_reviews(self, group_id: str) -> list[dict[str, Any]]:
        with self._session() as connection:
            rows = connection.execute(
                f"SELECT * FROM match_decisions d WHERE d.group_id = ? AND {_OPEN_REVIEW} ORDER BY d.id",
                (group_id,),
            ).fetchall()
        return [_decision_dict(row) for row in rows]


class StorageSession:
    """Reads and writes inside one open database transaction."""

    def __init__(self, connection: _Connection) -> None:
        self._connection = connection

    def own_accounts(self, group_id: str) -> list[OwnAccountRecord]:
        """The group's own accounts, read in the write transaction that classifies a new record."""
        rows = self._connection.execute("SELECT * FROM own_accounts WHERE group_id = ? ORDER BY id", (group_id,)).fetchall()
        return [_row_to_own_account(row) for row in rows]

    def merchant_categories(self, group_id: str) -> list[MerchantCategoryRecord]:
        """The group's merchant rules, read in the write transaction that categorizes a new record."""
        rows = self._connection.execute(
            "SELECT * FROM merchant_categories WHERE group_id = ? ORDER BY id", (group_id,)
        ).fetchall()
        return [_row_to_merchant_category(row) for row in rows]

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
        category_source: str = "none",
        category_confidence: str = "low",
    ) -> int:
        now = _now()
        happened = happened_at.isoformat() if isinstance(happened_at, datetime) else happened_at
        return self._connection.insert(
            """
            INSERT INTO events (
                group_id, amount, currency, direction, happened_at, merchant, category,
                category_source, category_confidence, review_state, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                group_id, str(amount), currency, direction, happened, merchant, category,
                category_source, category_confidence, review_state, now, now,
            ),
        )

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
        category_source: str = "none",
        category_confidence: str = "low",
    ) -> int:
        return self._connection.insert(
            """
            INSERT INTO transactions (
                user_id, group_id, amount, currency, description, merchant, category, source,
                happened_at, created_at, event_id, direction, happened_at_precision, fingerprint,
                duplicate_of_id, raw_payload, source_ref, import_batch_id, category_source, category_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                category_source,
                category_confidence,
            ),
        )

    def refresh_event(self, event_id: int) -> None:
        """Copy display values from the primary record: a notification first, then the earliest.

        A category a member decided (`user`) stays: linking or splitting records never overwrites it."""
        originals = self.event_originals(event_id)
        if not originals:
            return
        primary = min(originals, key=lambda record: (record.source != "android_notification", record.id))
        self._connection.execute(
            """
            UPDATE events SET amount = ?, currency = ?, direction = ?, happened_at = ?, merchant = ?,
                primary_transaction_id = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                str(primary.amount),
                primary.currency,
                primary.direction,
                primary.happened_at.isoformat(),
                primary.merchant,
                primary.id,
                _now(),
                event_id,
            ),
        )
        self._connection.execute(
            """
            UPDATE events SET category = ?, category_source = ?, category_confidence = ?,
                category_agreement = CASE WHEN ? = 'llm' THEN category_agreement ELSE NULL END
            WHERE id = ? AND category_source != 'user'
            """,
            (primary.category, primary.category_source, primary.category_confidence, primary.category_source, event_id),
        )

    # Category correction (revision 0006). Every write here is a member's action, logged by the core
    # with insert_category_change in the same transaction.

    def get_event(self, group_id: str, event_id: int) -> EventRecord | None:
        """One event of the group with its records and category lines; None outside the group."""
        row = self._connection.execute(
            "SELECT * FROM events WHERE group_id = ? AND id = ? AND review_state != 'empty'", (group_id, event_id)
        ).fetchone()
        if row is None:
            return None
        records = self._connection.execute(
            f"SELECT {_TRANSACTION_COLUMNS} FROM transactions WHERE group_id = ? AND event_id = ? ORDER BY id",
            (group_id, event_id),
        ).fetchall()
        lines = _lines_by_event(self._connection, group_id, event_id)
        return _row_to_event(row, tuple(_row_to_transaction(r) for r in records), lines.get(event_id, ()))

    def set_event_category(self, group_id: str, event_id: int, category: str, source: str, confidence: str) -> None:
        self._connection.execute(
            """
            UPDATE events SET category = ?, category_source = ?, category_confidence = ?, updated_at = ?
            WHERE group_id = ? AND id = ?
            """,
            (category, source, confidence, _now(), group_id, event_id),
        )

    def set_event_mixed(self, group_id: str, event_id: int, mixed: bool) -> None:
        self._connection.execute(
            "UPDATE events SET mixed = ?, updated_at = ? WHERE group_id = ? AND id = ?",
            (1 if mixed else 0, _now(), group_id, event_id),
        )

    def replace_category_lines(
        self, group_id: str, event_id: int, lines: Sequence[tuple[str, Decimal]], created_by: str
    ) -> None:
        """Replace the event's category lines as one set (an empty set removes them)."""
        self._connection.execute(
            "DELETE FROM event_category_lines WHERE group_id = ? AND event_id = ?", (group_id, event_id)
        )
        now = _now()
        for category, amount in lines:
            self._connection.execute(
                """
                INSERT INTO event_category_lines (group_id, event_id, category, amount, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (group_id, event_id, category, str(amount), created_by, now),
            )

    def classify_event_records(
        self, group_id: str, event_id: int, direction: str | None, category: str, source: str, confidence: str
    ) -> None:
        """Set the classification of every record of the event (a member marks or unmarks a transfer).

        `direction` None gives each record the direction of its amount's sign again."""
        if direction is None:
            self._connection.execute(
                """
                UPDATE transactions SET direction = CASE WHEN amount LIKE ? THEN 'expense' ELSE 'income' END
                WHERE group_id = ? AND event_id = ?
                """,
                ("-%", group_id, event_id),
            )
        else:
            self._connection.execute(
                "UPDATE transactions SET direction = ? WHERE group_id = ? AND event_id = ?",
                (direction, group_id, event_id),
            )
        self._connection.execute(
            """
            UPDATE transactions SET category = ?, category_source = ?, category_confidence = ?
            WHERE group_id = ? AND event_id = ?
            """,
            (category, source, confidence, group_id, event_id),
        )

    def insert_category_change(
        self, group_id: str, event_id: int, kind: str, old: Any, new: Any, changed_by: str
    ) -> int:
        return self._connection.insert(
            """
            INSERT INTO category_changes (group_id, event_id, kind, old_value, new_value, changed_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (group_id, event_id, kind, json.dumps(old), json.dumps(new), changed_by, _now()),
        )

    def llm_settings(self, group_id: str) -> LlmSettingsRecord:
        return _llm_settings(self._connection, group_id)

    def save_llm_settings(self, settings: LlmSettingsRecord, updated_by: str) -> None:
        params = (
            settings.mode, settings.hours_after, settings.run_time, settings.weekday,
            str(settings.monthly_budget_usd), updated_by, _now(),
        )
        exists = self._connection.execute(
            "SELECT 1 FROM group_llm_settings WHERE group_id = ?", (settings.group_id,)
        ).fetchone()
        if exists:
            self._connection.execute(
                """
                UPDATE group_llm_settings SET mode = ?, hours_after = ?, run_time = ?, weekday = ?,
                    monthly_budget_usd = ?, updated_by = ?, updated_at = ?
                WHERE group_id = ?
                """,
                (*params, settings.group_id),
            )
        else:
            self._connection.execute(
                """
                INSERT INTO group_llm_settings (
                    mode, hours_after, run_time, weekday, monthly_budget_usd, updated_by, updated_at, group_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*params, settings.group_id),
            )

    def uncertain_event_ids(self, group_id: str) -> list[tuple[int, datetime]]:
        """(event, arrival of its first record) for the group's events with a suggested category nobody
        settled, which the LLM schedule may cover. Transfers are never sent."""
        rows = self._connection.execute(
            """
            SELECT e.id, MIN(t.created_at) AS arrived FROM events e JOIN transactions t ON t.event_id = e.id
            WHERE e.group_id = ? AND e.review_state != 'empty' AND e.direction != 'transfer'
              AND e.category_source != 'user' AND e.category_confidence != 'high'
            GROUP BY e.id ORDER BY e.id
            """,
            (group_id,),
        ).fetchall()
        return [(int(row["id"]), datetime.fromisoformat(str(row["arrived"]))) for row in rows]

    def set_llm_due(self, group_id: str, event_id: int, due: datetime | None) -> None:
        self._connection.execute(
            "UPDATE events SET llm_due_at = ? WHERE group_id = ? AND id = ?",
            (due.isoformat() if due else None, group_id, event_id),
        )

    def clear_llm_due(self, group_id: str) -> None:
        self._connection.execute("UPDATE events SET llm_due_at = NULL WHERE group_id = ?", (group_id,))

    def set_llm_category(
        self, group_id: str, event_id: int, category: str, source: str, confidence: str, agreement: float | None
    ) -> None:
        """The LLM layer's answer for the event and its records (never over a member's decision)."""
        self._connection.execute(
            """
            UPDATE events SET category = ?, category_source = ?, category_confidence = ?, category_agreement = ?,
                llm_due_at = NULL, updated_at = ?
            WHERE group_id = ? AND id = ? AND category_source != 'user'
            """,
            (category, source, confidence, agreement, _now(), group_id, event_id),
        )
        self._connection.execute(
            """
            UPDATE transactions SET category = ?, category_source = ?, category_confidence = ?
            WHERE group_id = ? AND event_id = ? AND category_source != 'user'
            """,
            (category, source, confidence, group_id, event_id),
        )

    def insert_llm_call(
        self, *, group_id: str, event_id: int, requested_by: str, model: str, new_calls: int,
        input_tokens: int, output_tokens: int, cost_usd: Decimal,
    ) -> int:
        return self._connection.insert(
            """
            INSERT INTO llm_calls (
                group_id, event_id, requested_by, model, new_calls, input_tokens, output_tokens, cost_usd, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (group_id, event_id, requested_by, model, new_calls, input_tokens, output_tokens, str(cost_usd), _now()),
        )

    def remember_merchant_category(
        self, group_id: str, key: str, label: str, category: str, created_by: str, *, may_change: bool
    ) -> tuple[str, int]:
        """A member's "always use this" for a merchant: (outcome, rule id).

        No rule yet: `created`. A rule with the same category: `confirmed` (times_confirmed + 1). A rule
        with another category: `updated` when `may_change` (an admin), otherwise `kept`."""
        row = self._connection.execute(
            "SELECT * FROM merchant_categories WHERE group_id = ? AND merchant_key = ?", (group_id, key)
        ).fetchone()
        now = _now()
        if row is None:
            rule_id = self._connection.insert(
                """
                INSERT INTO merchant_categories (
                    group_id, merchant_key, merchant_label, category, times_confirmed, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (group_id, key, label, category, created_by, now, now),
            )
            return "created", rule_id
        rule_id = int(row["id"])
        if row["category"] == category:
            self._connection.execute(
                "UPDATE merchant_categories SET times_confirmed = times_confirmed + 1, updated_at = ? "
                "WHERE group_id = ? AND id = ?",
                (now, group_id, rule_id),
            )
            return "confirmed", rule_id
        if not may_change:
            return "kept", rule_id
        self._connection.execute(
            "UPDATE merchant_categories SET category = ?, times_confirmed = 1, updated_at = ? WHERE group_id = ? AND id = ?",
            (category, now, group_id, rule_id),
        )
        return "updated", rule_id

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
            WHERE d.candidate_event_id = ? AND {self._connection.contested_condition()} AND {_OPEN_REVIEW}
            """,
            (event_id, event_id),
        ).fetchone():
            state = "needs_review"
        else:
            state = "clear"
        self._connection.execute(
            "UPDATE events SET review_state = ?, updated_at = ? WHERE id = ?", (state, _now(), event_id)
        )

    def import_batch_exists(self, group_id: str, import_batch_id: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM transactions WHERE group_id = ? AND import_batch_id = ? LIMIT 1", (group_id, import_batch_id)
        ).fetchone()
        return row is not None

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
        """Scores of the automatic links that put a current record into this event.

        Empty when a person confirmed a link into the event: such an event is never reopened.
        """
        if self._connection.execute(
            """
            SELECT 1 FROM match_decisions d JOIN transactions t ON t.id = d.transaction_id
            WHERE t.event_id = ? AND d.candidate_event_id = ? AND d.outcome = 'confirmed'
              AND NOT EXISTS (SELECT 1 FROM match_decisions later WHERE later.supersedes_id = d.id)
            """,
            (event_id, event_id),
        ).fetchone():
            return []
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
        return self._connection.insert(
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


def _execute_script(connection: _Connection, script: str) -> None:
    # executescript() would commit first; separate statements keep the schema change in one transaction.
    for statement in script.split(";"):
        if statement.strip():
            connection.execute(statement)


def candidate_time_range(happened_at: datetime, days: int) -> tuple[datetime, datetime]:
    return happened_at - timedelta(days=days), happened_at + timedelta(days=days)


def _optional_time(value: Any) -> datetime | None:
    return datetime.fromisoformat(str(value)) if value is not None else None


def _row_to_own_account(row: Mapping[str, Any]) -> OwnAccountRecord:
    return OwnAccountRecord(
        id=int(row["id"]),
        group_id=str(row["group_id"]),
        label=str(row["label"]),
        kind=str(row["kind"]),
        match_key=str(row["match_key"]),
        created_by=str(row["created_by"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
    )


def _row_to_merchant_category(row: Mapping[str, Any]) -> MerchantCategoryRecord:
    return MerchantCategoryRecord(
        id=int(row["id"]),
        group_id=str(row["group_id"]),
        merchant_key=str(row["merchant_key"]),
        merchant_label=str(row["merchant_label"]),
        category=str(row["category"]),
        times_confirmed=int(row["times_confirmed"]),
        created_by=str(row["created_by"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        updated_at=datetime.fromisoformat(str(row["updated_at"])),
    )


def _row_to_api_token(row: Mapping[str, Any]) -> ApiTokenRecord:
    return ApiTokenRecord(
        id=int(row["id"]),
        user_id=str(row["user_id"]),
        group_id=str(row["group_id"]),
        name=str(row["name"]),
        prefix=str(row["prefix"]),
        created_at=datetime.fromisoformat(str(row["created_at"])),
        last_used_at=_optional_time(row["last_used_at"]),
        revoked_at=_optional_time(row["revoked_at"]),
    )


def _llm_settings(connection: _Connection, group_id: str) -> LlmSettingsRecord:
    row = connection.execute("SELECT * FROM group_llm_settings WHERE group_id = ?", (group_id,)).fetchone()
    if row is None:
        return LlmSettingsRecord(group_id)
    return LlmSettingsRecord(
        group_id=group_id,
        mode=str(row["mode"]),
        hours_after=int(row["hours_after"]),
        run_time=str(row["run_time"]),
        weekday=int(row["weekday"]),
        monthly_budget_usd=Decimal(str(row["monthly_budget_usd"])),
        updated_by=str(row["updated_by"]),
        updated_at=datetime.fromisoformat(str(row["updated_at"])),
    )


def _lines_by_event(
    connection: _Connection, group_id: str, event_id: int | None = None
) -> dict[int, tuple[CategoryLineRecord, ...]]:
    sql = "SELECT * FROM event_category_lines WHERE group_id = ?"
    params: tuple[Any, ...] = (group_id,)
    if event_id is not None:
        sql += " AND event_id = ?"
        params += (event_id,)
    grouped: dict[int, list[CategoryLineRecord]] = {}
    for row in connection.execute(sql + " ORDER BY id", params).fetchall():
        grouped.setdefault(int(row["event_id"]), []).append(
            CategoryLineRecord(
                category=str(row["category"]),
                amount=Decimal(str(row["amount"])),
                created_by=str(row["created_by"]),
                created_at=datetime.fromisoformat(str(row["created_at"])),
            )
        )
    return {key: tuple(value) for key, value in grouped.items()}


def _row_to_event(
    row: Mapping[str, Any], transactions: tuple[TransactionRecord, ...], lines: tuple[CategoryLineRecord, ...]
) -> EventRecord:
    return EventRecord(
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
        transactions=transactions,
        category_source=str(row["category_source"]),
        category_confidence=str(row["category_confidence"]),
        mixed=bool(row["mixed"]),
        lines=lines,
        category_agreement=float(row["category_agreement"]) if row["category_agreement"] is not None else None,
        llm_due_at=_optional_time(row["llm_due_at"]),
    )


def _decision_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    return {**dict(row), "features": json.loads(row["features"]) if row["features"] else None}


def _row_to_transaction(row: Mapping[str, Any]) -> TransactionRecord:
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
        category_source=str(row["category_source"]),
        category_confidence=str(row["category_confidence"]),
    )
