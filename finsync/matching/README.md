# `finsync/matching/` — transaction matching and duplicate detection

**Status: planned, not implemented.** This folder holds only a package marker so the target layout is visible.

This is the main thesis contribution: deciding whether a new record describes a financial event that is already stored (from another source or another member) or a new one, without merging separate purchases.

## Planned contents

| Module | Contents |
| --- | --- |
| `normalize.py` | Sign/direction, UTC time with precision, merchant key |
| `fingerprint.py` | SHA-256 fingerprint for exact re-delivery |
| `scoring.py` | Candidate gates (blocking), feature scores, weighted score |
| `decision.py` | Thresholds → `auto_linked`, `needs_review`, `separate` |

## Rules for this folder

- Pure functions on plain values: no database, network or clock access, so every rule is unit-testable and results are reproducible.
- Every decision carries a `matcher_version`.

Design: [docs/design/transaction-matching.md](../../docs/design/transaction-matching.md).
