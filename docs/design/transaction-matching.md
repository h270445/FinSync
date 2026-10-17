# Transaction matching and duplicate detection

- Status: **Partially implemented** (matching steps 1–5 and the review endpoints on SQLite since 2026-10-17; evaluation pending)
- Date: 2026-10-09
- Decision record: [ADR 0004](../architecture/decisions/0004-event-based-transaction-matching.md)

## Summary

FinSync keeps every incoming record untouched and links records that describe the same purchase to one shared **event**, using a transparent rule-based score with two thresholds: link automatically, send to review, or keep separate.

The core rule that stops false merges: an event may hold at most one original record per **channel**, meaning a source type plus the member who submitted it. Exact re-deliveries of a record are kept for traceability but attached to the record they repeat, so they never count as a second record (step 2). Two notifications on the same phone with the same amount five minutes apart are always two purchases; a notification and a manual entry, or two members' manual entries, can be linked. Every decision is written to an append-only log, so it can be explained, confirmed or undone.

- **In scope:** exact re-import detection, cross-source matching, the review queue, undo, the data model, tests and the evaluation dataset.
- **Out of scope:** foreign-currency matching, split payments, LLM-assisted matching, authentication (see [Open questions](#open-questions)).

## Where duplicates come from

Three different things look like duplicates. They need different handling, and mixing them up is the main source of wrong merges.

| Kind | What it is | Typical source | Handling |
| --- | --- | --- | --- |
| **A. Re-delivery** | The same record from the same source arrives again | Android retry after a network error or restart, a notification posted twice; the same export file uploaded twice or two exports with overlapping date ranges; a Sheets row sent again; a double-clicked web form | Automatic, no question to the member: recognised by an identity key, stored as `exact_duplicate`, never counted twice |
| **B. Cross-source duplicate** | The same purchase reported by different channels | Notification and a manual, sheet or file entry; two members both logging a shared dinner | Candidate matching with a score: auto-link only when confident and unique, otherwise review; always reversible with split |
| **C. Look-alike, not a duplicate** | Separate purchases that share amount and time | Two bus tickets or coffees on the same day; monthly subscriptions; a refund of the same amount | Must stay separate: the one-original-per-channel rule, the time window, the direction gate; ambiguous cases go to review, never to an automatic merge |

### Per source

| Source | Re-delivery risk (A) | Identity key, strongest first | Notes |
| --- | --- | --- | --- |
| **Android notifications** | High: retries, restarts, re-posted notifications | Client idempotency key per notification (generated once on the phone and resent on every retry); then the fingerprint of the notification text | Some banks send an authorization and a later booking notification for one purchase; that is the same channel, so the parser must tell the two types apart (check during the Android spike). Notification time is minute-precise. |
| **File import (CSV/XLSX export)** | High: the same file twice, overlapping date ranges | Bank transaction reference column if the export has one; else `source_ref` built from the row; whole-file hash per `import_batch_id` | Re-importing a known file is reported before anything is stored. Two identical rows inside one file are not merged automatically (two equal tickets are possible); they go to review. Exports often carry the booking date, 1–3 days after the purchase, so rows are day-precision. |
| **Google Sheets script** | Medium: resending rows after an edit or a failed run | A stable row id column written by the script, used as `source_ref` | An edited row is a new version of the same record, not a new purchase (open question 7). |
| **Manual entry (web app)** | Low: double submit | Idempotency key per form submission | Manual entries are the main cause of kind B; typed amounts may be rounded and the time is often day-precision. |

### Practices this design follows

1. **Idempotency first.** Clients send a key that stays the same across retries; the server stores it and answers a repeated request with the original result instead of creating a record. This removes most of kind A before any matching runs.
2. **Source identity before content.** A reference the source itself provides (bank transaction id, sheet row id) beats a content hash; the content fingerprint is the fallback.
3. **Fuzzy matching only across channels.** Kind B is scored; within one channel only kind A is possible, so look-alikes (kind C) from the same phone are never merged.
4. **Keep everything, link instead of delete.** Every record stays stored with its raw payload; duplicates are linked to an event, so totals count the event once and nothing is lost.
5. **Human decision when uncertain, and undo.** Review for the middle band and split for wrong links; every decision is logged.
6. **Measure both error types.** Missed duplicates (double-counted expenses) and false merges (a real purchase disappears) are reported separately, because the second is worse for the user.

### Hand-decided examples (first tests)

Requested by the supervisor (2026-10-16) before the full dataset:

| Example | Expected |
| --- | --- |
| Same notification sent twice (retry) | Kind A: `exact_duplicate`, one event |
| Manual entry first, notification for the same purchase later | Kind B: linked, same result as the other order |
| Date-only manual entry vs. a notification at 18:42 the same day | Kind B: candidate with day-precision time score; linked or review by merchant |
| Two notifications of 4 500 Ft at the same shop, 10 minutes apart | Kind C: two events |

## Current state

Steps 1 to 5 below run on every ingest path since 2026-10-17, on the existing SQLite backend (`finsync/matching/`, `FinSyncService._store_and_match`, schema version 2). The review endpoints (list, confirm, reject, split) work as described in [User flow and API](#user-flow-and-api). Client idempotency keys and the evaluation runner are not built yet.

| Entry point | Channel | Exact re-delivery key | `match_outcome` in the response |
| --- | --- | --- | --- |
| `POST /v1/notifications/ingest` | `android_notification` + member | Fingerprint of the notification text | Yes |
| `POST /v1/transactions` | `manual` + member | Fingerprint of the row; only with a `source_ref`, else an identical row goes to review | Yes |
| `POST /v1/transactions/bulk` | `manual` + member | Same as manual; all rows in one transaction with one `import_batch_id` | Yes, per row |

Choices made while implementing, open to change:

- **Time:** everything is stored in UTC. A date-only manual value is kept as that date at 00:00 UTC with `happened_at_precision = day`; calendar days of minute-precision records are taken in Europe/Budapest. Notification times are still read as UTC (open question 1).
- **Direction:** a manual row may send `direction` (`expense` or `income`), which sets the sign; without it the typed sign decides, as before.
- **Below 0.60:** the decision row still names the best candidate event, so a near miss can be inspected later.
- **Concurrency:** each ingest call runs inside `BEGIN IMMEDIATE`, so two calls cannot both read the same candidates.
- **Review state:** an event is `needs_review` while one of its records has an unanswered `needs_review` decision. An event left without records (after a confirm moved its only record away) is kept for the log but hidden from `GET /v1/events`.
- **Confirming an identical manual row** (the two-bus-tickets case) turns it into a re-delivery of the original; confirming any other record into an event that already holds that channel returns 409 ("split it first").
- **Rejected pairs:** a record whose fingerprint was already rejected for an event is never proposed for that event again.
- **Errors:** an id from another group returns 404, an action on a decision that is no longer open returns 409.

## Matching approach

Each new record goes through five steps inside one database transaction. Matching is deterministic and versioned (`matcher_version` on every decision), so a result can be reproduced from the same data. Every path writes a `match_decisions` row; only a confident, unique match is linked without a person.

### 1. Normalise

- **Amount and sign:** `Decimal`; money leaving the group is negative. Manual input gets an explicit `direction` (expense or income) instead of trusting the typed sign.
- **Time:** convert to UTC and keep `happened_at_precision` (`minute` or `day`). A date-only manual entry is a day, not midnight.
- **Merchant key:** lowercase, strip accents, drop punctuation, store numbers and legal suffixes (kft, zrt, bt), then keep the token set. "TESCO Áruház 41021" and "Tesco weekly shop" both yield `tesco` plus extra tokens. Without a merchant, the description tokens are used.

### 2. Exact re-delivery

A fingerprint is the SHA-256 of group, channel and the raw payload (notification text, or the canonical JSON of a manual row plus an optional client `row_ref`). The same notification text from the same phone is a re-delivery: the new record is stored with `duplicate_of_id` set to the original record, joins the original's event, and gets outcome `exact_duplicate`. A re-delivery is not an original record: it is ignored by the one-record-per-channel rule, by scoring and by the event's display values, and it always moves together with its original. An identical manual row goes to review instead, because a person may buy two identical bus tickets.

### 3. Candidates (blocking)

Only events that pass every gate are scored:

- same `group_id` (matching never crosses groups);
- same currency and same direction;
- equal amount, or equal after rounding to a whole currency unit (HUF entries are often typed as 1235 for 1234.56);
- time difference within the window: 48 hours, or 3 calendar days when either side is day-precision;
- the event does not already hold an original record (`duplicate_of_id` is null) from the new record's channel.

### 4. Score

The new record is scored against each record in a candidate event; the best pair counts.

| Feature | Value |
| --- | --- |
| Amount `a` | 1.0 exact; 0.7 equal only after rounding |
| Time `t` | 1 − Δt / window; 1.0 on the same local day when either side is day-precision |
| Merchant `m` | Jaccard overlap of merchant token sets; 0.5 when one side has no merchant text |

`S = 0.4·a + 0.3·t + 0.3·m` (starting weights).

### 5. Decide

| Condition | Outcome |
| --- | --- |
| Best S ≥ 0.85 and no runner-up within 0.10 | `auto_linked` to that event |
| Best S in [0.60, 0.85), or two candidates within 0.10 | `needs_review`; the record gets its own event until a member decides |
| Best S < 0.60, or no candidate | `separate`, new event |

Weights, window and thresholds are starting values, tuned on a development split of the evaluation dataset and reported on a held-out split.

## Data model changes

`transactions` becomes the immutable record of what each source said; a new `events` table holds the events people see; `match_decisions` explains every link. No source row is updated or deleted by matching.

**`transactions`** (existing columns kept) — new columns:

| Column | Type | Purpose |
| --- | --- | --- |
| `event_id` | INTEGER FK `events.id` | The event this record belongs to |
| `direction` | TEXT `expense`/`income` | Normalised sign |
| `happened_at_precision` | TEXT `minute`/`day` | Stops a date-only entry reading as midnight |
| `merchant_key` | TEXT | Normalised merchant tokens |
| `fingerprint` | TEXT, indexed | SHA-256 for exact re-delivery |
| `duplicate_of_id` | INTEGER FK `transactions.id`, nullable | Set on an exact re-delivery; points to the original record |
| `raw_payload` | TEXT | Original notification text or row JSON |
| `source_ref` | TEXT, nullable | Client reference such as a spreadsheet row id |
| `import_batch_id` | TEXT, nullable | Groups the rows of one bulk import |

**`events`** (new): `id`, `group_id`, display values (`amount`, `currency`, `direction`, `happened_at`, `merchant`, `category`), `primary_transaction_id` (notification over manual, then earliest), `review_state` (`clear`/`needs_review`), `created_at`, `updated_at`.

**`match_decisions`** (new, append-only): `id`, `group_id`, `transaction_id`, `candidate_event_id`, `outcome` (`exact_duplicate`, `auto_linked`, `needs_review`, `separate`, `confirmed`, `rejected`, `split`), `score`, `features` (JSON: a, t, m, Δt, runner-up), `matcher_version`, `decided_by` (`system` or user id), `supersedes_id`, `created_at`.

Indexes: `transactions(group_id, currency, amount, happened_at)`, `transactions(fingerprint)`, `match_decisions(group_id, outcome)`.

Migration: a `schema_version` table; one step adds the columns, creates one event per existing transaction and writes a `separate` decision with `decided_by = migration`. Existing data is never auto-merged.

## User flow and API

Matching runs synchronously on every insert. Members see one event per real purchase; anything uncertain stays visible as two events with a review flag until someone decides.

| Method | Path | Change |
| --- | --- | --- |
| POST | ingest, `/v1/transactions`, `/v1/transactions/bulk` | Responses add `event_id` and `match_outcome` |
| GET | `/v1/events` | New: deduplicated list, each event with its records and `review_state` |
| GET | `/v1/transactions` | Unchanged, records now carry `event_id` |
| GET | `/v1/matches/review` | New: open `needs_review` decisions with both records, score and features |
| POST | `/v1/matches/{decision_id}/confirm` | New: link, write `confirmed` |
| POST | `/v1/matches/{decision_id}/reject` | New: keep separate, write `rejected`; never proposed again |
| POST | `/v1/events/{event_id}/split` | New: body `{"transaction_id": …}` names an original record in the event; that record and its re-deliveries move to a new event and a `split` decision is written (the undo for a wrong link). Naming a re-delivery returns 400. |

Every endpoint keeps `ensure_authorized(user_id, group_id)`; every lookup by id also filters on `group_id`, so an id from another group returns 404.

### Where the code goes

- `finsync/matching/`: pure functions `normalize`, `fingerprint`, `is_candidate`, `score`, `decide`.
- `finsync/storage/`: candidate query, event and decision writes, a `transaction()` context using `BEGIN IMMEDIATE` (after the PostgreSQL switch planned in [ADR 0006](../architecture/decisions/0006-framework-based-stack.md): a transaction-scoped advisory lock per group).
- `finsync/core/`: each ingest path calls one `_store_and_match(record)`; bulk import runs in one transaction with an `import_batch_id`.
- `finsync/evaluation/`: the evaluation runner (`python -m finsync.evaluation`).

## Testing and evaluation

- **Unit tests** (`tests/test_matching.py`): normalisation, fingerprint stability, each blocking gate, score boundaries at 0.60 and 0.85, runner-up margin.
- **Service tests** (`tests/test_matching_service.py`), one per scenario:

| Scenario | Expected |
| --- | --- |
| Notification, then manual entry for the same purchase, same day | `auto_linked`, one event |
| Manual first, notification later | Same (order independent) |
| Two notifications, same amount and merchant, 5 min apart | `separate` (same channel) |
| Same notification text twice | `exact_duplicate` |
| Two members log the same dinner manually | `auto_linked` or `needs_review` by score |
| Manual 1235 HUF vs notification −1234.56 HUF | Candidate via rounding, a = 0.7 |
| Manual without merchant vs two same-amount notifications | `needs_review` |
| Same amount and merchant, 4 days apart | `separate` |
| Same purchase in two groups | `separate` |
| Wrong auto-link, then split | Two events, `split` supersedes |
| Rejected pair re-imported | Not proposed again |
| Bulk import with invalid row 3 | Nothing stored, error names row 3 |
| Group B member confirms group A's decision | 404, nothing written |

- **Evaluation dataset and metrics:** see [evaluation-plan.md](../evaluation/evaluation-plan.md#1-transaction-matching).

## Open questions

1. Do the target banks print notification times in local time? If so, the parser needs a Europe/Budapest default before matching is evaluated.
2. Should two manual entries from the same member ever be linked, or always go to review?
3. Is a 48-hour window right for manual entries, or do people log expenses days later?
4. Foreign-currency card purchases are out of scope; confirm with the supervisor.
5. Split payments and refunds are out of scope for the first version.
6. An LLM could later score only the `needs_review` band as a comparison point.
7. Sheets rows can be edited after sending: treat an edit as a new version superseding the old record, or as a correction of the same record?
8. Client idempotency keys (Android, web) are a new request field; agree the header name and how long keys are kept.

## Implementation plan

Each step is a separate pull request with its tests; dates are in the [roadmap](../planning/roadmap.md).

1. ~~Schema migration: new columns, `events`, `match_decisions`, one event per existing row.~~ Done 2026-10-17.
2. ~~`finsync/matching/` with normalisation, fingerprint, blocking, scoring and decision, plus unit tests.~~ Done 2026-10-17.
3. ~~Wire matching into the three ingest paths; atomic bulk import; `event_id` and `match_outcome` in responses.~~ Done 2026-10-17, with `GET /v1/events`.
4. ~~Review and correction endpoints with service and permission tests.~~ Done 2026-10-17.
5. Synthetic evaluation dataset and the evaluation runner; tune on the development split, report on the test split.
