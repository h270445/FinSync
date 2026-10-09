# Semester roadmap (Szakdolgozat I., autumn 2026)

- Last updated: 2026-10-09
- Owner: Bence Varga

This roadmap turns the course deadlines into concrete, verifiable steps. Each deadline has a target file in [milestones/](milestones/README.md) with acceptance criteria and a checklist.

## Course deadlines

All deadlines are 23:59 Hungarian time. Each milestone is announced by e-mail with a reference to the tagged repository version.

| Deadline | Internal target | Milestone | Expected result | Tag |
| --- | --- | --- | --- | --- |
| 2026-10-02 | – | – | First status e-mail and repository sharing (done) | – |
| 2026-10-09 | – | [M0](milestones/m0-2026-10-09-semester-commitment.md) | Semester commitment refined: what the prototype will do, how it is verified, what is done, next steps | `v0.1.0` |
| 2026-11-06 | 2026-10-30 | [M1](milestones/m1-2026-11-06-working-core.md) | Working core: one complete processing flow end to end; working experimental solution, test or measurement for the main technical risk | `v0.2.0` |
| 2026-12-04 | 2026-11-27 | [M2](milestones/m2-2026-12-04-integrated-prototype.md) | Integrated prototype: committed core flows work together with proper data handling, basic error handling and tests | `v0.3.0` |
| 2027-01-15 | 2027-01-08 | [M3](milestones/m3-2027-01-15-preliminary-package.md) | Preliminary final package: runnable system, test and measurement results, short report, known limitations, Szakdolgozat II. plan | `v0.9.0` |
| 2027-01-30 | as feedback arrives | [M4](milestones/m4-2027-01-30-final-package.md) | Corrected final package: fixes from feedback, final tag and a short fix log | `v1.0.0` |

The first working version must not slip to January: M3 is reviewed and M4 only fixes feedback.

## Planning rules

- **Course deadlines are the latest dates, not start dates.** Each milestone has an internal target about one week earlier; the week in between is buffer.
- **Work rolls forward.** As soon as a milestone's acceptance criteria are met, work on the next milestone starts, even if the course deadline is weeks away.
- **Submission is a snapshot of `main`.** At each deadline the current `main` commit is tagged and submitted, even if it already contains work for the next milestone.
- **Side tracks start early.** Work that does not depend on the current milestone (datasets, the Android spike, ADRs for open questions) is done in parallel to remove risks early.

## Semester scope

Every capability listed in the [project overview](../overview.md#planned--not-yet-implemented) is committed for **this semester**, the Android and Google Sheets clients in a reduced scope. Szakdolgozat II. is reserved for refinement based on the evaluation results and for writing the thesis.

### Committed for this semester

The professional core of the thesis is **transaction matching across sources**; it is built first because it is the main technical risk.

1. **Transaction matching and duplicate detection** with the event model, exact re-delivery detection, scored candidate matching and an append-only decision log ([design](../design/transaction-matching.md)).
2. **Match review and correction:** list uncertain matches, confirm, reject, split.
3. **Source traceability:** raw payload, source reference, import batch and decision history for every record.
4. **Authentication and stronger access control:** server-issued per-user API tokens replace client-supplied identity headers.
5. **Measurement:** labelled synthetic datasets and an evaluation runner for matching, compared with a naive baseline that stores every incoming row separately.
6. **LLM-based categorization** behind the same interface as the rule-based categorizer, compared with it on one hand-labelled dataset (accuracy, error patterns, time and cost); members can correct a suggested category.
7. **Web app** (React and TypeScript): event list, event detail, match review and correction, category correction ([design](../design/user-interface.md), [ADR 0005](../architecture/decisions/0005-web-client-first.md)).
8. **Security and privacy evaluation:** group isolation, input validation, atomicity, traceability and AI-boundary tests, plus a data-minimization review.
9. **Android integration (reduced scope):** a minimal app that forwards one bank's notification format to the ingest endpoint.
10. **Spreadsheet input (reduced scope):** file import of spreadsheet exports; a Google Sheets script that posts new rows only if time allows.
11. **Documentation and setup guide** that let someone else run the system and the evaluation from the repository.

### Priority if time runs short

The order above is the priority order, following the supervisor's advice (2026-10-09) to keep enough time for the core. Items 1–5 are never cut; the web app (7) may shrink to the event list and review screens. If a later item slips, it is delivered in a reduced but working form (for example, the Android app supports one bank's format) rather than dropped, and the reduction is recorded in the change log below.

