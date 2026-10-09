# Semester roadmap (Szakdolgozat I., autumn 2026)

- Last updated: 2026-10-09
- Owner: Bence Varga

This roadmap turns the course deadlines into concrete, verifiable steps. Each deadline has a target file in [milestones/](milestones/README.md) with acceptance criteria and a checklist.

## Course deadlines

All deadlines are 23:59 Hungarian time. Each milestone is announced by e-mail with a reference to the tagged repository version.

| Date | Milestone | Expected result | Tag |
| --- | --- | --- | --- |
| 2026-10-02 | – | First status e-mail and repository sharing (done) | – |
| 2026-10-09 | [M0](milestones/m0-2026-10-09-semester-commitment.md) | Semester commitment refined: what the prototype will do, how it is verified, what is done, next steps | `v0.1.0` |
| 2026-11-06 | [M1](milestones/m1-2026-11-06-working-core.md) | Working core: one complete processing flow end to end; working experimental solution, test or measurement for the main technical risk | `v0.2.0` |
| 2026-12-04 | [M2](milestones/m2-2026-12-04-integrated-prototype.md) | Integrated prototype: committed core flows work together with proper data handling, basic error handling and tests | `v0.3.0` |
| 2027-01-15 | [M3](milestones/m3-2027-01-15-preliminary-package.md) | Preliminary final package: runnable system, test and measurement results, short report, known limitations, Szakdolgozat II. plan | `v0.9.0` |
| 2027-01-30 | [M4](milestones/m4-2027-01-30-final-package.md) | Corrected final package: fixes from feedback, final tag and a short fix log | `v1.0.0` |

The first working version must not slip to January: M3 is reviewed and M4 only fixes feedback.

## Semester scope

### Committed for this semester

The professional core of the thesis is **transaction matching across sources**. The semester delivers it end to end:

1. **Ingestion** from three sources through one pipeline: banking notification text, manual entry, and bulk import of spreadsheet-export rows (CSV/JSON).
2. **Normalization** into one transaction model (sign/direction, UTC time with precision, merchant key).
3. **Matching and duplicate detection** with the event model, exact re-delivery detection, scored candidate matching and an append-only decision log ([design](../design/transaction-matching.md)).
4. **Review and correction:** list uncertain matches, confirm, reject, split.
5. **Measurement:** a labelled synthetic dataset and an evaluation runner reporting precision, recall, false-merge rate, missed-duplicate rate and review rate, with a threshold sweep.
6. **Data handling and security basics:** atomic writes, schema migrations, server-side validation, group isolation, and a simple authentication (server-issued per-user API tokens) replacing client-supplied identity headers.
7. **Rule-based categorization** kept as the baseline.
8. **Documentation and setup guide** that let someone else run the system and the evaluation from the repository.

### Deferred to Szakdolgozat II.

- Android notification collector app.
- Direct Google Sheets integration (this semester the spreadsheet source is an exported file).
- LLM-based categorization and its comparison with the rule baseline (only a dataset and the baseline numbers this semester, if time allows).
- Full security and privacy evaluation, retention rules, user interface, deployment.

### How it is verified

| Claim | Verification |
| --- | --- |
| Flows work end to end | Service and HTTP tests per scenario (`python -m unittest discover -s tests`) |
| Matching is correct | Labelled dataset, metrics from `python -m finsync.evaluation`, results in [evaluation/](../evaluation/README.md) |
| Groups are isolated | Cross-group access tests for every endpoint |
| Others can run it | [Getting started](../guides/getting-started.md) tried on a clean machine before M3 |

## Plan by phase

Weeks start on Monday. Each line is roughly one pull request with its tests and documentation.

### Phase 0 — Foundations (done by 2026-10-09, M0)

- [x] Minimal backend: notification parsing, manual and bulk entry, categorization, SQLite, group checks, tests.
- [x] Matching design ([design/transaction-matching.md](../design/transaction-matching.md)).
- [x] Documentation structure, layered package layout, roadmap.
- [ ] Open pull requests merged: whole-word categorization (#2), atomic bulk import and amount validation (#3).

### Phase 1 — Working core (2026-10-12 → 2026-11-06, M1)

Goal: the main technical risk, telling duplicates from look-alike purchases, has a working, measured solution.

| Week | Work |
| --- | --- |
| Oct 12–18 | Schema versioning and migration: `events`, `match_decisions`, new `transactions` columns. Decide the notification time-zone question. Start the synthetic dataset generator. |
| Oct 19–25 | `finsync/matching/`: normalization, fingerprint, blocking, scoring, decision, with unit tests. |
| Oct 26–Nov 1 | Wire matching into all ingest paths in one transaction; `event_id` and `match_outcome` in responses; `GET /v1/events`. Dataset v1 (~100 records). |
| Nov 2–6 | Evaluation runner, first measurement on the development split, results file, M1 notes, tag `v0.2.0`. |

### Phase 2 — Integrated prototype (2026-11-09 → 2026-12-04, M2)

Goal: all committed flows work together with proper data handling and error handling.

| Week | Work |
| --- | --- |
| Nov 9–15 | Review and correction: `GET /v1/matches/review`, confirm, reject, split, with permission tests. |
| Nov 16–22 | Spreadsheet-export import (CSV) with `import_batch_id` and `source_ref`; source traceability in responses. |
| Nov 23–29 | Authentication with per-user API tokens (hashed); request size limits; consistent error responses; cross-group tests on every endpoint. |
| Nov 30–Dec 4 | Full dataset (200–300 records), threshold tuning on development split, report on test split; M2 notes, tag `v0.3.0`. |

### Phase 3 — Hardening and preliminary package (2026-12-07 → 2027-01-15, M3)

| Week | Work |
| --- | --- |
| Dec 7–13 | Fix gaps found at M2; edge-case tests (late manual entries, rounded amounts, time zones). |
| Dec 14–20 | **Feature freeze (Dec 18).** Documentation matches the implementation; setup guide tested on a clean machine. |
| Dec 21–Jan 3 | Buffer (holidays). |
| Jan 4–10 | Final measurement run, results report, known limitations, Szakdolgozat II. plan, AI-usage log completed. |
| Jan 11–15 | Short professional report; M3 notes, tag `v0.9.0`, e-mail. |

### Phase 4 — Corrections (2027-01-16 → 2027-01-30, M4)

- Apply review feedback; record each fix in the fix log ([releases/](../releases/README.md)).
- Tag `v1.0.0`, e-mail with the final commit id.

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Matching rules produce false merges on real-looking data | Core claim fails | Channel rule, review band, measured false-merge rate; thresholds tuned on a separate split |
| Unknown real notification formats and time zones | Parser or matching off by hours | Decide time-zone default in Phase 1; keep raw payload for re-processing |
| Labelled dataset too small or biased | Weak evaluation | Generate scenarios per category from the design; document generation rules |
| Scope creep (Android, Sheets, LLM) | Core not finished | Deferred to Szakdolgozat II. explicitly |
| Late first working version | No time for review | M1 requires a measured end-to-end flow; feature freeze on Dec 18 |

## Szakdolgozat II. continuation (outline)

1. Android notification collector feeding the existing ingest endpoint.
2. Google Sheets integration on top of the bulk import.
3. LLM categorization compared with the rule baseline; optionally an LLM scorer for the `needs_review` band only.
4. Full security and privacy evaluation; retention and deletion rules.
5. A simple user interface for groups and the review queue.

The detailed plan is written in M3.

## Change log

| Date | Change |
| --- | --- |
| 2026-10-09 | First version. |
