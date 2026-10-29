# Supervisor feedback

Summary of each letter from the thesis supervisor (Dr. Bilicki Vilmos) and what it changed. The letters themselves are not stored in the repository, because they contain another person's correspondence and e-mail addresses; the author keeps them in the project's shared files and in the mailbox. Outgoing e-mails are in [releases/status-emails/](../releases/status-emails/README.md).

Each entry lists the points as actions; ticked actions link to where they were done.

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

- [ ] M1 (2026-11-06): the reverse-order case investigated with both directions compared on the development split, the time-zone ADR, and an updated evaluation summary ([M1](milestones/m1-2026-11-06-working-core.md)).
- [ ] M2 (2026-12-04): token authentication and web screens W3, W4, W5, then W1, W6, W7 ([user interface](../design/user-interface.md)).
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
