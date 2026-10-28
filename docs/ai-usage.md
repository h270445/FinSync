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
