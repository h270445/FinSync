# 0008. Notification time and the calendar day

- Status: Proposed
- Date: 2026-10-29

## Context

Matching compares two kinds of time. A minute-precision record (a bank notification, or a manual entry with a time) is an instant; a day-precision record (a manual or sheet entry with only a date) is a calendar day. The scorer compares instants by minutes and, when either side is day-precision, compares calendar days ([matching design](../../design/transaction-matching.md)).

What the Android spike showed ([findings](../../design/android-notification-spike.md)):

- The OTP Bank notification text carries no time at all, for transfers and card purchases alike. The only time is the notification's `post_time_ms`, an epoch-millisecond instant set by the phone when the bank app posts it.
- The spike also records `device_time_ms` and `device_zone` when it stores a notification; on the test phone the zone was `Europe/Budapest`.
- A notification can be shown late: the listener reads still-visible notifications when it reconnects, so the time it is read can be minutes or hours after `post_time_ms`.

Today the code stores every instant in UTC and projects minute-precision records to the `Europe/Budapest` calendar day before a day comparison (`finsync/matching/normalize.py`). Two inputs still treat a time without an offset as UTC: the synthetic notification text (`... on 2026-09-05 16:42`) and a manual `happened_at` without an offset. For a person in Hungary, both are local wall-clock times.

The supervisor approved the approach on 2026-10-29 ([feedback](../../planning/supervisor-feedback.md#2026-10-29--reply-to-the-oct-28-interim-note)).

## Decision

1. **The time of a notification is `post_time_ms`.** The Android app sends it as `posted_at`, an ISO 8601 instant with offset; the server stores it in UTC as `happened_at` with minute precision. A time printed in the text is not used, because the supported formats have none. The time the listener read it, or the server received it, is kept only as arrival time, never as `happened_at`.
2. **Instants are stored in UTC.** Every stored `happened_at` of minute precision is a UTC instant.
3. **A time without an offset is `Europe/Budapest` wall-clock time.** This applies to manual and sheet entries and to any notification text that prints a time. It is converted to UTC on input. In the repeated hour at the end of summer time, the first occurrence is taken (`fold=0`); a time in the skipped spring hour is moved forward by the zone rules.
4. **A day-precision record stays a calendar date.** It is stored as the date the person typed, with no time-zone conversion.
5. **Calendar days are compared in `Europe/Budapest`.** A minute-precision instant is projected to its local day before it is compared with a day-precision record, so a purchase at 23:30 local time is on the same day as a manual entry for that date. The zone is one constant for the prototype; a per-group zone setting is left for Szakdolgozat II.
6. **The device zone is recorded, not used for matching.** `device_zone` stays with the raw record for diagnosis (travel abroad, a wrong phone clock), but the group's zone decides the calendar day.

## Consequences

- No time is guessed from text, and the instant is independent of the phone's zone, so a notification captured while travelling still matches its manual entry by instant.
- A notification read late keeps its true time, so a delayed read does not push it outside the matching window.
- A purchase near midnight abroad may fall on a different local day in Budapest than the one the person remembers; this is accepted for the prototype and visible through the recorded `device_zone`.
- Follow-up work:
  - The Android ingest (M2, Nov 9–15) sends `posted_at`; `/v1/notifications/ingest` accepts it, and `happened_at` comes from it.
  - Manual and notification-text times without an offset are read as `Europe/Budapest` instead of UTC, with tests for a late-evening purchase and for both summer-time changes. The synthetic dataset's notification text then prints local time, so the evaluation data and its results are regenerated and re-checked in the same change.
