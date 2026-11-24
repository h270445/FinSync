---
name: supervisor-feedback-intake
description: Use when a reply from the thesis supervisor arrives (pasted or saved in the project files), to store it outside the repository, summarise it in English in docs/planning/supervisor-feedback.md as assessment, decisions and actions, and carry each action into the plan, the milestone, the ADRs and the thesis map.
---

# Supervisor feedback intake

- Version: 1.0 (2026-11-24)
- Owner: Bence Varga
- Why it exists: the supervisor answers every report, lately every week (2026-11-16, 2026-11-23). Each reply was processed the same way from memory: the letter kept out of the repository, an English summary with numbered actions, then the roadmap, milestone, designs, ADR statuses and thesis map updated. The [supervisor-status-email](../supervisor-status-email/SKILL.md) skill covers the outgoing side; this is the incoming side, so the loop report → reply → actions → evidence in the next report is fixed.

## Input

- The supervisor's reply as the author gives it (pasted text or a file). The author's own comments on it, if any.
- [supervisor-feedback.md](../../../docs/planning/supervisor-feedback.md) (format of the earlier entries), the [roadmap](../../../docs/planning/roadmap.md), the current milestone file, the ADR index and the [thesis map](../../../docs/thesis-map.md).

## Output

1. The letter word for word in the project files: `/mnt/project-files/supervisor/YYYY-MM-DD-<short title>.md`, with a row in that folder's README (Hungarian, as the folder's README says). **Not in the repository.**
2. A new entry at the top of `docs/planning/supervisor-feedback.md`: `## YYYY-MM-DD — <what it replies to>`, then **Assessment** (what was reviewed, at which commit, what was judged good or weak), **Decisions** (what the supervisor accepted or decided, for example an ADR accepted), **Actions** (one checkbox per point, bold short title, what is asked, and in brackets what was already done or planned and where).
3. Each action carried where it belongs: a roadmap line or change-log row, a milestone checklist line, an ADR status (with the date and "by the supervisor"), a design note, a thesis-map row. Each place links back to the entry's anchor.
4. A short report in the reply: the actions table (action, where it is planned or done, open or done), the decisions applied, and questions for the author.

## Prohibitions

- **Never put the letter, a quotation longer than a phrase, the supervisor's e-mail address or any other person's personal data in the repository.** The repository has only the English summary; the letter stays in the project files and the mailbox.
- Never invent a decision or an action the letter does not contain; a suggestion the supervisor makes is an action, not a decision. An unclear point is asked about, not interpreted.
- Never tick an action in this step unless it is already done with evidence; new actions start unticked. An action is ticked later, by the session that does it, with a link.
- Never change an ADR to Accepted unless the letter says so in so many words; write who accepted it and when.
- Never edit the status e-mails in `docs/releases/status-emails/`; they are what was sent.
- Never reorder or rewrite earlier entries; a correction to an earlier summary is a dated note under it.

## Steps

1. **Store the letter** in the project files and add its README row. Check that the repository diff does not contain it (`git diff | grep -c` for a distinctive Hungarian phrase gives 0).
2. **Read against the last report.** Open the status e-mail the reply answers and the open actions of the previous entry; note which of them the reply closes, keeps or changes.
3. **Write the entry** in English: assessment, decisions, actions. Name the commit the supervisor reviewed when the letter gives it.
4. **Carry the actions.** For each action, add or change the line in the roadmap (and a change-log row when it changes the plan), the milestone file, the design or ADR, and the thesis map; put the location in the action's brackets.
5. **Apply the decisions.** ADR status, design status ("approved by the supervisor on ..."), and a roadmap change-log row for each.
6. **Check.** `python .claude/skills/docs-and-comments/check_docs.py` prints OK (the new anchors resolve); the leak search of the session-wrap-up skill finds no e-mail address.

## Human checkpoints

1. **Before** writing a decision or an action whose meaning is not clear from the letter: ask the author.
2. **After**: the author reads the entry and the carried actions in the session's pull request before it is merged.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-24 | First version, from the processing of the replies of 2026-11-16 and 2026-11-23 (PRs of those days). |
