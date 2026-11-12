# Getting started

## Requirements

- Python 3.10 or newer (the code uses `str | None` type syntax).
- The packages in `requirements.txt`: FastAPI and Uvicorn for the API, SQLAlchemy, Alembic and psycopg for storage, openpyxl for XLSX file import, httpx for the tests, and on Windows the `tzdata` time-zone data (Windows does not ship it; without it the matching code fails with `No time zone found with key Europe/Budapest`). Install them once, preferably in a virtual environment:

  ```bash
  python -m venv .venv
  source .venv/bin/activate     # Windows PowerShell: .venv\Scripts\Activate.ps1
  python -m pip install -r requirements.txt
  ```

## Run the API

From the repository root:

```bash
python -m finsync.api
```

The server listens on `http://127.0.0.1:8080` and creates `finsync.db` (SQLite) in the current directory. The interactive API description is at `http://127.0.0.1:8080/docs`. Options: `--host`, `--port`, `--db <file or URL>`.

### With PostgreSQL (Docker Compose)

With Docker installed, from the repository root:

```bash
docker compose up --build
```

This starts PostgreSQL 16 and the API on `http://127.0.0.1:8080`; the schema is created on the first start and kept in a Docker volume (`docker compose down -v` deletes it). The commands below then run inside the API container, for example `docker compose exec api sh -c 'python -m finsync.api.tokens --db "$FINSYNC_DATABASE_URL" create --user demo-user --group demo-group --name curl'`. The database password in `compose.yaml` is a development placeholder; set `FINSYNC_DB_PASSWORD` to change it.

Without Docker, any PostgreSQL works: `python -m finsync.api --db postgresql+psycopg://user:password@localhost/finsync`. The startup line prints the URL with the password masked.

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

## Run the web app

Give the member a password (the member must already be in a group, for example through the token command above):

```bash
python -m finsync.api.passwords set --user demo-user --email demo@example.com
```

With the API running, see [web/README.md](../../web/README.md): `npm install` and `npm run dev` in `web/`, then sign in with `demo@example.com` or `demo-user` and the password.

## Run the tests

```bash
python -m unittest discover -s tests
```

Web app: `npm test` in `web/`.

## Reset local data

Stop the server and delete `finsync.db`.

## Security note

Requests are authenticated with per-member API tokens or, in the web app, a password and a session cookie ([ADR 0010](../architecture/decisions/0010-web-sign-in.md)); keep a token like a password and revoke it if it leaks. Request bodies are size-limited (64 KiB, 1 MiB for bulk and file import). Expose the API through a tunnel only temporarily, for tests and the demo ([ADR 0007](../architecture/decisions/0007-how-external-clients-reach-the-api.md)). Use synthetic data only.
