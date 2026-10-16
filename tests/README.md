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
| `test_finsync_service.py` | Notification parsing, notification ingest, manual and bulk creation, group authorization |

## Conventions

- One file per package or behaviour: `test_<area>.py` (for example `test_matching.py`, `test_matching_service.py`).
- Each test uses its own temporary SQLite file; tests never touch `finsync.db`.
- Only synthetic data. No real bank notifications or personal data.
- Planned: `tests/data/` for labelled evaluation datasets (for example `matching_eval.csv`), described in [docs/evaluation/](../docs/evaluation/README.md).
