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
| `test_evaluation_dataset.py` | The committed matching dataset equals the generator output, is reproducible, covers every scenario, keeps purchases in one split, and every row can be ingested |
| `test_evaluation_runner.py` | Evaluation metrics on hand-made events (false merges, review-flagged pairs, baseline), threshold choice, the late Decathlon entry on dataset v1, a deterministic report |
| `test_matching_service.py` | Matching end to end: the four hand-decided examples (repeated notification, reversed arrival order, date-only manual entry, two same-amount purchases), further design scenarios, the schema migration |

## Conventions

- One file per package or behaviour: `test_<area>.py`.
- Each test uses its own temporary SQLite file; tests never touch `finsync.db`.
- Only synthetic data. No real bank notifications or personal data.
- `tests/data/` holds the labelled evaluation datasets, described in [docs/evaluation/datasets.md](../docs/evaluation/datasets.md).
