# `finsync/api/` — HTTP API layer

Translates HTTP requests into calls on `FinSyncService` and maps results and errors to JSON responses. Built on FastAPI and served by Uvicorn ([ADR 0006](../../docs/architecture/decisions/0006-framework-based-stack.md)); the storage below it is still SQLite.

| File | Contents |
| --- | --- |
| `server.py` | `create_app(storage)`: routes, request and response models (they make the OpenAPI schema), the token dependency, the body size middleware and error mapping; `run_server()` |
| `__main__.py` | Entry point for `python -m finsync.api` (`--host`, `--port`, `--db`; `--openapi` prints the schema) |
| `tokens.py` | Command line for API tokens: `python -m finsync.api.tokens create|list|revoke` |
| `__init__.py` | Public names: `create_app`, `run_server` |

## Behaviour

- Endpoints: full reference in [docs/guides/api.md](../../docs/guides/api.md).
- Identity comes from the `Authorization: Bearer` API token only; the token decides member and group, and `X-User-Id`/`X-Group-Id` are ignored ([ADR 0009](../../docs/architecture/decisions/0009-api-tokens.md)). Request bodies are limited before the app parses them: 64 KiB, and 1 MiB for `/v1/transactions/bulk`; a larger body gets 413. The middleware counts the bytes that arrive, not only the declared `Content-Length`, so chunked bodies are limited too.
- Errors: `AuthenticationError` → 401 with `WWW-Authenticate: Bearer`, `AuthorizationError` → 403, `NotFoundError` → 404, `ConflictError` → 409, `ValueError` and request-model validation errors → 400, unknown path → 404. Every error body is `{"error": "..."}`.
- The request models describe the shapes; the service validates the values again, so its rules stay in one place and its tests cover them.

## Known limitations

- Matching cost grows with the number of rows in one bulk request (1 000 similar rows took about 100 s on a laptop); a row-count limit is open.
- Password login for the web app is not implemented yet.

## Rules for this folder

- No business logic here: validation of transaction content belongs in `core`, parsing in `ingestion`.
