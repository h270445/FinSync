# `finsync/api/` — HTTP API layer

Translates HTTP requests into calls on `FinSyncService` and maps results and errors to JSON responses.

| File | Contents |
| --- | --- |
| `server.py` | `FinSyncRequestHandler` (routes, header identity, JSON parsing, error mapping) and `run_server()` |
| `__main__.py` | Entry point for `python -m finsync.api` |
| `__init__.py` | Public names: `FinSyncRequestHandler`, `run_server` |

## Behaviour

- Endpoints: `POST /v1/notifications/ingest`, `POST /v1/transactions`, `POST /v1/transactions/bulk`, `GET /v1/transactions`. Full reference: [docs/guides/api.md](../../docs/guides/api.md).
- Identity comes from the `X-User-Id` and `X-Group-Id` headers. This is a development stand-in, not authentication.
- Errors: `AuthorizationError` → 403, `ValueError` → 400, unknown path → 404.

## Known limitations

- The handler creates its `FinSyncService` and a `finsync.db` file in the working directory at import time.
- No request size limit and no authentication yet; both are on the [roadmap](../../docs/planning/roadmap.md).

## Rules for this folder

- No business logic here: validation of transaction content belongs in `core`, parsing in `ingestion`.
