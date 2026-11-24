# Semester roadmap (Szakdolgozat I., autumn 2026)

- Last updated: 2026-11-24
- Owner: Bence Varga

This roadmap turns the course deadlines into concrete, verifiable steps. Each deadline has a target file in [milestones/](milestones/README.md) with acceptance criteria and a checklist.

## Course deadlines

All deadlines are 23:59 Hungarian time. Each milestone is announced by e-mail with a reference to the tagged repository version.

| Deadline | Internal target | Milestone | Expected result | Tag |
| --- | --- | --- | --- | --- |
| 2026-10-02 | – | – | First status e-mail and repository sharing (done) | – |
| 2026-10-09 | – | [M0](milestones/m0-2026-10-09-semester-commitment.md) | Semester commitment refined: what the prototype will do, how it is verified, what is done, next steps | `0.1.0` |
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
- [x] Fixes from the open pull requests carried over: whole-word categorization (#2), atomic bulk import and amount validation (#3).

### Phase 1 — Working core (2026-10-12 → internal target 2026-10-30, M1 due 2026-11-06)

Goal: the main technical risk, telling duplicates from look-alike purchases, has a working, measured solution.

**Order changed on 2026-10-17:** matching came first on the existing SQLite backend (normalisation, fingerprint, blocking, scoring, decision, wiring, `GET /v1/events` and the review endpoints, all done on Oct 17), because the supervisor named the working Nov 6 core as the deciding factor. The stack switch follows once the core works; if it would delay M1, the SQLite fallback stays until M2.

| Week | Main track | Side track |
| --- | --- | --- |
| Oct 12–18 | Stack switch on top of the existing backend ([ADR 0006](../architecture/decisions/0006-framework-based-stack.md)): FastAPI routes, SQLAlchemy and Alembic on PostgreSQL, Docker Compose, CI; existing parsing, categorization and tests carried over. First Alembic migration: `events`, `match_decisions`, traceability columns. Time-zone decision (ADR). Matching normalization and fingerprint. | Synthetic matching dataset generator. Figma wireframes for the event list, review queue and Android setup. |
| Oct 19–25 | Interim note to the supervisor by Oct 22 (matching status, whether the SQLite fallback was needed). Blocking, scoring and decision; matching wired into all ingest paths in one transaction; `event_id`, `match_outcome`; `GET /v1/events`. | Android spike: notification listener on a real device logging the supported formats. Spike app and emulator rounds done on Oct 24–26 ([findings](../design/android-notification-spike.md)); the phone test with OTP Bank and Revolut moved to Oct 27. |
| Oct 26–30 | Dataset v1 (~100 records), evaluation runner, first results file. **M1 content complete.** | ADR for how the Sheets script reaches the API. Web app skeleton (React, Vite, generated API types) with a read-only event list. |

### Phase 2 — Integrated prototype (2026-11-02 → internal target 2026-11-27, M2 due 2026-12-04)

Goal: every committed component exists and works together with proper data handling and error handling.

| Week | Main track | Side track |
| --- | --- | --- |
| Nov 2–8 | Authentication with per-user API tokens (hashed) (done Nov 2, [ADR 0009](../architecture/decisions/0009-api-tokens.md)); review and correction endpoints already done on Oct 17. M1 submitted from `main` (tag `v0.2.0` on Nov 2, e-mail sent late on Nov 7). Tests run on Windows (time-zone data, closed database connections). | Labelled categorization dataset (done Nov 8, 200 synthetic items, [datasets.md](../evaluation/datasets.md#testsdatacategorization_evalcsv--categorization-version-1)). Styled screens in Figma. |
| Nov 9–15 | Web app: sign-in, review queue, event detail with split (review queue and event detail with split done Nov 8, decision history Nov 11–12; password sign-in with e-mail or member id done Nov 12, [ADR 0010](../architecture/decisions/0010-web-sign-in.md)). Request size limits; cross-group tests on every endpoint (done early with the tokens on Nov 2). Agent skills brought forward (done Nov 12). | Android app (one bank format): token setup, sending to `/v1/notifications/ingest`, retry without duplicates (done Nov 12 and tested on the emulator; the test on the real phone is the author's step). |
| Nov 16–22 | Storage on SQLAlchemy and Alembic with PostgreSQL, Docker Compose (ADR 0006 step 2, time-boxed; if it runs over, SQLite stays and the rest of the week goes ahead) (done early on Nov 12). File import of spreadsheet exports with `source_ref` and `import_batch_id` (CSV and XLSX import with the W7 screen done early on Nov 12); grow the matching dataset to 200–300 records. | Google Sheets script posting rows to `/v1/transactions/bulk`, if on schedule. Web app overview and manual entry (manual entry W6 done Nov 14). W2 overview on deduplicated events, transfers within the group excluded, items waiting for review flagged; W8 settings with members, API tokens (create, revoke) and group merchant → category rules, the first layer of the hybrid categorizer ([supervisor, Nov 16](supervisor-feedback.md#2026-11-16--reply-to-the-weekly-report-of-nov-915)) (W2 and W8 done Nov 19, with admin/member roles). |
| Nov 23–27 | LLM categorizer behind the categorizer interface with output validation; category correction with the "mixed" flag and category lines (API and web app, [design](../design/categorization.md#mixed-baskets)); money transfers between the group's own accounts (`transfer` direction, [design](../design/categorization.md#money-transfers)) (own-accounts list and `transfer` direction done early on Nov 19); end-to-end demo. Hybrid categorizer measured on the 200-item dataset: merchant/keyword layer (built early on Nov 19: group rules, then a built-in Hungarian merchant and keyword dictionary) + model/LLM layer + abstention threshold ("Bizonytalan"), coverage–accuracy curve, latency and cost (LLM layer, measurement runner and runbook built early on Nov 19, [ADR 0011](../architecture/decisions/0011-llm-categorization-layer.md); paid run done Nov 24, [report](../evaluation/results/2026-11-24-categorization-hybrid.md); wiring the LLM into the core with the author's scheduling settings, [design](../design/categorization.md#when-the-llm-is-called-proposed-by-the-author-2026-11-19), done Nov 24). Category correction with the mixed flag, category lines and transfer marking in the API and on W2, W3, W4 done Nov 24 (Tuesday's and Wednesday's items in one session). Thursday's items done early on Nov 24 as well: the LLM setting on W8, [ADR 0013](../architecture/decisions/0013-llm-in-the-live-flow.md) and ADR 0011's measured result, the six design views checked against the code, the demo seed and [demo guide](../guides/demo.md); open: the author's dry run of the demo with the emulator and the skill choice. The correction follows the supervisor's UX principles of Nov 23: source and uncertainty of every suggestion visible, few clicks to correct or split, merchant memory learns a rule only for non-mixed merchants ([design](../design/categorization.md#review-in-the-web-app)). Role changes only from the web session, like token management (least privilege, [ADR 0012](../architecture/decisions/0012-no-multi-factor-authentication.md), done Nov 23). Day-by-day plan: [M2 closing schedule](m2-closing-schedule.md). **M2 content complete; package sent to the supervisor on Nov 27.** | Real-device Android test of the OTP forwarding (the author's step, before M2) (done Nov 20–21 with one real purchase). Design views 1–2 finalised after W2 and W8 (drafted early on Nov 19); views 5 and 6 show the optional outbound model call and its data-minimization rule once the LLM layer is wired in (all six checked against the code and updated on Nov 24, waiting for review). Android A1/A2 split: later cleanup, lower priority than the measurement, the category correction and the demo ([supervisor, Nov 23](supervisor-feedback.md#2026-11-23--reply-to-the-weekly-report-of-nov-1622)). The skill (1, at most 2) for the methods chapter chosen ([supervisor, Nov 16](supervisor-feedback.md#2026-11-16--reply-to-the-weekly-report-of-nov-915)). |

### Phase 3 — Evaluation, hardening and preliminary package (2026-11-30 → internal target 2027-01-08, M3 due 2027-01-15)

| Week | Work |
| --- | --- |
| Nov 30–Dec 6 | Supervisor feedback on the Nov 27 package fixed by Dec 2, freeze on Dec 3 ([M2 closing schedule](m2-closing-schedule.md)). Threshold tuning on the development split, report on the test split. M2 submitted from `main` (tag `v0.3.0`). |
| Dec 7–13 | LLM vs rule categorization measurement; security and privacy evaluation (tests and data-minimization review). If time allows, a small local OpenAI-compatible model measured with the same runner after the paid baseline (privacy–accuracy–cost comparison, [ADR 0011](../architecture/decisions/0011-llm-categorization-layer.md)); otherwise at the start of Szakdolgozat II. |
| Dec 14–18 | Fix gaps found in evaluation; documentation matches the implementation; setup guide tested on a clean machine. Skeleton of chapters 1–3 of the Hungarian thesis manuscript (SZTE format) started from `docs/` and the [thesis map](../thesis-map.md). **Feature freeze (Dec 18).** |
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

## Future work (options beyond the committed scope)

Candidates for Szakdolgozat II. or for the thesis's "Limitations and future work" section. None of them is committed; each is chosen, or left as a mention, when the M3 plan is written. Collected on 2026-11-19 from the author's ideas (e-mail confirmation, forgotten password, a group chat with an LLM adviser) and the discussion that followed.

**Near, small (could still fit before the thesis):**

- **E-mail confirmation and forgotten password.** Both need the same mechanism: a single-use, expiring token sent by e-mail. Once it exists, inviting a member to a group by e-mail can build on it (today members are added on the command line). Listed as future work in [ADR 0010](../architecture/decisions/0010-web-sign-in.md).
- **Step-up re-authentication and a sign-in attempt limit.** Re-authentication before issuing an API token or changing a role is the next step proposed in [ADR 0012](../architecture/decisions/0012-no-multi-factor-authentication.md) (accepted 2026-11-23; both routes already work only from a web session); the attempt limit belongs to the December security evaluation ([ADR 0010](../architecture/decisions/0010-web-sign-in.md)).
- *Already scheduled, not future work:* the scheduled LLM run and members setting uncertain categories themselves come with the category correction (see the change log, 2026-11-19).

**Medium term:**

- **Budgets and alerts** per category and month. Closely tied to the thesis's goal of accurate spending tracking.
- **Self-hosted LLM** (for example LM Studio), compared with the cloud model on the same frozen dataset; the layer already supports an OpenAI-compatible server ([ADR 0011](../architecture/decisions/0011-llm-categorization-layer.md)). Planned since 2026-11-23 at the supervisor's suggestion, after the paid baseline: in the December refinement if time allows, else at the start of Szakdolgozat II. (see Dec 7–13).
- **Multi-factor authentication** (TOTP or passkeys) for the web sign-in, required before FinSync holds real households' data outside a test setting ([ADR 0012](../architecture/decisions/0012-no-multi-factor-authentication.md)).
- **Export** of the group's data (CSV or Google Sheets).

**Further out, a mention only:**

- **Group chat with an LLM adviser.** A chat between members is a separate product and does not serve the main goal. The adviser part is interesting in a narrower form: "ask about your data" (for example "why did we spend more in November?"), built on the existing overview endpoint, sending the LLM only aggregated figures, never individual records.
- **Direct bank connection (PSD2 / open banking).** Would replace notification reading and file import, but needs a licence or a licensed provider and is a large piece of work.

## Change log

| Date | Change |
| --- | --- |
| 2026-10-09 | First version. |
| 2026-10-09 | Added the web app as committed item 4 (main user interface, built before the Android app); Figma wireframes and web app work added to Phases 1–2 ([ADR 0005](../architecture/decisions/0005-web-client-first.md)). |
| 2026-10-09 | Supervisor feedback: core first, build on the existing backend, adjust client scope. Priority order changed (authentication and measurement moved up, naive baseline and category correction added, Android and Sheets reduced); the framework-based stack (FastAPI, PostgreSQL, React, Docker Compose) stays this semester, built on the existing backend logic ([ADR 0006](../architecture/decisions/0006-framework-based-stack.md)). |
| 2026-10-16 | Supervisor accepted the commitment and schedule ([feedback](supervisor-feedback.md#2026-10-16--reply-to-the-m0-e-mail)); added the Oct 22 interim note, the baseline and hand-decided examples to M1, and carrying over the PR #2 and #3 fixes. |
| 2026-10-26 | Android spike: emulator rounds done, phone test moved to Oct 27; ADR 0007 accepted (HTTPS tunnel for the Sheets script and the Android app). The Oct 22 interim note was not sent on time and goes out with these updates. |
| 2026-10-27 | First real OTP notification captured on the phone; purchase test on Oct 28, the interim note goes out that evening with its result. |
| 2026-10-26 | Author's decision: transfers between the group's own or family accounts are booked as `transfer`, not as expense or income, using a per-group list of own accounts and counterparties (M2, Nov 23–27); linking the two sides into one event is left for Szakdolgozat II. |
| 2026-10-29 | Supervisor replied to the interim note ([feedback](supervisor-feedback.md#2026-10-29--reply-to-the-oct-28-interim-note)): on track for M1; M1 adds a comparison of two fixes for the reverse-order case on the development split; time handling (UTC instant, Europe/Budapest calendar day) approved for the ADR; M2 UI focus on token authentication and W3–W5, then W1, W6, W7; a versioned agent skill and the six design views added as actions. |
| 2026-11-07 | Author's decision: the HTTP layer moves to FastAPI now (ADR 0006 step 1), so the web app gets an OpenAPI schema and generated types; the storage switch to SQLAlchemy and PostgreSQL follows in M2, in the week of Nov 16–22. Request size limits were built into the new layer. The web UI is Hungarian only. |
| 2026-11-11 | Supervisor replied to the M1 e-mail ([feedback](supervisor-feedback.md#2026-11-11--reply-to-the-m1-e-mail)): M1 complete; matching engine frozen (no further complexity); M2 adds a hybrid categorizer with abstention and its coverage–accuracy measurement, ADR 0008 in code, SQLite and PostgreSQL both runnable, W2/W6/W7/W8 and W4 decision history, one agent skill and the six design views. |
| 2026-11-12 | Author's decision: the agent skills (supervisor action D1) are built first, before the rest of the week's tasks, because they speed up the remaining work; five skills added in `.claude/skills/`. Web password sign-in followed the same day, then the Android forwarding, tested on the emulator with the new `android-emulator-e2e` skill. |
| 2026-11-12 | The week of Nov 9–15 finished on Nov 12, so work of the week of Nov 16–22 was brought forward: ADR 0008 in code (supervisor action B1) and, by the author's choice, the PostgreSQL switch first because it is the riskiest item (B2, done the same day). A sixth skill, documentation and code comments, at the author's request. |
| 2026-11-12 | Author's decision: members have an e-mail address for signing in to the web app (needed later for forgotten-password e-mails), and the same field also accepts the member id ([ADR 0010](../architecture/decisions/0010-web-sign-in.md)). |
| 2026-11-16 | Supervisor replied to the weekly report ([feedback](supervisor-feedback.md#2026-11-16--reply-to-the-weekly-report-of-nov-915)): ADR 0010 accepted; matching engine stays frozen; W2 totals on deduplicated events without transfers within the group and with review items flagged; W8 merchant → category rules as the hybrid categorizer's first layer; hybrid categorizer measured Nov 23–27; real-device Android test before M2; 1–2 skills presented in depth in the methods chapter; the Hungarian manuscript skeleton (chapters 1–3) started in December instead of Szakdolgozat II. |
| 2026-11-19 | Author's decisions on the open questions of W2 and W8: basic role-based permissions now, with `admin` and `member` roles (only an admin changes group settings; existing members became admins); one category list, the dataset's nine categories (`housing` renamed to `housing_utilities`); the members list only shows members, inviting and removing stay on the command line; tokens are managed only from a web session and each member sees only their own; merchant rules apply to new records only; the `transfer` direction with the own-accounts list brought forward from Nov 23–27. Chosen from the options offered, except the roles, which the author asked for. |
| 2026-11-19 | The week of Nov 16–22 finished on Nov 19, so by the author's choice work of Nov 23–27 was brought forward: the deterministic layer of the hybrid categorizer (group rules, then a built-in Hungarian merchant and keyword dictionary; the LLM layer and the measurement stay on Nov 23–27) and drafts of design views 1–2. |
| 2026-11-19 | Author's decisions on the LLM layer: Anthropic `claude-haiku-5-5`, five samples per record as the confidence, the threshold rule (highest dev coverage with at most 5 % wrong settled answers), USD 2 for the measurement (ADR 0011 accepted); the API key follows in the week of Nov 23, so the LLM layer and the measurement runner were built early on Nov 19 and the paid run stays on Nov 23–27. The author proposed that members can set uncertain categories before the LLM runs and that admins choose when it runs (never, X hours after the purchase, daily or weekly); scheduled with the category correction. A self-hosted model (LM Studio) may be tried later; the layer already supports it. |
| 2026-11-19 | Future-work options added (not committed): e-mail confirmation and forgotten password, step-up re-authentication and a sign-in attempt limit, budgets and alerts, a self-hosted LLM, MFA, export, an "ask about your data" adviser, open banking. The author's ideas, grouped and refined by Claude; the author asked to record them. |
| 2026-11-21 | Real-phone test of the Android forwarding done (supervisor action, Nov 16): made-up cases and one real OTP Bank card purchase passed; found that **Send now** could not shorten a long retry delay, fixed the same evening ( [results](../design/android-notification-spike.md#2026-11-2021-m2-forwarding-on-the-real-phone)). |
| 2026-11-23 | Supervisor replied to the weekly report ([feedback](supervisor-feedback.md#2026-11-23--reply-to-the-weekly-report-of-nov-1622)): ADR 0012 accepted, with a least-privilege rule (every action that widens access, including role changes, only from a web session; built the same day); a local OpenAI-compatible model compared with the paid baseline afterwards (December if time allows, else Szakdolgozat II.); UX principles for the category correction (source and uncertainty visible, few clicks, merchant memory only for non-mixed merchants); the Android A1/A2 split stays below the measurement, the category correction and the demo for M2; views 5 and 6 show the outbound model call once wired in. |
| 2026-11-23 | Author's decision: the M2 closing package is finished and sent to the supervisor on Nov 27, so his feedback arrives before the Dec 4 close; Nov 28 – Dec 2 is buffer for the feedback, Dec 3 freeze. Day-by-day plan and cut order in the [M2 closing schedule](m2-closing-schedule.md). |
| 2026-11-24 | Paid hybrid categorizer measurement run ([report](../evaluation/results/2026-11-24-categorization-hybrid.md)): threshold 0.40 chosen on dev, on test 79.8 % coverage with 93.7 % accuracy of settled answers, USD 0.034. The cloud key is read from `FINSYNC_ANTHROPIC_API_KEY`. Wiring the LLM into the core stays in this week. |
| 2026-11-24 | Category correction (API and web) and the LLM in the live flow done in the same session as planned for Tue–Wed, because Tuesday finished early (author's rule: work moves on to the next day's items). Defaults taken where the design left the behaviour open, recorded in the [categorization design](../design/categorization.md) for the author to confirm or change: any member may create or confirm a merchant rule through a correction but only an admin changes one; lines that no longer add up after a split are ignored by the overview and flagged; saving the LLM setting schedules the group's existing uncertain events too; changing the LLM setting is web-session only. |
| 2026-11-24 | Thursday's items (W8 LLM setting, ADR 0013, ADR 0011 update, design views, demo seed and guide) done on Nov 24 in a third session at the author's request ("Folytassuk a csütörtöki feladatokkal"). Friday's package stays on Nov 27; Nov 25–26 are free for the author's demo dry run, the skill choice and reading the measurement report. |
| 2026-11-24 | Demo run on the Android emulator on the author's computer (all steps as in the guide). Author's decision on the finding: income is never an uncertain category (chosen from the options offered). |
| 2026-11-24 | The author tried the demo, read the measurement report, accepted ADR 0013 and confirmed the five defaults of the category correction and the LLM flow (rules created or confirmed by any member, changed only by an admin; lines that no longer add up ignored and flagged; saving the LLM setting schedules the backlog; *after arrival* counts from the record's arrival; the category panel on W4). Open: the skill choice for the methods chapter. |
