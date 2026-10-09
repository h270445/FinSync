# `finsync/` — backend package

The FinSync backend: a Python standard-library HTTP API that ingests transactions, categorizes them and stores them per group in SQLite.

## Layout

| Folder | Layer | Contents |
| --- | --- | --- |
| [`api/`](api/README.md) | HTTP | Request handler, identity headers, JSON (de)serialization, server entry point |
| [`core/`](core/README.md) | Application | `FinSyncService`: the use cases (ingest, create, bulk create, list) and authorization checks |
| [`ingestion/`](ingestion/README.md) | Domain | Source-specific parsers, currently the notification text parser |
| [`categorization/`](categorization/README.md) | Domain | Rule-based categorizer (baseline for the planned LLM comparison) |
| [`matching/`](matching/README.md) | Domain | Transaction matching and duplicate detection (planned, empty) |
| [`storage/`](storage/README.md) | Persistence | SQLite schema, transaction and membership queries |

## Dependency rule

Imports only point downwards:

```text
api  →  core  →  ingestion, categorization, matching, storage
```

- `ingestion`, `categorization` and `matching` do not import `api`, `core` or `storage`; they work on plain values so they can be unit-tested without a database.
- `storage` holds no business rules.
- Each subpackage re-exports its public names in `__init__.py`; other packages import from there (`from finsync.storage import FinSyncStorage`), not from the module inside.

The full target architecture is in [docs/architecture/overview.md](../docs/architecture/overview.md).

## Running

```bash
python -m finsync.api        # starts the API on http://127.0.0.1:8080
```

See [docs/guides/getting-started.md](../docs/guides/getting-started.md).
