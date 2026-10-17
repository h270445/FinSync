# `finsync/matching/` — transaction matching and duplicate detection

The main thesis contribution: deciding whether a new record describes a financial event that is already stored (from another source or another member) or a new one, without merging separate purchases.

## Contents

| Module | Contents |
| --- | --- |
| `normalize.py` | Direction from the sign, whole-unit rounding, calendar day (Europe/Budapest), merchant tokens |
| `fingerprint.py` | Canonical JSON of a manual row; SHA-256 fingerprint of group, channel and payload |
| `scoring.py` | `MatchRecord`; blocking gates (group, currency, direction, amount, time window) and the weighted score |
| `decision.py` | Thresholds and runner-up margin: `auto_linked`, `needs_review` or `separate`; `MATCHER_VERSION` |

The database side (candidate query, events, decision log) is in `finsync/storage/`, and the flow that ties them together is `FinSyncService._store_and_match` in `finsync/core/`.

## Rules for this folder

- Pure functions on plain values: no database, network or clock access, so every rule is unit-testable and results are reproducible.
- Every decision carries a `matcher_version`; change it whenever a rule, weight or threshold changes.

Design: [docs/design/transaction-matching.md](../../docs/design/transaction-matching.md). Tests: `tests/test_matching.py` (rules) and `tests/test_matching_service.py` (end to end).
