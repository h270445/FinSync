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

OTP Bank (from the Android app; shapes from the [spike findings](../../docs/design/android-notification-spike.md), examples made up):

```text
-4 990 Ft értékben vásárolt a PELDABOLT KFT 12. üzletében.    card purchase: merchant = the words in capitals
-12 000 Ft, Minta Anna                                        transfer: counterparty after the comma
```

The amount comes first, signed, with a space as thousands separator and `Ft` (HUF) or a three-letter currency. These texts print no time, so the time is the phone's `posted_at`. The Android app applies the same rule before sending (`OtpFormat.kt`); the server stays the authority.

Any other text raises `ValueError("Unsupported notification format")`. A time printed in a synthetic text has no offset and is read as Europe/Budapest wall-clock time, then converted to UTC (`local_time.py`, [ADR 0008](../../docs/architecture/decisions/0008-notification-time-and-calendar-day.md)).

## Rules for this folder

- Pure functions only: no database or network access.
- A new source (for example a spreadsheet CSV export) gets its own module and its own tests.
