# `finsync/core/` — application core

The use cases of the system. Each public method of `FinSyncService` is one operation a client can perform; it checks group membership, validates input, calls the domain packages and persists the result.

| File | Contents |
| --- | --- |
| `service.py` | `FinSyncService`, `TransactionInput` (validated manual input), `AuthorizationError` |
| `__init__.py` | Public names: `AuthorizationError`, `FinSyncService`, `TransactionInput` |

## Use cases

| Method | Source written | Notes |
| --- | --- | --- |
| `ingest_notification` | `android_notification` | Parses notification text via `ingestion` |
| `create_manual_transaction` | `manual` | Validates amount, currency, description, ISO timestamp |
| `bulk_create_manual_transactions` | `manual` | One call per row |
| `list_group_transactions` | – | Returns the group's records, newest first |
| `bootstrap_demo_membership` | – | Adds `demo-user` to `demo-group` for local use |

Every use case calls `ensure_authorized(user_id, group_id)` first.

## Planned

- `_store_and_match(record)`: one path that stores a record and runs matching, used by every ingest use case ([design](../../docs/design/transaction-matching.md)).
- Review use cases: list, confirm, reject, split.
