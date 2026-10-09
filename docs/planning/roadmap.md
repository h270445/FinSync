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

Every capability listed in the [project overview](../overview.md#planned--not-yet-implemented) is committed for **this semester**. Szakdolgozat II. is reserved for refinement based on the evaluation results and for writing the thesis.

### Committed for this semester

The professional core of the thesis is **transaction matching across sources**; it is built first because it is the main technical risk.

1. **Transaction matching and duplicate detection** with the event model, exact re-delivery detection, scored candidate matching and an append-only decision log ([design](../design/transaction-matching.md)).
2. **Match review and correction:** list uncertain matches, confirm, reject, split.
3. **Source traceability:** raw payload, source reference, import batch and decision history for every record.
4. **Android integration:** a minimal Android app that reads supported banking notifications and sends them to the ingest endpoint.
5. **Google Sheets integration:** a sheet-side script that sends new rows to the bulk endpoint, plus file import of spreadsheet exports.
6. **LLM-based categorization** behind the same interface as the rule-based categorizer, compared with it on one labelled dataset.
7. **Authentication and stronger access control:** server-issued per-user API tokens replace client-supplied identity headers.
8. **Security and privacy evaluation:** group isolation, input validation, atomicity, traceability and AI-boundary tests, plus a data-minimization review.
9. **Measurement:** labelled synthetic datasets and an evaluation runner for matching and categorization.
10. **Documentation and setup guide** that let someone else run the system and the evaluation from the repository.

### Priority if time runs short

The order above is the priority order. Items 1–3 and 7 are never cut. If a later item slips, it is delivered in a reduced but working form (for example, the Android app supports one bank's format) rather than dropped, and the reduction is recorded in the change log below.

### How it is verified

| Claim | Verification |
| --- | --- |
| Flows work end to end | Service and HTTP tests per scenario (`python -m unittest discover -s tests`) |
| Matching is correct | Labelled dataset, metrics from `python -m finsync.evaluation`, results in [evaluation/](../evaluation/README.md) |
| LLM vs rules | Accuracy and error patterns of both categorizers on the same labelled dataset |
| Clients work | Demo: a notification on the phone and a new sheet row both appear as one matched event |
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
| Oct 12–18 | Schema versioning and migration: `events`, `match_decisions`, traceability columns. Decide the notification time-zone question. Start the synthetic dataset generator. |
| Oct 19–25 | `finsync/matching/`: normalization, fingerprint, blocking, scoring, decision, with unit tests. |
| Oct 26–Nov 1 | Wire matching into all ingest paths in one transaction; `event_id` and `match_outcome` in responses; `GET /v1/events`. Dataset v1 (~100 records). |
| Nov 2–6 | Evaluation runner, first measurement on the development split, results file, M1 notes, tag `v0.2.0`. |

### Phase 2 — Integrated prototype (2026-11-09 → 2026-12-04, M2)

Goal: every committed component exists and works together with proper data handling and error handling.

| Week | Work |
| --- | --- |
| Nov 9–15 | Authentication with per-user API tokens (hashed); review and correction endpoints (review list, confirm, reject, split) with permission tests. |
| Nov 16–22 | Android app: notification listener for the supported formats, token setup, sending to `/v1/notifications/ingest`, retry without duplicates (fingerprint). |
| Nov 23–29 | Google Sheets script posting new rows to `/v1/transactions/bulk` with `source_ref`; file import of exports; request size limits; cross-group tests on every endpoint. |
| Nov 30–Dec 4 | LLM categorizer behind the categorizer interface with output validation; labelled categorization dataset; end-to-end demo across all sources; M2 notes, tag `v0.3.0`. |

### Phase 3 — Evaluation, hardening and preliminary package (2026-12-07 → 2027-01-15, M3)

| Week | Work |
| --- | --- |
| Dec 7–13 | Full matching dataset (200–300 records), threshold tuning on development split, report on test split. LLM vs rule categorization measurement. |
| Dec 14–20 | Security and privacy evaluation (tests and data-minimization review). **Feature freeze (Dec 18).** |
| Dec 21–Jan 3 | Buffer (holidays). |
| Jan 4–10 | Fix gaps found in evaluation; final measurement run; documentation matches the implementation; setup guide tested on a clean machine; AI-usage log completed. |
| Jan 11–15 | Short professional report, known limitations, Szakdolgozat II. plan; M3 notes, tag `v0.9.0`, e-mail. |

### Phase 4 — Corrections (2027-01-16 → 2027-01-30, M4)

- Apply review feedback; record each fix in the fix log ([releases/](../releases/README.md)).
- Tag `v1.0.0`, e-mail with the final commit id.

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Full scope is large for one semester | Late or shallow components | Matching first; priority order above; reduced-but-working fallback; feature freeze on Dec 18 |
| Matching rules produce false merges on real-looking data | Core claim fails | Channel rule, review band, measured false-merge rate; thresholds tuned on a separate split |
| Unknown real notification formats and time zones | Parser or matching off by hours | Decide time-zone default in Phase 1; keep raw payload for re-processing |
| Android notification access and testing need a real device and real bank apps | Android component slips | Test with self-sent notifications in the supported formats; never store real personal data |
| Google Sheets script must reach the API | Integration cannot be demonstrated | Decide the reachability approach in an ADR before Nov 23 (for example a temporary tunnel for the demo) |
| LLM API cost, latency and data exposure | Unusable or unsafe comparison | Send only description and merchant; validate output against the category list; measure cost and latency |
| Labelled datasets too small or biased | Weak evaluation | Generate scenarios per category from the design; document generation rules |
| Late first working version | No time for review | M1 requires a measured end-to-end flow |

## Szakdolgozat II. (outline)

1. Refinement of matching, categorization and the clients based on the M3/M4 evaluation and feedback.
2. Additional measurements where the semester's results leave questions open.
3. Writing the thesis.

The detailed plan is written in M3.

## Change log

| Date | Change |
| --- | --- |
| 2026-10-09 | First version. |
