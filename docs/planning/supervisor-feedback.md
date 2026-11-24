# Supervisor feedback

Summary of each letter from the thesis supervisor (Dr. Bilicki Vilmos) and what it changed. The letters themselves are not stored in the repository, because they contain another person's correspondence and e-mail addresses; the author keeps them in the project's shared files and in the mailbox. Outgoing e-mails are in [releases/status-emails/](../releases/status-emails/README.md).

Each entry lists the points as actions; ticked actions link to where they were done.

## 2026-11-23 — Reply to the weekly report of Nov 16–22

**Assessment**

- The supervisor reviewed `main` at `19f25c17`: W2, W8, the hybrid categorizer's structure and run plan, the real-phone Android test, ADRs 0011 and 0012, and design views 1–2. The supervisor singled out the privacy discipline of the real-device test, the quick fix of the background retry issue found on the phone, and that the matching engine stayed untouched as agreed.
- The three layers of the hybrid categorizer (group rules → Hungarian dictionary → LLM layer behind an interface), the five-sample self-consistency uncertainty, the strict dev/test split and the data minimization are judged very clean. The planned live wiring (asynchronous, off by default for privacy, with a cost cap and the manual decision always winning) is supported, because the model stays a support and not a black-box override.
- With W2 and W8 all eight planned web screens exist; W2 saying openly how much is still waiting for review is judged a particularly good UX choice.
- Views 1–2 are clear and consistent. Choosing the skill(s) after next week's measurement and starting the Hungarian manuscript skeleton (chapters 1–3) in December fit the schedule.
- Next report: the hybrid categorizer's measurement results and the preparation of the Dec 4 package.

**Decisions**

- **ADR 0012 accepted:** for a spending tracker without money movement or bank credentials, full TOTP/WebAuthn MFA would be a disproportionate scope increase this semester; a failed sign-in limit and step-up re-authentication for sensitive actions are a proportionate, defensible answer. Status set to Accepted.
- **Least privilege added:** every admin action that widens access, not only issuing tokens but also changing a member's role, is allowed only from a web session, never with a long-lived phone API token, so the reach of a compromised phone token is closed at the architecture level.

**Actions**

