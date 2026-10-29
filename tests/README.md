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
| `test_evaluation_dataset.py` | The committed matching datasets (v1 and v2) equal the generator output, v2 keeps v1 record for record, generation is reproducible, every scenario is covered, purchases stay in one split, and every row can be ingested |
| `test_reverse_order_options.py` | The two `rules-3` fixes for the reverse-order case: the strict gate for information-poor pairs, and reopening a contested automatic link (the 2026-10-18 IKEA case replayed), including that a person's links are never reopened |
| `test_evaluation_runner.py` | Evaluation metrics on hand-made events (false merges, review-flagged pairs, baseline), threshold choice, the late Decathlon entry on dataset v1, a deterministic report |
| `test_matching_service.py` | Matching end to end: the four hand-decided examples (repeated notification, reversed arrival order, date-only manual entry, two same-amount purchases), further design scenarios (including an invalid bulk row leaving records, events and decisions unchanged), the schema migration |

## Conventions

- One file per package or behaviour: `test_<area>.py`.
- Each test uses its own temporary SQLite file; tests never touch `finsync.db`.
- Only synthetic data. No real bank notifications or personal data.
- `tests/data/` holds the labelled evaluation datasets, described in [docs/evaluation/datasets.md](../docs/evaluation/datasets.md).
