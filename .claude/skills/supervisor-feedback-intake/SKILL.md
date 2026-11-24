---
name: supervisor-feedback-intake
description: Use when the thesis supervisor's reply to a FinSync status e-mail or milestone package arrives. Turns the letter into an English summary with assessment, decisions and actions in docs/planning/supervisor-feedback.md and carries every point into the plan, the milestone, the ADRs, the design docs and the thesis map, without storing the letter itself.
---

# Supervisor feedback intake

- Version: 1.0 (2026-11-24)
- Owner: Bence Varga
- Why it exists: the supervisor answers every weekly report and milestone package (2026-10-16, 10-29, 11-11, 11-16, 11-23, and from now on weekly). Each reply approves or rejects ADRs, reorders priorities and asks for new work, and each was processed by hand in a session of its own (PR #37, commit 4318f7e), touching 10–14 files. Nothing fixed the order of work, so a point could stay only in the summary and never reach the roadmap or the milestone. The [supervisor-status-email](../supervisor-status-email/SKILL.md) skill answers the open actions; [session-wrap-up](../session-wrap-up/SKILL.md) ticks them when done; this skill is the missing step in between, where the actions are written down and carried into the plan.

## Input

- The supervisor's letter: in the project's shared files (`supervisor/`) or pasted by the author. Its date and which e-mail it replies to (`docs/releases/status-emails/`).
- `docs/planning/supervisor-feedback.md` (the open actions of earlier replies), the roadmap, the current milestone file, the M2 closing schedule or the plan that is current, the ADR index and the [thesis map](../../../docs/thesis-map.md).

## Output

1. A new entry at the top of `docs/planning/supervisor-feedback.md`: `## YYYY-MM-DD — Reply to <the e-mail>`, then **Assessment**, **Decisions** (only if the letter decides something) and **Actions**, as the existing entries are written.
2. Every action carried to where the work is planned or done (step 3), and each earlier open action that the letter closes or changes, updated.
3. A short report in the reply, in Hungarian: the actions as a table (action, where it was carried, due date, author question if any), the decisions applied, and the questions for the author.

## Prohibitions

- **Never store the letter** or quote it at length: no copy, no screenshot, no e-mail address, no greeting or signature. The repository gets an English summary in the project's words; a short phrase may be quoted where the exact wording matters (for example a priority order), marked as the supervisor's.
- Never invent a decision or an action: an aside, a suggestion with "if time allows" or a question to the author is recorded as such, not as a requirement. If a point is unclear (what is asked, by when), ask the author (checkpoint 1) instead of guessing.
- Never tick an action in this step unless the letter itself closes it (for example "ADR 0012 accepted": the status change is done in this session and ticked with its link). Work the letter asks for is ticked later by [session-wrap-up](../session-wrap-up/SKILL.md), when it is done.
- Never change an ADR's status, the milestone dates or the scope beyond what the letter says. A letter that changes the scope or a deadline is applied only after the author confirms (checkpoint 2).
- Never edit a sent status e-mail. If the e-mail the letter answers is still `Státusz: vázlat`, ask the author for the sent text (the supervisor-status-email skill's checkpoint 2) and match the file to it in the same session.
- No code change in this step unless the letter asks for a small, clear one and the author agrees; larger work goes into the plan.

## Steps

1. **Read and split.** Read the whole letter once. Split it into points and label each: assessment (praise, a judgement, a review of a commit), decision (an ADR accepted or rejected, a scope or priority change), action (work asked for, with its due date or milestone), question to the author, or aside. Note which commit the supervisor reviewed, if the letter says so.
2. **Write the entry.** At the top of `supervisor-feedback.md`, newest first:
   - **Assessment:** what was reviewed (the commit, the screens, the tests run) and the judgements, in bullets.
   - **Decisions:** each in bold with its consequence ("**ADR 0012 accepted:** ... Status set to Accepted.").
   - **Actions:** one checkbox each, a bold short name, then what is asked, in the supervisor's order; add the reference when it refines an earlier action ("Refines C3 of 2026-11-11"). After each, in brackets with today's date, where it was carried: "(2026-11-23: planned in the roadmap, Nov 25; noted in the M2 checklist.)"
   - Earlier entries: an open action that this letter closes, changes or drops gets a dated note in brackets; never rewrite its text.
3. **Carry each point.** For each decision and action, update what it touches, as the earlier intakes did:

   | Point | Where it goes |
   | --- | --- |
   | ADR accepted, rejected or changed | the ADR's status and a consequence line; the index in `docs/architecture/decisions/README.md` |
   | New or reordered work | `docs/planning/roadmap.md` (the week's line and a change-log row "Supervisor replied ...") and the current plan (for example `m2-closing-schedule.md`) |
   | A milestone criterion added, changed or confirmed | the milestone file's acceptance criteria or checklist, with a dated note |
   | A design rule or UX principle | the design doc it concerns (`docs/design/...`) and the design views when it changes a view |
   | Security or privacy rule | `docs/architecture/security-and-privacy.md`, and the ADR it refines |
   | Something for the thesis (a chapter, a defence question, the skills of the methods chapter) | the [thesis map](../../../docs/thesis-map.md) |
   | A future-work idea | the roadmap's "Future work (options beyond the committed scope)" section, marked as the supervisor's |

4. **Check the open actions.** Read every unticked action of earlier entries: is each still in the plan with a date? An action without a place is either carried now or listed as a question for the author.
5. **Report and ask.** Give the author the action table and the questions; record the author's answers as author decisions in `docs/ai-usage.md` when the session is wrapped up.
6. **Wrap up** with the [session-wrap-up](../session-wrap-up/SKILL.md) skill: time log, AI-usage log (one row for the intake), one pull request. The pull request's title names the letter's date and its main decision.

## Self-check

- Every point of the letter appears in the entry, labelled, and every action has a dated "where it was carried" note.
- `git diff` touches the files the table names for each point, and no file the letter does not concern.
- No sentence of the letter is copied beyond a short marked phrase; no e-mail address or name other than the supervisor's (already in the file's header); the leak search of session-wrap-up finds nothing.
- `python .claude/skills/docs-and-comments/check_docs.py` prints `OK` (the new links resolve).

## Human checkpoints

1. **Before** writing an action whose meaning or due date is unclear: ask the author, quoting the point in a few words.
2. **Before** applying a change of scope, of a milestone date or of a priority that moves planned work: the author confirms, and the confirmation is recorded as an author decision.
3. **After**: the author reads the entry before the pull request is merged; the next status e-mail answers each open action (supervisor-status-email skill, step 1).

## Change log

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-24 | First version, from the intakes of the replies of 2026-11-16 (commit 4318f7e) and 2026-11-23 (PR #37) and the entry format of `supervisor-feedback.md`. |
