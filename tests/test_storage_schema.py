"""The schema: Alembic creates the same tables as the hand-written SQLite migrations did (ADR 0006, step 2)."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import NullPool

from finsync.storage import FinSyncStorage
from finsync.storage.database import BASELINE_REVISION


def _describe(path: str) -> dict[str, object]:
    """Every table's columns, keys and indexes, as SQLAlchemy reads them back from the file."""
    engine = create_engine(f"sqlite:///{path}", poolclass=NullPool)
    try:
        inspector = inspect(engine)
        described = {}
        for table in sorted(set(inspector.get_table_names()) - {"alembic_version", "schema_version", "sqlite_sequence"}):
            primary_key = inspector.get_pk_constraint(table)["constrained_columns"]
            described[table] = {
                # Two differences that change nothing are evened out: FLOAT and REAL are the same type in
                # SQLite, and the old DDL left primary-key columns formally nullable (NOT NULL is stricter).
                "columns": [
                    (c["name"], str(c["type"]).replace("FLOAT", "REAL"), c["nullable"] and c["name"] not in primary_key,
                     (c["default"] or "").strip("'\""))
                    for c in inspector.get_columns(table)
                ],
                "primary_key": primary_key,
                "foreign_keys": sorted(
                    (tuple(fk["constrained_columns"]), fk["referred_table"], tuple(fk["referred_columns"]))
                    for fk in inspector.get_foreign_keys(table)
                ),
                "indexes": sorted((i["name"], tuple(i["column_names"]), bool(i["unique"])) for i in inspector.get_indexes(table)),
                "unique": sorted(tuple(u["column_names"]) for u in inspector.get_unique_constraints(table)),
            }
        return described
    finally:
        engine.dispose()


@unittest.skipIf(os.environ.get("FINSYNC_TEST_DATABASE_URL"), "compares SQLite files")
class SchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _path(self, name: str) -> str:
        return os.path.join(self.tempdir.name, name)

    def _version_1_file(self) -> str:
        """A database as the first version of FinSync left it: one transactions table."""
        legacy = self._path("legacy.db")
        connection = sqlite3.connect(legacy)
        connection.execute(
            """CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, group_id TEXT NOT NULL,
                amount TEXT NOT NULL, currency TEXT NOT NULL, description TEXT NOT NULL, merchant TEXT,
                category TEXT NOT NULL, source TEXT NOT NULL, happened_at TEXT NOT NULL, created_at TEXT NOT NULL)"""
        )
        connection.close()
        return legacy

    def test_a_file_from_before_alembic_ends_with_the_same_schema_as_a_new_one(self) -> None:
        legacy = self._version_1_file()
        FinSyncStorage(legacy)
        FinSyncStorage(self._path("new.db"))
        self.assertEqual(_describe(legacy), _describe(self._path("new.db")))

    def test_the_legacy_file_is_handed_over_to_alembic_once(self) -> None:
        legacy = self._version_1_file()
        FinSyncStorage(legacy)
        FinSyncStorage(legacy)  # reopening must not run the old migrations again
        connection = sqlite3.connect(legacy)
        try:
            self.assertEqual(connection.execute("SELECT version_num FROM alembic_version").fetchall(), [(BASELINE_REVISION,)])
            self.assertEqual(connection.execute("SELECT MAX(version) FROM schema_version").fetchone(), (4,))
        finally:
            connection.close()

    def test_a_new_database_has_no_legacy_version_table(self) -> None:
        FinSyncStorage(self._path("new.db"))
        connection = sqlite3.connect(self._path("new.db"))
        try:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        finally:
            connection.close()
        self.assertIn("alembic_version", tables)
        self.assertNotIn("schema_version", tables)


if __name__ == "__main__":
    unittest.main()
