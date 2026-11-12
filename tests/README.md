# `tests/` — automated tests

All tests use the standard-library `unittest` and need no extra packages.

## Running

From the repository root:

```bash
python -m unittest discover -s tests
```

## Contents

| File | Covers |
| --- | --- |
| `test_finsync_service.py` | Notification parsing, notification ingest, manual and bulk creation (including atomic rollback and invalid rows), group authorization |
| `test_categorization.py` | Whole-word keyword matching of the rule-based categorizer |
| `test_matching.py` | Matching rules: merchant tokens, local day, fingerprint, each blocking gate, score values, thresholds and runner-up margin |
| `test_review.py` | Review list, confirm, reject (not proposed again), split, identical-row confirm, other-group access (404) and the HTTP flow |
| `test_storage_schema.py` | Alembic creates the same schema as the old SQLite migrations; a pre-Alembic file is handed over to Alembic once |
| `test_concurrency.py` | Eight threads sending the same notification at once store one original and one event (the write lock), on SQLite and PostgreSQL |
| `test_local_time.py` | Times without an offset are Budapest time, including both summer-time changes; dates stay calendar days |
| `test_evaluation_dataset.py` | The committed matching datasets (v1, v2 and v3) equal the generator output, v2 keeps v1 record for record, v3 is v2 with local notification times, generation is reproducible, every scenario is covered, purchases stay in one split, and every row can be ingested |
| `test_categorization_dataset.py` | The committed categorization dataset equals the generator output, generation is reproducible, the scenario mix and every category appear, both splits hold clear and ambiguous items |
| `test_reverse_order_options.py` | The two `rules-3` fixes for the reverse-order case: the strict gate for information-poor pairs, and reopening a contested automatic link (the 2026-10-18 IKEA case replayed), including that a person's links are never reopened |
| `test_evaluation_runner.py` | Evaluation metrics on hand-made events (false merges, review-flagged pairs, baseline), threshold choice, the late Decathlon entry on dataset v1, a deterministic report |
| `test_matching_service.py` | Matching end to end: the four hand-decided examples (repeated notification, reversed arrival order, date-only manual entry, two same-amount purchases), further design scenarios (including an invalid bulk row leaving records, events and decisions unchanged), the schema migration |

## Conventions

- One file per package or behaviour: `test_<area>.py`.
- Each test uses its own temporary SQLite file; tests never touch `finsync.db`.
- **On PostgreSQL:** `python tests/run_on_postgres.py postgresql+psycopg://user:password@localhost/finsync_test` runs the same suite with one PostgreSQL schema per test database (about a minute) and drops the schemas at the end. Tests that open the SQLite file directly (the pre-Alembic migrations, the raw-file checks for hashes) are skipped there with `FINSYNC_TEST_DATABASE_URL` set.
- Only synthetic data. No real bank notifications or personal data.
- `tests/data/` holds the labelled evaluation datasets, described in [docs/evaluation/datasets.md](../docs/evaluation/datasets.md).
