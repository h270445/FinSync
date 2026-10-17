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
| `test_matching_service.py` | Matching end to end: the four hand-decided examples (repeated notification, reversed arrival order, date-only manual entry, two same-amount purchases), further design scenarios, the schema migration |

## Conventions

- One file per package or behaviour: `test_<area>.py`.
- Each test uses its own temporary SQLite file; tests never touch `finsync.db`.
- Only synthetic data. No real bank notifications or personal data.
- Planned: `tests/data/` for labelled evaluation datasets (for example `matching_eval.csv`), described in [docs/evaluation/](../docs/evaluation/README.md).
