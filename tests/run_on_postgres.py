"""Run the whole test suite on PostgreSQL instead of SQLite (ADR 0006, step 2).

    python tests/run_on_postgres.py postgresql+psycopg://finsync:finsync@127.0.0.1:5432/finsync_test

The URL can also come from FINSYNC_TEST_DATABASE_URL. The tests keep creating storages from file paths;
here each path becomes its own PostgreSQL schema, so tests stay isolated and a test that reopens the same
path reopens the same data. The schemas are dropped at the end. The few tests that open the SQLite file
directly are skipped (they check SQLite-only behaviour: the pre-Alembic migrations and the raw file).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import unittest
from urllib.parse import quote

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parent))

from finsync.storage import database  # noqa: E402


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FINSYNC_TEST_DATABASE_URL")
    if not url:
        print(__doc__)
        return 2
    os.environ["FINSYNC_TEST_DATABASE_URL"] = url
    admin = create_engine(url, poolclass=NullPool)
    created: list[str] = []
    original = database.database_url

    def per_test_schema(db: str) -> str:
        if "://" in db:
            return original(db)
        schema = "t_" + hashlib.sha256(str(Path(db).resolve()).encode()).hexdigest()[:16]
        if schema not in created:
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            created.append(schema)
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}options={quote(f'-csearch_path={schema}')}"

    database.database_url = per_test_schema
    try:
        suite = unittest.defaultTestLoader.discover(str(TESTS))
        result = unittest.TextTestRunner(verbosity=1).run(suite)
    finally:
        for schema in created:  # one transaction each: dropping them all at once runs out of lock slots
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin.dispose()
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
