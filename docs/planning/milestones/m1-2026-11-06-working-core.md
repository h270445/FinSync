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

- [ ] Ingest → normalize → match → store runs in one database transaction for notification, manual and bulk input.
- [ ] Every stored record has an `event_id`; every matching outcome has a `match_decisions` row with score, features and `matcher_version`.
- [ ] Service tests cover the scenarios in the [matching design](../../design/transaction-matching.md#testing-and-evaluation) that do not need the review endpoints.
- [ ] `python -m finsync.evaluation` runs on dataset v1 and prints precision, recall, false-merge rate, missed-duplicate rate and review rate.
- [ ] First results are saved in `docs/evaluation/results/` with the commit id.

## Checklist

- [ ] PR #2 and #3 merged.
- [ ] Schema versioning and migration (`events`, `match_decisions`, new columns).
- [ ] Notification time-zone decision recorded (ADR).
- [ ] `finsync/matching/` with unit tests.
- [ ] Matching wired into all ingest paths; `event_id`, `match_outcome` in responses.
- [ ] `GET /v1/events`.
- [ ] Synthetic dataset v1 (~100 labelled records) and its description.
- [ ] Evaluation runner and first results.
- [ ] Side tracks: Android notification-listener spike on a real device; ADR for how the Sheets script reaches the API.
- [ ] Docs updated (API reference, storage README, design status → Accepted).
- [ ] Release notes, tag `v0.2.0`, e-mail.