### How it is verified

| Claim | Verification |
| --- | --- |
| Flows work end to end | Service and HTTP tests per scenario (`python -m unittest discover -s tests`) |
| Matching is correct | Labelled dataset, metrics from `python -m finsync.evaluation`, results in [evaluation/](../evaluation/README.md) |
| LLM vs rules | Accuracy and error patterns of both categorizers on the same labelled dataset |
| Clients work | Demo: a notification on the phone and a new sheet row both appear as one matched event in the web app, where an uncertain match is reviewed |
| Groups are isolated | Cross-group access tests for every endpoint |
| Others can run it | [Getting started](../guides/getting-started.md) tried on a clean machine before M3 |

## Plan by phase

Weeks start on Monday. Each line is roughly one pull request with its tests and documentation. Dates are planned starts; if a step finishes early, the next one starts immediately.

### Phase 0 — Foundations (done by 2026-10-09, M0)

- [x] Minimal backend: notification parsing, manual and bulk entry, categorization, SQLite, group checks, tests.
- [x] Matching design ([design/transaction-matching.md](../design/transaction-matching.md)).
- [x] Documentation structure, layered package layout, roadmap.
- [ ] Open pull requests merged: whole-word categorization (#2), atomic bulk import and amount validation (#3).

### Phase 1 — Working core (2026-10-12 → internal target 2026-10-30, M1 due 2026-11-06)

Goal: the main technical risk, telling duplicates from look-alike purchases, has a working, measured solution.

| Week | Main track | Side track |
| --- | --- | --- |
| Oct 12–18 | Stack switch on top of the existing backend ([ADR 0006](../architecture/decisions/0006-framework-based-stack.md)): FastAPI routes, SQLAlchemy and Alembic on PostgreSQL, Docker Compose, CI; existing parsing, categorization and tests carried over. First Alembic migration: `events`, `match_decisions`, traceability columns. Time-zone decision (ADR). Matching normalization and fingerprint. | Synthetic matching dataset generator. Figma wireframes for the event list, review queue and Android setup. |
| Oct 19–25 | Blocking, scoring and decision; matching wired into all ingest paths in one transaction; `event_id`, `match_outcome`; `GET /v1/events`. | Android spike: notification listener on a real device logging the supported formats. |
| Oct 26–30 | Dataset v1 (~100 records), evaluation runner, first results file. **M1 content complete.** | ADR for how the Sheets script reaches the API. Web app skeleton (React, Vite, generated API types) with a read-only event list. |

### Phase 2 — Integrated prototype (2026-11-02 → internal target 2026-11-27, M2 due 2026-12-04)

Goal: every committed component exists and works together with proper data handling and error handling.

| Week | Main track | Side track |
| --- | --- | --- |
| Nov 2–8 | Authentication with per-user API tokens (hashed); review and correction endpoints with permission tests. M1 submitted from `main` (tag `v0.2.0`). | Labelled categorization dataset. Styled screens in Figma. |
| Nov 9–15 | Web app: sign-in, review queue, event detail with split. Request size limits; cross-group tests on every endpoint. | Android app (one bank format): token setup, sending to `/v1/notifications/ingest`, retry without duplicates. |
| Nov 16–22 | File import of spreadsheet exports with `source_ref` and `import_batch_id`; grow the matching dataset to 200–300 records. | Google Sheets script posting rows to `/v1/transactions/bulk`, if on schedule. Web app overview and manual entry. |
| Nov 23–27 | LLM categorizer behind the categorizer interface with output validation; category correction (API and web app); end-to-end demo. **M2 content complete.** | |

### Phase 3 — Evaluation, hardening and preliminary package (2026-11-30 → internal target 2027-01-08, M3 due 2027-01-15)

| Week | Work |
| --- | --- |
| Nov 30–Dec 6 | Threshold tuning on the development split, report on the test split. M2 submitted from `main` (tag `v0.3.0`). |
| Dec 7–13 | LLM vs rule categorization measurement; security and privacy evaluation (tests and data-minimization review). |
| Dec 14–18 | Fix gaps found in evaluation; documentation matches the implementation; setup guide tested on a clean machine. **Feature freeze (Dec 18).** |
| Dec 21–Jan 3 | Buffer (holidays). |
| Jan 4–8 | Final measurement run, short professional report, known limitations, Szakdolgozat II. plan, AI-usage log completed. **M3 content complete.** |
| Jan 11–15 | Review own package, small fixes; M3 notes, tag `v0.9.0`, e-mail (can be sent as soon as the package is ready). |

### Phase 4 — Corrections (2027-01-16 → 2027-01-30, M4)

- Apply review feedback as it arrives; record each fix in the fix log ([releases/](../releases/README.md)).
- Tag `v1.0.0`, e-mail with the final commit id.

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Stack switch (FastAPI, PostgreSQL, React, Compose) slows the start of Phase 1 | M1 core late | Existing logic is carried over, not rewritten; switch in the first week only; matching stays pure Python; fallback: FastAPI and SQLAlchemy on SQLite until M2 |
| Full scope is large for one semester (including the web app) | Late or shallow components | Matching first; priority order above; reduced-but-working fallback; feature freeze on Dec 18 |
| Matching rules produce false merges on real-looking data | Core claim fails | Channel rule, review band, measured false-merge rate; thresholds tuned on a separate split |
| Unknown real notification formats and time zones | Parser or matching off by hours | Decide time-zone default in Phase 1; keep raw payload for re-processing |
| Android notification access and testing need a real device and real bank apps | Android component slips | Spike on a real device already in October; test with self-sent notifications in the supported formats; never store real personal data |
| Google Sheets script must reach the API | Integration cannot be demonstrated | Decide the reachability approach in an ADR in October (for example a temporary tunnel for the demo) |
| LLM API cost, latency and data exposure | Unusable or unsafe comparison | Send only description and merchant; validate output against the category list; measure cost and latency |
| Labelled datasets too small or biased | Weak evaluation | Generate scenarios per category from the design; document generation rules |
| Late first working version | No time for review | M1 requires a measured end-to-end flow; internal targets one week before each deadline |

## Szakdolgozat II. (outline)

1. Refinement of matching, categorization and the clients based on the M3/M4 evaluation and feedback.
2. Fuller Android and Google Sheets clients.
3. Additional measurements where the semester's results leave questions open.
4. Writing the thesis.

The detailed plan is written in M3.

## Change log

| Date | Change |
| --- | --- |
| 2026-10-09 | First version. |
| 2026-10-09 | Added the web app as committed item 4 (main user interface, built before the Android app); Figma wireframes and web app work added to Phases 1–2 ([ADR 0005](../architecture/decisions/0005-web-client-first.md)). |
| 2026-10-09 | Supervisor feedback: core first, build on the existing backend, adjust client scope. Priority order changed (authentication and measurement moved up, naive baseline and category correction added, Android and Sheets reduced); the framework-based stack (FastAPI, PostgreSQL, React, Docker Compose) stays this semester, built on the existing backend logic ([ADR 0006](../architecture/decisions/0006-framework-based-stack.md)). |
