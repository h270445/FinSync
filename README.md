# FinSync MVP Prototype

FinSync is a personal and community-focused financial tracking prototype for authorized groups (families, couples, roommates, friends).

This repository now contains a **minimal end-to-end MVP backend flow**:

Android-like notification text -> parser -> normalized transaction -> rule-based categorization -> SQLite persistence -> authorized group access

## What is implemented

- Deterministic parser for supported notification formats.
- Normalized transaction records.
- Manual transaction creation.
- Bulk/manual import path (for Google Sheets-exported rows handled by API payload).
- Basic deterministic transaction categorization.
- Persistent SQLite storage.
- Explicit authorization checks (user must belong to the requested group).
- Clear separation of modules:
  - parsing (`finsync.parser`)
  - categorization (`finsync.categorization`)
  - storage (`finsync.storage`)
  - service/business logic (`finsync.service`)
  - backend API (`finsync.api`)

## Security and privacy guardrails in MVP

- No banking credential access.
- No hard-coded secrets.
- Server-side validation for transaction inputs.
- Group-scoped authorization checks before read/write.
- AI functionality is intentionally out of scope until core data flow is stable.

## Run

```bash
python -m finsync.api
```

Server listens on `http://127.0.0.1:8080`.

## API overview

All endpoints require headers:

- `X-User-Id`
- `X-Group-Id`

A default demo membership (`demo-user` in `demo-group`) is bootstrapped for local MVP demonstration.

Endpoints:

- `POST /v1/notifications/ingest` -> parse + categorize + persist automatic transaction
- `POST /v1/transactions` -> create manual transaction
- `POST /v1/transactions/bulk` -> bulk manual creation
- `GET /v1/transactions` -> list group transactions

## Tests

```bash
python -m unittest discover -s tests -p 'test_*.py'
```
