# M2 closing schedule (Nov 23 – Dec 4, 2026)

- Written: 2026-11-23
- Owner: Bence Varga
- Milestone: [M2 — Integrated prototype](milestones/m2-2026-12-04-integrated-prototype.md), due 2026-12-04 23:59, tag `v0.3.0`

## Goal

The M2 closing package is complete on **Wednesday 2026-11-25** and goes to the supervisor that day, so his feedback arrives before the real close on Dec 4. Nov 26 – Dec 2 is kept for fixing what the feedback asks for, Dec 3 is the freeze, and Dec 4 only tags `main` and sends the final e-mail. (Planned for Fri Nov 27 at first; moved to Nov 25 by the author on 2026-11-24, because the work of Nov 24–26 was finished on Nov 24.)

The day plan follows the priorities in the [supervisor's reply of 2026-11-23](supervisor-feedback.md#2026-11-23--reply-to-the-weekly-report-of-nov-1622):

1. Hybrid categorizer measurement results.
2. Category correction, the "mixed" flag and category lines, with the [UX principles](../design/categorization.md#review-in-the-web-app) (source and uncertainty visible, few clicks, merchant memory only for non-mixed merchants).
3. One end-to-end demo.
4. All six design views final, views 5 and 6 with the optional outbound model call and its data-minimization rule.
5. ADR updates.
6. Lower priority: the Android A1/A2 split, the Google Sheets script.

The matching engine stays frozen (supervisor, 2026-11-11).

## Day by day

Each day is one working session with Claude and ends with one pull request. The dates are the latest dates: when a day finishes early, the next day's work starts at once (author, 2026-11-24), as the [roadmap's planning rules](roadmap.md#planning-rules) say. Steps marked **(author)** can only be done by Bence.

| Day | Work | Done when |
| --- | --- | --- |
| **Mon Nov 23** (evening) | Supervisor reply of Nov 23 processed (ADR 0012 accepted, role changes web-session only; PR #37). This schedule. **(author)** Put the API key into the cloud environment ([runbook step 1](../evaluation/hybrid-measurement-runbook.md#1-provide-the-key-author)) and confirm or change the [LLM scheduling proposal](../design/categorization.md#when-the-llm-is-called-proposed-by-the-author-2026-11-19), because Wednesday's wiring builds on it. (Both done on Nov 24: the key is set, under the name `FINSYNC_ANTHROPIC_API_KEY`, and the proposal was confirmed as written.) | PR #37 and this schedule merged; the key is set before Tuesday's session starts. |
| **Tue Nov 24** | **1. Measurement:** preflight, paid run (about USD 0.04, budget USD 2), reproducibility check from the cache, results file in `docs/evaluation/results/`, evaluation README row, thesis-map row ([runbook](../evaluation/hybrid-measurement-runbook.md)). **(author)** reads the report before it is quoted (checkpoint 3 of the dev-test-evaluation skill). **2. Category correction API:** change and confirm a category (stored as `user`, with source and uncertainty in the response), the "mixed" flag, category lines in `event_category_lines` (Alembic revision, lines add up to the amount, same sign, replaced as one logged change), mark or unmark a record as a transfer, overview totals follow the lines, a group rule only for non-mixed merchants; tests on SQLite and PostgreSQL, OpenAPI and web types. | Coverage–accuracy curve, latency and cost in a committed report from a clean tree; correction endpoints tested, cross-group tests included. **Done Nov 24** (measurement PR #39; correction API in the Nov 24 session PR). |
| **Wed Nov 25 → done Tue Nov 24** | **Category correction in the web app:** suggestion marker with source and uncertainty in Hungarian on the event list (W3) and detail (W5), one-tap confirm or change, "mixed" toggle, line editor pre-filled with the whole amount (last line takes the remainder), "always use this for …" only at non-mixed merchants, "uncertain categories" filter, browser check at 360 and 1280 px. **LLM in the live flow (API):** group setting (*never* by default), `llm_due_at`, in-process task for due events, "ask for a suggestion now", monthly cost cap per group, a member's decision never overwritten and skipped by a later run. | The correction works in the browser on synthetic data; the LLM path is tested with a fake provider (no paid calls in tests). **Done early on Nov 24** in the same session (detail screen is W4; one synthetic live call with the real key, USD 0.0005). |
| **Thu Nov 26 → done Tue Nov 24** | **LLM setting on W8** (admins only) and the cost-cap message. **ADRs:** ADR 0013 for the LLM in the live flow (off by default, manual first, cost cap, only description, merchant and amount leave the system); ADR 0011 updated with the measured result; ADR index. **Design views:** 5 and 6 show the optional outbound model call and the data-minimization rule; 1–4 checked against the code (category correction use case, W3/W5/W8 flows, event states). **Demo:** a seeded synthetic dataset and a step-by-step demo guide: a phone notification and the same purchase from a spreadsheet export become one event; two same-amount purchases on the same day stay two; an uncertain match reviewed and split; a category corrected, marked mixed and split into lines; the overview follows. **(author)** Dry run of the demo on the Windows computer with the Android emulator (android-emulator-e2e skill, Remote Control). **(author)** Choose the 1 (at most 2) skills for the methods chapter. | The demo runs from the guide without help; all six views and the ADRs match the code. **Done early on Nov 24** except the author's steps: W8 LLM setting, [ADR 0013](../architecture/decisions/0013-llm-in-the-live-flow.md), ADR 0011 with the measured result, views 1–6 checked and updated, demo seed (`python -m finsync.api.demo`) and [demo guide](../guides/demo.md). The demo ran on the emulator on the author's computer the same day and the author tried it. The author chose endpoint-and-screen-checklist and dev-test-evaluation for the methods chapter on Nov 24. Friday's package follows the [milestone-package](../../.claude/skills/milestone-package/SKILL.md) skill. |
| **Wed Nov 25** (package day, moved from Fri Nov 27) | **Package:** full test suite on SQLite and PostgreSQL, web build and tests, docs-and-comments checker; API reference, security status and getting-started guide updated; M2 acceptance criteria and checklist ticked with evidence; v0.3.0 release notes drafted (`docs/releases/v0.3.0.md`, tag not yet set); AI-usage log and time log. **Status e-mail** "M2 zárócsomag – előzetes" drafted with the supervisor-status-email skill, every claim checked against `main`. **(author)** Merges the PR and sends the e-mail the same day. | E-mail sent on Nov 25 with the commit id of `main`. |
| **Thu Nov 26 – Wed Dec 2** | **Buffer.** Supervisor feedback handled as it arrives, each fix recorded in the plan. Only if nothing is waiting: the Android A1 (setup) / A2 (status) split, then the Google Sheets script. | Every feedback item fixed or answered. |
| **Thu Dec 3** | Freeze: no new features; final test run on both databases; release notes final. | `main` is the M2 snapshot. |
| **Fri Dec 4** | Tag `v0.3.0` on `main`, M2 e-mail with the tag and commit id (deadline 23:59). | Tag pushed, e-mail sent. |

## If a day runs over

Work rolls forward to the next day; the package day (Nov 25) is not moved again. When something has to give, it is cut in this order (last cut first):

1. The Google Sheets script (optional since M0).
2. The Android A1/A2 split (supervisor: after M2 if needed).
3. LLM scheduling options beyond *never* and "ask for a suggestion now" (*X hours after*, *daily*, *weekly*) move to the buffer; the setting and the cost cap stay.
4. Demo on the emulator only, without the real phone.

Never cut: the measurement results, the category correction with the mixed flag and lines, the six design views.

## Risks

| Risk | Mitigation |
| --- | --- |
| The API key is not set by Tuesday | Everything else on Tuesday goes ahead; the run takes a few minutes and can happen any day up to Thursday. If there is still no key, the package reports the deterministic layer and the run moves to the buffer, said openly in the e-mail. |
| The category lines touch the overview totals and the matching split | Lines belong to the event, not to a source record ([design](../design/categorization.md#mixed-baskets)); a test for split-after-lines and for totals with and without lines. |
| The demo needs the Windows computer and the emulator | Dry run on Thursday, not Friday, so a failure leaves a day to fix it. |
| The supervisor's feedback arrives late | The buffer runs until Dec 2; anything that comes later is answered in the Dec 4 e-mail as a known limitation or a December item. |
