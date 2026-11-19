# `finsync/core/` — application core

The use cases of the system. Each public method of `FinSyncService` is one operation a client can perform; it checks group membership, validates input, calls the domain packages and persists the result.

| File | Contents |
| --- | --- |
| `auth.py` | `TokenService` (create, authenticate, revoke, list API tokens; `list_own`, `create_own`, `revoke_own` for the W8 screen, web session only), `Principal` (member and group of a token or session), `AuthenticationError`, `WebSessionRequired` |
| `overview.py` | `build_overview()`: the W2 month totals per currency, category and member over events, transfers left out, review items counted |
| `service.py` | `FinSyncService`, `TransactionInput` (validated manual input), `StoreResult` (record, event and match outcome), `AuthorizationError` |
| `__init__.py` | Public names: `AuthenticationError`, `AuthorizationError`, `ConflictError`, `FinSyncService`, `NotFoundError`, `Principal`, `ReviewItem`, `StoreResult`, `SessionService`, `TokenService`, `TransactionInput`, `WebSessionRequired` |

## Use cases

| Method | Source written | Notes |
| --- | --- | --- |
| `ingest_notification` | `android_notification` | Parses notification text via `ingestion` |
| `create_manual_transaction` | `manual` | Validates amount, currency, description, ISO timestamp |
| `bulk_create_manual_transactions` | `manual` | All rows in one transaction with one `import_batch_id`; nothing is stored if a row is invalid |
| `list_group_transactions` | – | Returns the group's records, newest first |
| `list_group_events` | – | Returns the group's events with their records |
| `list_open_reviews` | – | Unanswered `needs_review` decisions with the record, the candidate event and the features |
| `confirm_match`, `reject_match` | – | Answer a review: link the record, or keep it separate and never propose the pair again |
| `split_event` | – | Move one original record (with its re-deliveries) out of an event: the undo of a wrong link |
| `overview` | – | W2: a month's totals over deduplicated events ([rules](overview.py)) |
| `list_members`, `set_member_role` | – | W8: the group's members with e-mail and role; an admin changes roles, the last admin stays |
| `list_own_accounts`, `create_own_account`, `delete_own_account` | – | W8: own accounts and counterparties; records naming one become transfers (admin changes the list) |
| `list_merchant_rules`, `create_merchant_rule`, `update_merchant_rule`, `delete_merchant_rule` | – | W8: the group's merchant → category rules; only an admin changes them (`ensure_admin`); a duplicate key is a `ConflictError` |

Every use case calls `ensure_authorized(user_id, group_id)` first. The API takes `user_id` and `group_id` from the caller's token (`TokenService.authenticate`), never from client headers.

Every ingest use case goes through `_store_and_match`, which marks transfers to the group's own accounts and applies the group's merchant rules to the category, stores the record, runs matching ([design](../../docs/design/transaction-matching.md)) and writes the decision in the same database transaction.

Errors: `AuthenticationError` (no valid token, 401), `AuthorizationError` (not a member, 403), `NotFoundError` (id not in this group, 404), `ConflictError` (decision already answered or the action no longer fits, 409), `ValueError` (invalid input, 400).
