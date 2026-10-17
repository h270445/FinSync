# Supervisor feedback

Summary of each letter from the thesis supervisor (Dr. Bilicki Vilmos) and what it changed. The letters themselves are not stored in the repository, because they contain another person's correspondence and e-mail addresses; the author keeps them in the project's shared files and in the mailbox. Outgoing e-mails are in [releases/status-emails/](../releases/status-emails/README.md).

Each entry lists the points as actions; ticked actions link to where they were done.

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

- [ ] Hand-decided examples first, at least: repeated submission, reverse arrival order, date-only manual entry, two separate purchases with the same amount ([matching design](../design/transaction-matching.md#testing-and-evaluation)).
- [ ] M1 results: matching vs. naive baseline on the same data, false merges reported separately ([M1](milestones/m1-2026-11-06-working-core.md)).
- [ ] Totals follow confirm, reject and split (test and web app).
- [x] Carry over the fixes from PR #2 (whole-word categorization) and PR #3 (atomic bulk import, amount validation) (PR #7).
- [ ] Interim note to the supervisor by 2026-10-22: state of matching, and whether the SQLite fallback was needed. Not an official deadline.
- [ ] Answer the supervisor's question: is this order realistic with Friday and Saturday as working days, and is any side track too much for the November core?
- Contact: progress e-mails with repository link and commit id, sent directly from Gmail.

## 2026-10-04 — Topic feedback (before M0)

Summarized in the [roadmap change log](roadmap.md#change-log) entry of 2026-10-09: matching as the core contribution, clearly separate implemented from planned work, a concrete user scenario with verification, reduced Android and spreadsheet scope, build on the existing backend, document AI use including the author's own decisions.
