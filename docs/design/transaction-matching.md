# Transaction matching and duplicate detection

- Status: **Proposed** (not implemented)
- Date: 2026-10-09
- Decision record: [ADR 0004](../architecture/decisions/0004-event-based-transaction-matching.md)

## Summary

FinSync keeps every incoming record untouched and links records that describe the same purchase to one shared **event**, using a transparent rule-based score with two thresholds: link automatically, send to review, or keep separate.

The core rule that stops false merges: an event may hold at most one original record per **channel**, meaning a source type plus the member who submitted it. Exact re-deliveries of a record are kept for traceability but attached to the record they repeat, so they never count as a second record (step 2). Two notifications on the same phone with the same amount five minutes apart are always two purchases; a notification and a manual entry, or two members' manual entries, can be linked. Every decision is written to an append-only log, so it can be explained, confirmed or undone.

- **In scope:** exact re-import detection, cross-source matching, the review queue, undo, the data model, tests and the evaluation dataset.
- **Out of scope:** foreign-currency matching, split payments, LLM-assisted matching, authentication (see [Open questions](#open-questions)).

## Current state

Every call inserts a new row into `transactions` with no comparison against existing rows, so the same purchase sent twice becomes two rows.

| Entry point | Code | Source written | What reaches storage |
| --- | --- | --- | --- |
| `POST /v1/notifications/ingest` | `FinSyncService.ingest_notification` | `android_notification` | Amount, currency, merchant from regex; time to the minute; description `card_purchase:<merchant>` |
| `POST /v1/transactions` | `create_manual_transaction` | `manual` | Free-text description, optional merchant, ISO time (a date-only value becomes midnight) |
| `POST /v1/transactions/bulk` | `bulk_create_manual_transactions` | `manual` | Same as manual, one insert per row, no batch id |

Gaps that matter for matching:

- **No raw payload or source reference.** The notification text and spreadsheet row are discarded after parsing, so an exact re-import cannot be recognised and a decision cannot be traced back.
- **Bulk import is not one unit.** A failed row leaves earlier rows saved and a retry creates duplicates.
- **Time precision is lost.** A manual `2026-09-05` and a notification `2026-09-05 13:45` look 13 h 45 min apart.
- **Notification times are assumed UTC.** If banks print local time (likely, not verified), that is a 1–2 hour shift against a manual entry in Hungarian local time.
- **Sign convention is not enforced.** A positive manual `4990` would never match a `-4990` notification.
- **Merchant fields differ in shape.** Notifications carry a clean merchant; manual rows often only have a description such as "Tesco weekly shop".

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
- `finsync/storage/`: candidate query, event and decision writes, a `transaction()` context using `BEGIN IMMEDIATE` (on PostgreSQL, if [ADR 0006](../architecture/decisions/0006-framework-based-stack.md) is accepted: a transaction-scoped advisory lock per group).
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

## Implementation plan

Each step is a separate pull request with its tests; dates are in the [roadmap](../planning/roadmap.md).

1. Schema migration: new columns, `events`, `match_decisions`, one event per existing row.
2. `finsync/matching/` with normalisation, fingerprint, blocking, scoring and decision, plus unit tests.
3. Wire matching into the three ingest paths; atomic bulk import; `event_id` and `match_outcome` in responses.
4. Review and correction endpoints with service and permission tests.
5. Synthetic evaluation dataset and the evaluation runner; tune on the development split, report on the test split.
