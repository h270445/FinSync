# `finsync/storage/` — persistence

SQLite persistence for group memberships and transactions.

| File | Contents |
| --- | --- |
| `sqlite.py` | `FinSyncStorage` (schema creation, membership and transaction queries) and `TransactionRecord` |
| `__init__.py` | Public names: `FinSyncStorage`, `TransactionRecord` |

## Schema (current)

| Table | Columns |
| --- | --- |
| `group_memberships` | `user_id`, `group_id` (primary key on both) |
| `transactions` | `id`, `user_id`, `group_id`, `amount` (decimal as text), `currency`, `description`, `merchant`, `category`, `source`, `happened_at`, `created_at` |

The database file defaults to `finsync.db` in the working directory; tests pass a temporary path.

## Rules for this folder

- Parameterised SQL only.
- No business rules; queries filter by `group_id` wherever data is returned.
- Planned: a `schema_version` table and migrations for the matching data model (`events`, `match_decisions`), see the [matching design](../../docs/design/transaction-matching.md).
