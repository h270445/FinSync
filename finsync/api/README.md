# `finsync/api/` — HTTP API layer

Translates HTTP requests into calls on `FinSyncService` and maps results and errors to JSON responses.

| File | Contents |
| --- | --- |
| `server.py` | `FinSyncRequestHandler` (routes, token identity, JSON parsing, error mapping), `create_handler(storage)` and `run_server()` |
| `__main__.py` | Entry point for `python -m finsync.api` (`--host`, `--port`, `--db`) |
| `tokens.py` | Command line for API tokens: `python -m finsync.api.tokens create|list|revoke` |
| `__init__.py` | Public names: `FinSyncRequestHandler`, `create_handler`, `run_server` |

## Behaviour

- Endpoints: full reference in [docs/guides/api.md](../../docs/guides/api.md).
- Identity comes from the `Authorization: Bearer` API token only; the token decides member and group, and `X-User-Id`/`X-Group-Id` are ignored ([ADR 0009](../../docs/architecture/decisions/0009-api-tokens.md)). The token is checked before the body is read.
- Errors: `AuthenticationError` → 401 with `WWW-Authenticate: Bearer`, `AuthorizationError` → 403, `NotFoundError` → 404, `ConflictError` → 409, `ValueError` → 400, unknown path → 404.

## Known limitations

- No request size limit yet; it is on the [roadmap](../../docs/planning/roadmap.md). Until then the API must not be exposed through a tunnel.

## Rules for this folder

- No business logic here: validation of transaction content belongs in `core`, parsing in `ingestion`.
