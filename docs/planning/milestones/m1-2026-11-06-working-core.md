# M1 — Working core

- Deadline: 2026-11-06 23:59
- Tag: `v0.2.0`
- Status: planned
- Internal target: 2026-10-30

## Expected result (course)

A working professional core: one complete, meaningful user or processing flow works end to end. The main technical risk has a working experimental solution, test or measurement.

## The flow demonstrated

A banking notification and a manual entry for the same purchase arrive through the API; FinSync stores both records, links them to one event, and `GET /v1/events` shows one purchase. Two look-alike purchases from the same phone stay separate.

## Acceptance criteria

- [x] Ingest → normalize → match → store runs in one database transaction for notification, manual and bulk input.
- [x] Every stored record has an `event_id`; every matching outcome has a `match_decisions` row with score, features and `matcher_version`.
- [x] Service tests cover the scenarios in the [matching design](../../design/transaction-matching.md#testing-and-evaluation) that do not need the review endpoints.
- [x] `python -m finsync.evaluation` runs on dataset v1 and prints precision, recall, false-merge rate, missed-duplicate rate and review rate.
- [x] The same run reports the naive store-every-row baseline, and wrongly merged separate purchases are reported separately from missed duplicates.
- [x] Hand-decided examples pass: repeated submission, reverse arrival order, date-only manual entry, two separate purchases with the same amount.
- [x] First results are saved in `docs/evaluation/results/` with the commit id.

## Checklist

- [x] Fixes from PR #2 (whole-word categorization) and PR #3 (atomic bulk import, amount validation) carried over to the current layout.
- [x] Schema versioning and migration (`events`, `match_decisions`, new columns).
- [ ] Notification time-zone decision recorded ([ADR 0008](../../architecture/decisions/0008-notification-time-and-calendar-day.md), proposed 2026-10-29).
- [x] `finsync/matching/` with unit tests.
- [x] Matching wired into all ingest paths; `event_id`, `match_outcome` in responses.
- [x] `GET /v1/events`.
- [x] Review and correction endpoints (planned for Nov 2–8, done early on Oct 17).
- [x] Synthetic dataset v1 (~100 labelled records) and its description.
- [x] Evaluation runner and first results (Oct 18).
- [ ] Side tracks: Android notification-listener spike on a real device (spike app and emulator rounds done 2026-10-26, [findings](../../design/android-notification-spike.md); phone test 2026-10-27); ADR for how the Sheets script reaches the API (done 2026-10-24, [ADR 0007](../../architecture/decisions/0007-how-external-clients-reach-the-api.md)).
- [x] Docs updated (API reference, storage README, design status → Accepted on 2026-10-26).
- [x] Reverse-order case investigated as the supervisor asked: two fixes compared on the development split of dataset v2, `rules-3` with both on and threshold 0.95 (2026-10-29, [results](../../evaluation/results/2026-10-29-matching-rules-3.md)).
- [ ] Release notes, tag `v0.2.0`, e-mail.
