# Getting started

## Requirements

- Python 3.10 or newer (the code uses `str | None` type syntax).
- No third-party packages: the prototype uses only the standard library.

## Run the API

From the repository root:

```bash
python -m finsync.api
```

The server listens on `http://127.0.0.1:8080` and creates `finsync.db` (SQLite) in the current directory. A demo membership, `demo-user` in `demo-group`, is created at start-up.

## Send a first request

```bash
curl -X POST http://127.0.0.1:8080/v1/notifications/ingest \
  -H "X-User-Id: demo-user" -H "X-Group-Id: demo-group" \
  -H "Content-Type: application/json" \
  -d '{"message": "CARD PURCHASE -1234.56 HUF at Tesco on 2026-09-01 13:45"}'

curl http://127.0.0.1:8080/v1/transactions \
  -H "X-User-Id: demo-user" -H "X-Group-Id: demo-group"
```

All endpoints: [api.md](api.md).

## Run the tests

```bash
python -m unittest discover -s tests
```

## Reset local data

Stop the server and delete `finsync.db`.

## Security note

The demo membership and client-supplied identity headers are intended for local development only. They must not be treated as production authentication. Use synthetic data only.
