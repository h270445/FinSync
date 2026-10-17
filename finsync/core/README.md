# `finsync/core/` — application core

The use cases of the system. Each public method of `FinSyncService` is one operation a client can perform; it checks group membership, validates input, calls the domain packages and persists the result.

| File | Contents |
| --- | --- |
| `service.py` | `FinSyncService`, `TransactionInput` (validated manual input), `StoreResult` (record, event and match outcome), `AuthorizationError` |
| `__init__.py` | Public names: `AuthorizationError`, `FinSyncService`, `StoreResult`, `TransactionInput` |

## Use cases

| Method | Source written | Notes |
| --- | --- | --- |
| `ingest_notification` | `android_notification` | Parses notification text via `ingestion` |
| `create_manual_transaction` | `manual` | Validates amount, currency, description, ISO timestamp |
| `bulk_create_manual_transactions` | `manual` | All rows in one transaction with one `import_batch_id`; nothing is stored if a row is invalid |
| `list_group_transactions` | – | Returns the group's records, newest first |
| `list_group_events` | – | Returns the group's events with their records |
| `bootstrap_demo_membership` | – | Adds `demo-user` to `demo-group` for local use |

Every use case calls `ensure_authorized(user_id, group_id)` first.

Every ingest use case goes through `_store_and_match`, which stores the record, runs matching ([design](../../docs/design/transaction-matching.md)) and writes the decision in the same database transaction.

## Planned

- Review use cases: list, confirm, reject, split.
