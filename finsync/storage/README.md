# `finsync/storage/` — persistence

SQLite persistence for group memberships, transactions, events and match decisions.

| File | Contents |
| --- | --- |
| `sqlite.py` | `FinSyncStorage` (schema and migrations, queries, `transaction()`), `StorageSession` (reads and writes inside one transaction), `TransactionRecord`, `EventRecord` |
| `__init__.py` | Public names |

## Schema (current)

| Table | Columns |
| --- | --- |
| `group_memberships` | `user_id`, `group_id` (primary key on both) |
| `transactions` | `id`, `user_id`, `group_id`, `amount` (decimal as text), `currency`, `description`, `merchant`, `category`, `source`, `happened_at` (UTC), `created_at`, `event_id`, `direction`, `happened_at_precision`, `fingerprint`, `duplicate_of_id`, `raw_payload`, `source_ref`, `import_batch_id` |
| `events` | `id`, `group_id`, display values copied from the primary record, `primary_transaction_id`, `review_state`, `created_at`, `updated_at` |
| `match_decisions` | Append-only: `transaction_id`, `candidate_event_id`, `outcome`, `score`, `features` (JSON), `matcher_version`, `decided_by`, `supersedes_id`, `created_at` |
| `schema_version` | Current version: 2 |

Opening an old database runs the migration to version 2 in one transaction: every existing row becomes its own event with a `separate` decision by `migration`, so nothing is merged after the fact.

The database file defaults to `finsync.db` in the working directory; tests pass a temporary path.

## Rules for this folder

- Parameterised SQL only.
- No business rules; queries filter by `group_id` wherever data is returned.
- Matching never updates or deletes a `transactions` row; it only writes events and decisions.