- [x] **ADR 0012 to Accepted, with the least-privilege rule.** (Done 2026-11-23: [ADR 0012](../architecture/decisions/0012-no-multi-factor-authentication.md) point 6; `PUT /v1/members/{member_id}/role` now answers `403` to an API token, even an admin's, like `/v1/tokens`; tests in `tests/test_tokens_api.py`; [security and privacy](../architecture/security-and-privacy.md#current-state), [API guide](../guides/api.md#put-v1membersmember_idrole), view 6.)
- [ ] **Local model comparison after the paid baseline:** a small local OpenAI-compatible model on the same evaluation runner, for a privacy–accuracy–cost comparison; in the December refinement or at the start of Szakdolgozat II. (2026-11-23: planned in [ADR 0011](../architecture/decisions/0011-llm-categorization-layer.md#consequences) and the [roadmap](roadmap.md), Dec 7–13 if time allows.)
- [ ] **UX of the category correction, the "mixed" flag and category lines (week of Nov 23):** the member always sees the source and uncertainty of a suggestion, corrects or splits with few clicks, and the group's merchant memory learns a final rule only for non-mixed merchants. (2026-11-23: recorded as principles in the [categorization design](../design/categorization.md#review-in-the-web-app) and the M2 checklist.)
- [ ] **Android A1/A2 split later:** the setup/status split is the right direction for a later cleanup, but for Dec 4 the hybrid measurement, the category correction and the unified demo come first. (2026-11-23: noted in the roadmap, the M2 checklist and view 2.)
- [ ] **Views 5 and 6 in step with the LLM wiring:** once the LLM layer is in the live flow, view 5 (architecture) and view 6 (security) show the optional outbound model call's boundary and the data-minimization rule. (2026-11-23: noted as a to-do in [design-views.md](../architecture/design-views.md) and [security and privacy](../architecture/security-and-privacy.md#rules).)

## 2026-11-16 — Reply to the weekly report of Nov 9–15

**Assessment**

- The supervisor pulled `main` at `5a6208c`, ran the Python suite (178 tests) and the Vitest suite (33 tests), all passing, and tried the new screens live. The backbone of the requested M2 items is done, and the matching engine was left untouched as agreed.
- B1 (ADR 0008 in code, `device_zone` kept in the raw record but outside the fingerprint, dataset v3 reproducing the 2026-10-29 results), B2 (one storage layer for the fast SQLite profile and the PostgreSQL 16 profile, the concurrent-matching race guarded by a transactional lock and checked with a mutation test), W1 and C1/C2 (W4 decision timeline, W6, W7 with remembered column mapping, Hungarian row-level preview, whole-file rejection and identical rows sent to review) are judged sound.
- **ADR 0010 approved:** scrypt with a constant answer time, the `HttpOnly`, `SameSite=Strict` session cookie and the separate `X-CSRF-Token` header are a defensible choice over adding Argon2. Status set to Accepted.
- Why volume, UI and complexity are judged together: the reviewer and the final-exam committee look at the balance of the whole work, so algorithmic depth, functional completeness on screen and code/test/data volume must be in proportion.
  - Volume: outstanding, well above the first-semester expectation.
  - Algorithmic complexity: stable L3–L4, **no further increase; the matching engine stays frozen.**
  - UI: strong G3, 6 of the 8 main screens live. The one visible imbalance in the live test: the rule-based categorizer still puts most Hungarian merchants (SPAR, DM, MOL, MÁV-START) in "Egyéb". W2, W8 and the hybrid categorizer close this gap together.
- The proposed order and schedule to 2026-12-04 is fully supported; development and documentation/thesis writing continue in parallel.

**Actions (M2, 2026-12-04)**

- [x] **W2 overview:** monthly, per-category and per-member totals built on **deduplicated events**, with **transfers within the group excluded** and **items waiting for review clearly flagged**, so the total spending is not distorted. (Refines C3 of 2026-11-11.) (Done 2026-11-19: [`GET /v1/overview`](../guides/api.md#get-v1overview) and the W2 screen.)
- [x] **W8 settings:** group members and Android API tokens (create, revoke), plus **group-level merchant → category rules** that also serve as the **first, deterministic layer of the hybrid categorizer**. (Refines C4 of 2026-11-11.) (Done 2026-11-19: members with admin/member roles, own tokens from the web session, merchant rules and own accounts; [API](../guides/api.md#get-v1members).)
- [ ] **Hybrid categorizer measurement, Nov 23–27:** on the existing 200-item dataset and evaluation runner, measure the Hungarian merchant/keyword layer + model/LLM layer + explicit abstention threshold ("Bizonytalan" category) together: coverage–accuracy curve, latency and cost. (Action A of 2026-11-11.) (2026-11-19: LLM layer and measurement runner built, [ADR 0011](../architecture/decisions/0011-llm-categorization-layer.md), [runbook](../evaluation/hybrid-measurement-runbook.md); the paid run waits for the API key.)
- [x] **Real-device Android test before M2:** repeat the OTP forwarding test, so far verified on the emulator, on the physical phone. (Done 2026-11-20–21: the emulator cases and one real OTP Bank card purchase, [results](../design/android-notification-spike.md#2026-11-2021-m2-forwarding-on-the-real-phone).)
- [ ] **D1, skills in the methods chapter:** do not list all seven skills equally; present 1 (at most 2) in depth, where real use led to a 1.0 → 1.1 refinement. Suggested: `endpoint-and-screen-checklist` (the Pydantic/OpenAPI mismatch and the sign-in endpoint lesson) and `dev-test-evaluation` (with next week's categorization measurement). (2026-11-24: the author chose these two; endpoint-and-screen-checklist is at 1.2 and dev-test-evaluation at 1.1 after real use; they are presented in chapter 9 of the manuscript, [thesis-manuscript skill](../../.claude/skills/thesis-manuscript/SKILL.md).)
- [ ] **D2, design views:** views 3–6 are judged accurate and consistent with the code; finalising views 1–2 (use case, W1–W8 and A1–A2 page flow) at the end of November, after W2 and W8, is agreed. The thesis map's defence question–evidence table was singled out as the right way to prepare the argument from the codebase. (2026-11-19: views 1–2 drafted from the built W1–W8 screens with admin/member roles, [design-views.md](../architecture/design-views.md#1-use-cases).)
- [ ] **Hungarian manuscript:** the English `docs/` are a good supporting package for the electronic appendix, but start shaping the skeleton of chapters 1–3 of the Hungarian thesis manuscript (SZTE format) towards the end of the semester instead of leaving it entirely to Szakdolgozat II.

## 2026-11-11 — Reply to the M1 e-mail

**Assessment**

- The supervisor reviewed tag `v0.2.0` (`4f545c2`), `main` up to `37c4b8d` and the unmerged `971b418` (categorization evaluation runner). M1 is complete, one week before the deadline.
- The single ingest pipeline, atomic bulk import and the order-independent gate (`STRICT_POOR_GATE` plus `REOPEN_CONTESTED`: 0 false merges in both arrival orders on the test split at 0.95, 64.3% automatic recall, the remaining Decathlon edge case documented) are judged sound and defensible.
- Volume (backend, 100 unit tests, Android client, web app, 9 ADRs, reports) exceeds the first-semester expectation. Algorithmic depth is L3–L4: **do not make the matching engine more complex.**
- The UI moved from G2 to G3 with W1, W3, W4 and W5 (score breakdown, contested-link guard, identical-manual-entry warning, undo). For the application to be a "whole", the placeholder screens must be completed in M2/M3.
- The categorization baseline is the next research question: keyword rules reach 13.9% (dev) / 13.1% (test); even a perfect merchant dictionary is capped at 48.3% / 47.6% by mixed merchants.

**Actions (M2, 2026-12-04)**

- [ ] **A. Hybrid categorizer with abstention.** On top of `finsync/evaluation/categories.py`: a deterministic Hungarian merchant and keyword layer for clear cases, and a model/LLM layer that sees merchant, description, amount and context for mixed merchants. An explicit abstention threshold ("Bizonytalan kategória"); on the 200-item dataset measure coverage vs. accuracy, latency and cost. (Measured 2026-11-24, [report](../evaluation/results/2026-11-24-categorization-hybrid.md); the LLM is not yet wired into the core.)
- [x] **B1. ADR 0008 in code:** separate `posted_at` and `ingested_at`; Europe/Budapest calendar-day comparison; offset-less times as Budapest wall-clock time. (Done 2026-11-12: `posted_at` from the phone, arrival time in `created_at`, `finsync/ingestion/local_time.py`, matching dataset v3 reproduces the 2026-10-29 results.)
- [x] **B2. PostgreSQL behind `FinSyncStorage`:** SQLite stays runnable for fast local/CI tests (the unit suite keeps running in seconds), PostgreSQL is the production/integration profile. (Done 2026-11-12: SQLAlchemy Core and Alembic, `tests/run_on_postgres.py`, Docker Compose; the SQLite suite runs in about 9 s.)
- [x] **C1. Decision history in W4:** the API returns the event's `match_decisions` (when and with what score `auto_linked`, who confirmed, rejected or split). Done in PR #25: `GET /v1/events/{event_id}/decisions` and the timeline on the event detail page ([API](../guides/api.md)).
- [x] **C2. W6 manual entry and W7 bulk import preview** wired to `POST /v1/transactions` and `POST /v1/transactions/bulk`. (Done: W7 on 2026-11-12 on `POST /v1/imports`, the file import route; W6 on 2026-11-14 on `POST /v1/transactions`.)
- [x] **C3. W2 overview:** monthly and per-category group totals with the split by member. (2026-11-16: refined, see the [Nov 16 entry](#2026-11-16--reply-to-the-weekly-report-of-nov-915).)
- [x] **C4. W8 settings / backoffice:** group and members, create and revoke API tokens without the CLI (for the Android client), override merchant–category rules. (2026-11-16: the rules are also the hybrid categorizer's first layer, see the [Nov 16 entry](#2026-11-16--reply-to-the-weekly-report-of-nov-915).)
- [ ] **D1. One versioned agent skill** in the repository (for example the leak-free dev/test evaluation protocol, or a group-isolation and OpenAPI-sync check for new endpoints), presented in the methods chapter. (2026-11-12: five versioned skills in [`.claude/skills/`](../../.claude/skills/README.md), with a usage log in [ai-usage.md](../ai-usage.md#skill-usage); the one presented in the thesis is chosen after it has been used; 2026-11-16: 1, at most 2, presented in depth, see the [Nov 16 entry](#2026-11-16--reply-to-the-weekly-report-of-nov-915).)
- [ ] **D2. Six design views in `docs/`:** use-case, page flow (W1–W8 and Android), ingest → normalise → match → store/review flowchart, event and decision state diagram (`auto_linked` / `needs_review` / `confirmed` / `rejected` / `split`), architecture, security (SHA-256 Bearer tokens and `group_id` isolation). (2026-11-14: views 3–6 drafted in [design-views.md](../architecture/design-views.md); all six finalised at the end of November; 2026-11-16: views 3–6 judged accurate, views 1–2 after W2 and W8; 2026-11-19: views 1–2 drafted.)

Open design questions on the PostgreSQL switch or the hybrid categorizer measurement can be sent to the supervisor at any time.

## 2026-10-29 — Reply to the Oct 28 interim note

**Assessment**

- The late interim note is fine. The supervisor reviewed commit `4f545c2` and the design, evaluation and AI-usage documents, and judged the work on track for M1 (2026-11-06, `v0.2.0`).
- Volume (code, tests, data, documentation) and algorithmic depth are both sufficient; the backend does not need to be made more complex.
- The user interface is the M2 focus: no web screen is implemented yet. For 2026-12-04, token authentication plus the core web screens W3 (event list with uncertain categories), W4 (event detail with sources, decision history and split) and W5 (review workbench with score components), with W1, W6 and W7 (sign-in, manual and file input preview). Over both semesters, 6–8 domain screen families.

**Decisions approved**

- SQLite kept until M1; the FastAPI/PostgreSQL switch after M1 is low risk, but keep it in a strict time box so it does not take time from authentication and W3–W5.
- Notification time: store the Android `post_time_ms` as a UTC instant and project it to the Europe/Budapest calendar day when comparing with date-only manual entries. Record it in the time-zone ADR.
- Marketing filtering by positive transaction patterns (allow-list), silence as a format-change signal, reading active notifications on reconnect, and on-phone masking.
- `transfer` direction excluded from M2 totals, linking both sides left for Szakdolgozat II.; the HTTPS tunnel started only temporarily and only after token authentication.

**Reverse-order limitation (IKEA case)**

Compare two directions on the development split:

1. A stricter gate for information-poor records: when one side is date-only or the merchant information is weak, require more for `auto_linked`, so the record goes to `needs_review` more easily.
2. Reopen a contested link: when a later candidate from the same channel scores higher than, or within the runner-up margin of, an automatic link that no person has confirmed, do not move the old record silently; open the event for review (`needs_review`) and log it in the decision log. Invariant: automation never overrides a decision a person confirmed or rejected.

Literature for the thesis: the three-zone decision model is a domain adaptation of Fellegi and Sunter, "A Theory for Record Linkage" (JASA, 1969); for incremental and order-dependent entity resolution, Christophides et al., https://arxiv.org/abs/1905.06397.

**Actions**

- [x] M1 (2026-11-06): the reverse-order case investigated with both directions compared on the development split, the time-zone ADR, and an updated evaluation summary ([M1](milestones/m1-2026-11-06-working-core.md), tag `v0.2.0` on 2026-11-02).
- [ ] M2 (2026-12-04): token authentication and web screens W3, W4, W5, then W1, W6, W7 ([user interface](../design/user-interface.md)). API tokens done on 2026-11-02 ([ADR 0009](../architecture/decisions/0009-api-tokens.md)); W3, W4, W5 on 2026-11-08; W1 with password sign-in on 2026-11-12 ([ADR 0010](../architecture/decisions/0010-web-sign-in.md)); W7 (file import) on 2026-11-12; W6 on 2026-11-14.
- [ ] Turn one recurring, discipline-heavy FinSync workflow into a versioned agent skill in the repository, with clear input, output, prohibitions and mandatory human checkpoints. Candidates: a bank-notification anonymiser and parser checker that guarantees no personal financial data reaches tests or docs, or an evaluation skill that enforces the dev/test split. Log what it sped up, where it failed and how it was refined, for the methods chapter.
- [ ] Keep documentation in step with development. By the end of Szakdolgozat I. the six design views form one coherent frame: use-case diagram, W1–W8 and A1–A2 page flow, matching and review flowchart, event and decision state diagram, layered architecture diagram, and a security diagram of token authentication and group isolation.

## 2026-10-16 — Reply to the M0 e-mail

**Decisions**

- The five committed capabilities and their verification are accepted as the Szakdolgozat I. commitment. README commitment, matching design, evaluation plan and schedule do not need to be redone.
- The milestones stay: 2026-11-06 working and first-measured matching core, 2026-12-04 integrated prototype, 2027-01-15 preliminary package, 2027-01-30 corrected final version. The one-week internal buffer is a planning tool, not a separate submission.
- The supervision continues on the shared-household scenario and source reconciliation; LLM categorization stays a separate, narrowly scoped result.

**Work organized around four results**

1. **Traceable purchase events.** Matching on the existing input paths; confirm, reject and split together with the detection rule, because a rule is only usable if its mistakes can be corrected. The member sees the shared event and its original sources, and totals follow a correction.
2. **Measurable benefit and limits.** First real result for 2026-11-06 on the same data against the store-every-row baseline. A wrongly merged separate purchase is a different kind of error and must be reported separately. Keep separate development and test examples. Categorization: same hand-labelled items for both methods; accuracy, typical errors, correction need, time and cost.
3. **A usable application.** The web app's main job is the event list, provenance and review. Group membership must be tied to an authenticated person; automated tests cover the whole flow and access to another group's data. One-bank Android input and export-file import are the right size; the Google Sheets script stays conditional. Repeated sending must not distort results.
4. **Technology and documentation follow the result.** Judge the FastAPI/PostgreSQL switch by whether it helps connect the existing logic, access control and storage; the 2026-11-06 core decides, with the SQLite fallback if the switch delays it. Carry over the fixes from the existing fix branches so fixed bugs do not return. Update the documentation with implemented decisions and results; keep own decisions and checks visible in the AI-usage log.

**Actions**

- [x] Hand-decided examples first, at least: repeated submission, reverse arrival order, date-only manual entry, two separate purchases with the same amount ([matching design](../design/transaction-matching.md#testing-and-evaluation)) (Oct 17).
- [x] M1 results: matching vs. naive baseline on the same data, false merges reported separately ([M1](milestones/m1-2026-11-06-working-core.md)) (Oct 18, [results](../evaluation/results/)).
- [ ] Totals follow confirm, reject and split (test and web app).
- [x] Carry over the fixes from PR #2 (whole-word categorization) and PR #3 (atomic bulk import, amount validation) (PR #7).
- [x] Interim note to the supervisor by 2026-10-22: state of matching, and whether the SQLite fallback was needed. Not an official deadline. Sent late, on 2026-10-28 ([e-mail](../releases/status-emails/2026-10-28-koztes-jelzes.md)).
- [x] Answer the supervisor's question: is this order realistic with Friday and Saturday as working days, and is any side track too much for the November core? Answered in the Oct 28 e-mail.
- Contact: progress e-mails with repository link and commit id, sent directly from Gmail.

## 2026-10-04 — Topic feedback (before M0)

Summarized in the [roadmap change log](roadmap.md#change-log) entry of 2026-10-09: matching as the core contribution, clearly separate implemented from planned work, a concrete user scenario with verification, reduced Android and spreadsheet scope, build on the existing backend, document AI use including the author's own decisions.
