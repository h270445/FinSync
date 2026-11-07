# Getting started

## Requirements

- Python 3.10 or newer (the code uses `str | None` type syntax).
- No third-party code: the prototype uses only the standard library. On Windows, `zoneinfo` needs the IANA time-zone data, which the operating system does not provide; install it once with `python -m pip install -r requirements.txt` (the `tzdata` data package; nothing is installed on Linux or macOS). Without it, the matching code fails with `No time zone found with key Europe/Budapest`.

## Run the API

From the repository root:

```bash
python -m finsync.api
```

The server listens on `http://127.0.0.1:8080` and creates `finsync.db` (SQLite) in the current directory. Options: `--host`, `--port`, `--db <file>`.

## Create an API token

Every request needs a token. In a second terminal, from the repository root:

```bash
python -m finsync.api.tokens create --user demo-user --group demo-group --name "curl"
```

This adds `demo-user` to `demo-group` if needed and prints a token (`fs_...`) once; only its hash is stored. `python -m finsync.api.tokens list` shows the tokens without the secret, and `python -m finsync.api.tokens revoke <id>` revokes one. Use `--db <file>` before the command if the server runs with another database.

## Send a first request

```bash
TOKEN=fs_...   # the printed token
curl -X POST http://127.0.0.1:8080/v1/notifications/ingest \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "CARD PURCHASE -1234.56 HUF at Tesco on 2026-09-01 13:45"}'

curl http://127.0.0.1:8080/v1/transactions -H "Authorization: Bearer $TOKEN"
```

All endpoints: [api.md](api.md).

## Run the tests

```bash
python -m unittest discover -s tests
```

## Reset local data

Stop the server and delete `finsync.db`.

## Security note

Requests are authenticated with per-member API tokens; keep a token like a password and revoke it if it leaks. There is no request size limit yet, so do not expose the API to the internet (for example through a tunnel) before that is in place. Use synthetic data only.
