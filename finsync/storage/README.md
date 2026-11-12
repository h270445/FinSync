# `finsync/storage/` — persistence

Group memberships, API tokens, web sessions, transactions, events and match decisions, on **SQLite or PostgreSQL** through SQLAlchemy Core, with the schema managed by Alembic ([ADR 0006](../../docs/architecture/decisions/0006-framework-based-stack.md), step 2).

| File | Contents |
| --- | --- |
| `database.py` | `FinSyncStorage` (opens the database, brings the schema up to date, one transaction per call, `transaction()` for a write unit), `StorageSession` (reads and writes inside one transaction), the record types |
| `migrations/` | Alembic: `env.py` (runs on the connection `FinSyncStorage` hands over) and `versions/` (hand-written revisions; `0001_baseline.py` is the schema of SQLite version 4) |
| `__init__.py` | Public names |

## How it works

`FinSyncStorage(db)` takes a SQLite file path (`finsync.db`) or a database URL (`postgresql+psycopg://user:password@host/finsync`). On opening, it runs `alembic upgrade head` unless the database is already at the latest revision. Every call opens a connection, runs in one transaction and closes it (no connection pool: the SQLite file is never held open, which matters on Windows).

The queries are plain SQL with `?` placeholders that both databases accept, so the code reads the same as before the switch. The few differences are kept in one place: reading the `contested` flag from the JSON features of a decision.

**Write units run one at a time.** `transaction()` is used by every matching and review step. On SQLite it starts with `BEGIN IMMEDIATE` (the write lock up front); on PostgreSQL it waits for a transaction-scoped advisory lock, released at commit or rollback. So two matching runs can never both read the same candidates and link conflicting records (`tests/test_concurrency.py`). The lock is one for the whole database, like SQLite's; a lock per group is a possible later refinement.

**Types.** Amounts are stored as decimal text (exact) and instants as UTC ISO 8601 text, on both databases, so ordering and range queries behave the same and no value changes on the way. Native `numeric` and `timestamptz` columns would be a later migration.

## Schema (current, Alembic revision `0001`)

| Table | Columns |
| --- | --- |
| `group_memberships` | `user_id`, `group_id` (primary key on both) |
| `api_tokens` | `id`, `user_id`, `group_id`, `name`, `token_hash` (SHA-256, unique), `prefix` (first 8 characters, for display), `created_at`, `last_used_at`, `revoked_at`; the token itself is never stored |
| `member_accounts` | `user_id` (primary key), `email` (unique, lower case), `password_hash` (scrypt with its parameters), `updated_at` |
| `web_sessions` | `id`, `user_id`, `group_id`, `session_hash` (SHA-256, unique), `created_at`, `expires_at`, `revoked_at` |
| `transactions` | `id`, `user_id`, `group_id`, `amount` (decimal as text), `currency`, `description`, `merchant`, `category`, `source`, `happened_at` (UTC), `created_at` (arrival time), `event_id`, `direction`, `happened_at_precision`, `fingerprint`, `duplicate_of_id`, `raw_payload`, `source_ref`, `import_batch_id` |
| `events` | `id`, `group_id`, display values copied from the primary record, `primary_transaction_id`, `review_state`, `created_at`, `updated_at` |
| `match_decisions` | Append-only: `transaction_id`, `candidate_event_id`, `outcome`, `score`, `features` (JSON), `matcher_version`, `decided_by`, `supersedes_id`, `created_at` |

## Migrations

- **A schema change is a new Alembic revision** in `migrations/versions/`, written by hand (the queries use no ORM models, so there is nothing to autogenerate from), with a test that an existing database is upgraded.
- **SQLite files from before Alembic** (with a `schema_version` table, versions 1 to 4) still open: `FinSyncStorage` runs the old hand-written migrations up to version 4 and stamps the file with revision `0001`. `tests/test_storage_schema.py` checks that this path and a new database end with the same schema.
- The version 2 migration turns every existing row into its own event with a `separate` decision by `migration`, so nothing is merged after the fact.

## Tests on PostgreSQL

`python -m unittest discover -s tests` runs on SQLite (seconds). `python tests/run_on_postgres.py <url>` runs the same suite on PostgreSQL, one schema per test database; the few tests that open the SQLite file directly are skipped there ([tests/README.md](../../tests/README.md)).

## Rules for this folder

- Parameterised SQL only, written so both databases accept it; a difference goes into a small dialect check here, never into the service.
- No business rules; queries filter by `group_id` wherever data is returned.
- Matching never updates or deletes a `transactions` row; it only writes events and decisions.
- A schema change needs the author's approval (see the endpoint-and-screen-checklist skill).
