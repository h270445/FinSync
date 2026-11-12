# AI usage

The course requires documenting significant use of AI tools and how their results were checked. The author remains responsible for the correctness of generated code and text.

## Rules

- Every pull request that contains significant AI-generated code or text says so in its description.
- Generated code is merged only after the author has read it and the tests pass; behaviour-changing code gets new tests.
- Generated designs and documents are reviewed against the code before they are marked Accepted.
- No real personal or financial data is shared with AI tools.
- For each entry, note what the author corrected in the suggestion and which decisions the author made; the [decision notes](#author-decisions) collect the latter (supervisor request, 2026-10-09).
- AI-generated UI designs (Figma Make, First Draft) are logged with the prompt used ([figma-prompts.md](design/figma-prompts.md)) and reviewed against the [UI design](design/user-interface.md) before export; generated code is rewritten and reviewed before it enters `web/`.

## Log

| Date | Tool | What it produced | How it was checked | PR / commit |
| --- | --- | --- | --- | --- |
| 2026-10-01 | GitHub Copilot agent | Initial MVP backend flow | Unit tests; reviewed and merged by the author | #1 |
| 2026-10-09 | Claude Code | Matching and duplicate detection design (proposed) | Under review by the author | – |
| 2026-10-09 | Claude Code | Whole-word categorization fix | Unit tests; carried over to the current layout by Claude Code, tests re-run | #2, #7 |
| 2026-10-09 | Claude Code | Atomic bulk import, amount validation | Unit and HTTP tests; branch updated by GitHub Copilot, merged by Claude Code, tests re-run | #3, #7 |
| 2026-10-09 | Claude Code | Documentation structure, package layout, roadmap | Existing tests pass after the move; reviewed and merged by the author | #4 |
| 2026-10-09 | Claude Code | UI plan, Figma prompt plan, technology stack, ADR 0005 and 0006 (proposed) | Awaiting author review | this PR |
| 2026-10-17 | Claude Code | Duplicate kinds and sources; matching steps 1–5 on SQLite (rules, schema version 2, wiring, `GET /v1/events`); categorization design | 37 unit and service tests including the four hand-decided examples; reviewed and merged by the author | #7 |
| 2026-10-17 | Claude Code | Review endpoints: list, confirm, reject, split | 8 service, permission and HTTP tests (45 in total) | session PR |
| 2026-10-17 | Claude Code | Synthetic matching dataset generator and dataset v1 (100 records) | Reproducibility and ingest tests; scenario labels by construction | session PR |
| 2026-11-08 | Claude Code | Web app skeleton in `web/` (Vite, React, TypeScript, Tailwind, shadcn/ui), types generated from the OpenAPI schema; screens W3, W4, W5 and a development token sign-in | Type check, lint, 11 Vitest tests; run against the local API with synthetic data, screenshots at 1280 px and 360 px, confirm and undo tried in the browser | session PR |
| 2026-11-08 | Claude Code | Synthetic categorization dataset generator and dataset v1 (200 items, clear and ambiguous) | Reproducibility and label tests; labels by construction; merchant shares to be checked by the author | session PR |
| 2026-11-12 | Claude Code | Five versioned agent skills in `.claude/skills/` (endpoint and screen checklist, session wrap-up, dev/test evaluation protocol, bank notification privacy, supervisor status e-mail) with two helper scripts | Every command in the skills run once; the time-log checker run on the current log and on a deliberately wrong total; the masking script run on a made-up capture (no unmasked character left); the endpoint checklist compared with the files of PR #25 | session PR |
| 2026-11-12 | Claude Code | Web sign-in (W1): e-mail or member id and password, scrypt hashes, HttpOnly session cookie with a CSRF token, `python -m finsync.api.passwords`, ADR 0010 (proposed) | 23 new backend tests (121 in total) and 6 Vitest tests (20 in total); mutation checks (CSRF check, `SameSite`, token-over-cookie and the web CSRF header each removed once: tests fail); tried in a browser against the local API at 360 px and 1280 px (wrong password, sign-in by e-mail and by id, reload, sign-out, cookie not readable by scripts) | session PR |
| 2026-11-12 | Claude Code | Android forwarding (M2): OTP Bank allow-list, outbox with retry (WorkManager), sent-keys so a retry is never a second event, dropped-notification counter, status screen; server ingest takes `title`, `posted_at`, `source_ref` and parses the OTP format; the `android-emulator-e2e` skill | 14 new backend tests (135 in total) and Kotlin unit tests; two emulator runs through Remote Control on the author's computer with made-up notifications (purchase, transfer, marketing, reconnect, offline retry, status screen): the first found two bugs (status lines not refreshing, dropped notifications counted again on reconnect), the second passed every case with the fixes. Not yet tested on the real phone | session PR |
| 2026-11-12 | Claude Code | ADR 0008 in code: times without an offset read as Europe/Budapest, matching dataset v3 (v2 with local notification times) | 9 new tests (both summer-time changes, late evening, dates unchanged), a mutation check (the parser back on UTC fails a test); the evaluation on v3 reproduces every generated number of the 2026-10-29 result (diff), reported as a regression check | session PR |
| 2026-11-12 | Claude Code | docs-and-comments skill with `check_docs.py`, docstrings for nine modules, the project overview's status rewritten, `docs/thesis-map.md` | The checker run on the repository (and on a planted broken link and anchor); every claim in the new overview checked against the M2 checklist | session PR |
| 2026-11-12 | Claude Code | Storage on SQLAlchemy Core and Alembic (SQLite or PostgreSQL), PostgreSQL test runner, Docker Compose with `db` and `api` | The whole suite on SQLite (149 OK) and on PostgreSQL 16 (141 OK, 8 SQLite-only skipped); a schema test (a pre-Alembic file and a new one end with the same schema); a concurrency test whose mutation (advisory lock removed) fails 3 runs out of 3; `docker compose up` with a token, two notifications (the second an `exact_duplicate`) and a restart that kept the data | session PR |

## Author decisions

Decisions made by the author, as opposed to suggested by an AI tool. Filled in by the author.

| Date | Decision | AI suggestion it concerned (if any) | Reason |
| --- | --- | --- | --- |
| 2026-10-09 | Web app before the Android app; React for the web app | UI plan (PR #5) | Easier testing; learning and portfolio |
| 2026-10-09 | Status e-mails kept in the repository in Hungarian | – | Backup and traceability of reports |
| 2026-10-17 | Duplicate handling first, on the existing SQLite backend, before the stack switch | Weekly plan that started with the stack switch | The supervisor's letter names the working Nov 6 core as the priority |
| 2026-10-17 | Ask the member about uncertain categories on the phone, with the likeliest options and "Other"; no daily question limit by default, configurable in settings | Categorization design (uncertain category shown only as a suggestion) | Most accurate while the purchase is fresh; the member decides how often to be asked |
| 2026-10-17 | Mixed baskets: one category by default, a "mixed" flag and splitting an event into category lines, all this semester | Splitting proposed for the second semester | Building the data model once avoids reworking it in the second semester |
| 2026-10-18 | Fix the merchant comparison now, before M1: shared tokens over the shorter name (matcher `rules-2`) | Evaluation finding that bank names with a suffix halve the merchant score | Chosen from the options offered (fix now, later with dataset v2, or keep as a known limit) |
| 2026-10-24 | External clients (Sheets script, Android off the local network) reach the local API through an HTTPS tunnel, started only after token authentication exists ([ADR 0007](architecture/decisions/0007-how-external-clients-reach-the-api.md)) | ADR 0007 options: tunnel, hosted server, server pulling the sheet | Chosen from the options offered; no hosting cost, works for both clients |
| 2026-10-24 | Android spike: Samsung on the latest Android, OTP Bank and Revolut; captured notifications stay on the phone and only anonymised formats enter the repository; only the bank apps' notifications are read (package-name allowlist); spike code in `clients/android/` | Spike plan with six questions | Fewer personal data (GDPR) and less storage; the listener should handle only bank notifications |
| 2026-10-26 | Transfers within the group (for example family transfers in mobile banking) are booked as `transfer` using a per-group list of own accounts and counterparties, this semester (M2); linking both sides into one event left for Szakdolgozat II | Options: transfer type now, also link both sides, or out of scope | Transfers inflate the group totals today; small change that keeps time for the matching core |
| 2026-10-26 | Matching design and ADR 0004 accepted | Design status set to "Implemented on SQLite" after the evaluation | Implemented, tested scenario by scenario and measured on dataset v1 |
| 2026-10-27 | Android spike also watches K&H (`hu.kh.smartbanking`), found on the test phone | Package seen during the phone set-up | A third bank format at no extra cost |
| 2026-10-28 | Handle bank marketing notifications in this pull request (spike keeps non-transactions only masked; M2 rule proposed: forward only known bank patterns) | Proposal after the Revolut marketing notification | Asked for after the first real Revolut notification turned out to be marketing |
| 2026-10-29 | Reverse-order case: both fixes on (strict gate and contested-link reopening, `rules-3`) | Recommended A+B after the dev-split comparison on dataset v2 | Fewest false merges on dev, the evaluation plan's first criterion; B kept as the safety net for a merge the gate lets through |
| 2026-10-29 | Auto-link threshold 0.95 instead of 0.85 | Recommended following the plan's tie rule | 0.85–0.95 tie on dev with `rules-3`; the pre-set rule takes the higher threshold |
| 2026-10-29 | ADR 0008 accepted: notification time is `post_time_ms` in UTC, days compared in Europe/Budapest | Drafted ADR 0008 | Approved by the supervisor on 2026-10-29 |
| 2026-11-12 | Build the agent skills before the rest of the week's tasks: first the endpoint and screen checklist and the session wrap-up, the others if time allows before noon | Five skill candidates offered, with the endpoint checklist and wrap-up recommended | Done well, skills speed up the rest of the semester; chosen from the options offered |
| 2026-11-12 | PostgreSQL switch brought forward from the week of Nov 16–22 as the next task, with SQLAlchemy, Alembic and psycopg as new dependencies | Recommended: PostgreSQL first, because it is the riskiest item | – |
| 2026-11-12 | A skill for documentation and code comments that supports quick understanding and the Szakdolgozat II. thesis, report and defence | – (the author's own proposal) | The thesis is written from the repository, so the reasons and evidence must be findable there |
| 2026-11-12 | Web sign-in with an e-mail address, and the same field also accepts the member id | Recommended: member id and password only, no e-mail stored | Later features such as a forgotten-password e-mail need the address |

## Skill usage

One row per use of an [agent skill](../.claude/skills/README.md) that taught something: what it sped up, where it failed or missed something, and how the skill was refined. Evidence for the methods chapter (supervisor, 2026-11-11, action D1).

| Date | Skill (version) | Task | What it sped up or caught | Where it failed, and the refinement |
| --- | --- | --- | --- | --- |
| 2026-11-12 | endpoint-and-screen-checklist (1.0) | Retrospective check against PR #25 (W4 decision history) | Every file PR #25 changed is on the checklist; it would also have required a Vitest test for the timeline, which PR #25 lacks | Found while writing it: `web/openapi.json` differs when regenerated with another Pydantic version (a `pattern` on `Decimal \| str` fields); the checklist now says not to commit that drift |
| 2026-11-12 | session-wrap-up (1.0) | Closing this session | The checker confirmed all weekly totals; the wrap-up found that supervisor action C1 (done in PR #25) was not ticked | – |
| 2026-11-12 | endpoint-and-screen-checklist (1.0) | Web sign-in (W1): `/v1/session` routes and the sign-in page | Checkpoint 1 stopped the work for the author's decision on the sign-in name; the checklist led to the route list, the 400 case, the OpenAPI test, the API types and the docs in one pass | The checklist assumed every route takes a token; added a line for routes without one (sign-in). The Pydantic drift note was not actionable; it now says how to regenerate with the snapshot's version (2.11), which worked. Version 1.1 |
| 2026-11-12 | android-emulator-e2e (1.0) | Second emulator run of the Android forwarding | The run followed the written steps without questions and confirmed both fixes with evidence (API JSON, preferences, UI dump) | The emulator held the first run's notifications and app data; the F case did not really check the refresh; the counters were read from the screen; the screenshot through `adb exec-out` was broken in PowerShell 5.1; the run once piped `captures.jsonl` into a line counter (synthetic content, not displayed, but against the rule); the slow first run could not be explained afterwards because free memory was not measured. Version 1.1 fixes each of these |
| 2026-11-12 | docs-and-comments (1.0) | First run over the whole repository | The checker found nine `finsync/` modules without a docstring and a design document missing from its folder README; reading the overview against the M2 checklist found its status list months behind (review, measurement, authentication, web app and Android still "planned") | The checker cannot judge whether a sentence is still true; the skill makes that a reading step (overview against the M2 checklist) |
