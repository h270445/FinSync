# `finsync/ingestion/` — input parsing

Turns source-specific input into structured transaction data. One module per source format.

| File | Contents |
| --- | --- |
| `notifications.py` | `parse_notification()` and `ParsedNotification` for banking notification text |
| `__init__.py` | Public names: `ParsedNotification`, `parse_notification` |

## Supported notification formats

```text
CARD PURCHASE -1234.56 HUF at Tesco on 2026-09-01 13:45
Incoming transfer 50000 HUF from Jane Doe 2026-09-01 13:45
```

Any other text raises `ValueError("Unsupported notification format")`. Timestamps are currently tagged as UTC; whether banks print local time is an open question in the [matching design](../../docs/design/transaction-matching.md).

## Rules for this folder

- Pure functions only: no database or network access.
- A new source (for example a spreadsheet CSV export) gets its own module and its own tests.
