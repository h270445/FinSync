# API reference

Status: describes the endpoints **implemented** in `finsync/api/server.py`.

## Common rules

- Every request needs the `X-User-Id` and `X-Group-Id` headers; the user must be a member of the group.
- Request and response bodies are JSON objects.

| Status | When |
| --- | --- |
| `201` | Created |
| `200` | Read succeeded |
| `400` | Missing headers, invalid JSON, validation error (`{"error": "..."}`) |
| `403` | User is not a member of the group |
| `404` | Unknown path |

## Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/v1/notifications/ingest` | Parse, categorize, and store a supported notification-like text payload |
| `POST` | `/v1/transactions` | Create a manual transaction |
| `POST` | `/v1/transactions/bulk` | Create multiple transactions from a structured payload |
| `GET` | `/v1/transactions` | List transactions accessible within the requested group |
| `GET` | `/v1/events` | List the group's events (one per purchase), each with its source records |

These endpoints describe the current prototype. They do not imply that direct Android or Google Sheets integrations are available.

### `POST /v1/notifications/ingest`

```json
{"message": "CARD PURCHASE -1234.56 HUF at Tesco on 2026-09-01 13:45"}
```

Response `201`: `{"transaction_id": 1, "event_id": 1, "match_outcome": "separate"}`. `match_outcome` is `separate`, `auto_linked`, `needs_review` or `exact_duplicate` ([matching design](../design/transaction-matching.md)). Supported formats are listed in [finsync/ingestion/README.md](../../finsync/ingestion/README.md).

### `POST /v1/transactions`

```json
{
  "amount": "-4990",
  "currency": "HUF",
  "description": "Monthly bus pass",
  "merchant": "BKK",
  "happened_at": "2026-09-05T07:00:00+00:00"
}
```

`merchant` is optional. `amount` must be non-zero, `currency` a 3-letter code, `happened_at` ISO 8601 (no time zone means UTC; a date without a time, such as `2026-09-05`, is stored as a day-precision value). Optional: `direction` (`expense` or `income`, sets the sign of `amount`) and `source_ref` (a stable client reference such as a sheet row id; resending the same row with the same reference is recognised as an exact duplicate). Response `201`: `{"transaction_id": 2, "event_id": 1, "match_outcome": "auto_linked"}`.

### `POST /v1/transactions/bulk`

```json
{"rows": [ { "amount": "-1000", "currency": "HUF", "description": "Taxi", "happened_at": "2026-09-06T10:00:00+00:00" } ]}
```

Each row has the same fields as a manual transaction. The import is atomic: if any row is invalid (for example a non-object row, a zero or non-finite amount), nothing is stored and the `400` error names the row (`Row 1: Amount cannot be zero`). All rows share one `import_batch_id`. Response `201`: `{"transaction_ids": [3], "results": [{"transaction_id": 3, "event_id": 2, "match_outcome": "separate"}]}`.

### `GET /v1/transactions`

Response `200`:

```json
{"transactions": [{
  "id": 1, "user_id": "demo-user", "group_id": "demo-group",
  "amount": "-1234.56", "currency": "HUF",
  "description": "card_purchase:Tesco", "merchant": "Tesco",
  "category": "groceries", "source": "android_notification",
  "happened_at": "2026-09-01T13:45:00+00:00", "happened_at_precision": "minute",
  "created_at": "...", "event_id": 1, "duplicate_of_id": null
}]}
```

### `GET /v1/events`

Response `200`: `{"events": [{"id": 1, "amount": "-1234.56", "currency": "HUF", "direction": "expense", "happened_at": "...", "merchant": "Tesco", "category": "groceries", "primary_transaction_id": 1, "review_state": "clear", "transactions": [ ... ]}]}`. Display values come from the primary record (a notification first, then the earliest). `review_state` is `needs_review` while an uncertain match waits for a member.

Planned endpoints for review (`/v1/matches/...`, split) are described in the [matching design](../design/transaction-matching.md#user-flow-and-api).
