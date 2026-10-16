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

These endpoints describe the current prototype. They do not imply that direct Android or Google Sheets integrations are available.

### `POST /v1/notifications/ingest`

```json
{"message": "CARD PURCHASE -1234.56 HUF at Tesco on 2026-09-01 13:45"}
```

Response `201`: `{"transaction_id": 1}`. Supported formats are listed in [finsync/ingestion/README.md](../../finsync/ingestion/README.md).

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

`merchant` is optional. `amount` must be non-zero, `currency` a 3-letter code, `happened_at` ISO 8601 (no time zone means UTC). Response `201`: `{"transaction_id": 2}`.

### `POST /v1/transactions/bulk`

```json
{"rows": [ { "amount": "-1000", "currency": "HUF", "description": "Taxi", "happened_at": "2026-09-06T10:00:00+00:00" } ]}
```

Each row has the same fields as a manual transaction. Response `201`: `{"transaction_ids": [3]}`.

### `GET /v1/transactions`

Response `200`:

```json
{"transactions": [{
  "id": 1, "user_id": "demo-user", "group_id": "demo-group",
  "amount": "-1234.56", "currency": "HUF",
  "description": "card_purchase:Tesco", "merchant": "Tesco",
  "category": "groceries", "source": "android_notification",
  "happened_at": "2026-09-01T13:45:00+00:00", "created_at": "..."
}]}
```

Planned endpoints for matching and review (`/v1/events`, `/v1/matches/...`) are described in the [matching design](../design/transaction-matching.md#user-flow-and-api).
