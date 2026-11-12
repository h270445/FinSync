---
name: session-wrap-up
description: Use at the end of every FinSync working session, before the pull request. Logs the session time, ticks the roadmap, milestone and supervisor actions, records AI use and the author's decisions, runs the checks and opens the one pull request of the session.
---

# Session wrap-up

- Version: 1.1 (2026-11-12)
- Owner: Bence Varga
- Why it exists: every session ends with the same bookkeeping (time log, roadmap, milestone checklist, AI-usage log, one pull request). Done from memory, totals drifted and decisions were missed. This skill makes the closing steps the same every time and checks the arithmetic.

## Input

- The session's commits: `git log origin/main..HEAD --format='%ad %s' --date=iso-local` (convert to Hungarian time, Europe/Budapest).
- The session's project messages with their timestamps, and any figure the author gave for the session ("today I worked 90 minutes").
- The decisions the author stated in the session, in the author's own words.

## Output

1. Updated `docs/planning/time-log.md`, `docs/planning/roadmap.md`, the current milestone file in `docs/planning/milestones/`, `docs/planning/supervisor-feedback.md` (action boxes) and `docs/ai-usage.md`, as far as the session changed them.
2. One pull request for the whole session, from the session's branch to `main`.
3. A short report in the reply: the time-log row, what was ticked, the author decisions recorded, the gate results and the pull request link.

## Prohibitions

- Never invent a time. If the start of the session is not visible (only commits), estimate from the previous merge or the first message and write "start time estimated ...; to be corrected by the author" in the Source column, as the existing rows do.
- Never record a decision the author did not state. Suggestions the author accepted without comment are not author decisions; options the author chose from a list are, with "Chosen from the options offered" as the reason.
- Never tick a box whose criterion is only partly met. Write what is done in brackets after it instead, with the date.
- Never put the supervisor's letters, e-mail addresses or any other person's personal data in the repository. Supervisor letters live in the project files (`supervisor/`), only the English summary goes in `supervisor-feedback.md`.
- Never edit files in `docs/releases/status-emails/` unless the session was about a status e-mail; they are Hungarian and are what was actually sent.
- Never open a second pull request in the same session, never merge it, and never request reviews (author's rule). Never push to `main`.
- Never put a model name or model identifier in commit messages, the pull request or the docs; "Claude Code" is the tool name to use.

## Steps

### 1. Time log

The rule is in the header of `time-log.md`: work is done together with Claude, sessions run from the first to the last activity (project messages and commits), gaps over 10 minutes are excluded, and a figure the author states replaces the estimate. Parallel sessions that overlap are counted once (say which minutes in the Work column).

1. Add one row per day: `| date | start–end (Hungarian time, several ranges comma-separated) | minutes | work in one line | source |`. Source is "Project messages and commits", "Commits" or "Author".
2. Update the week's row in "Weekly totals" (weeks start on Monday; add a row for a new week) and the **Total** row.
3. Run the checker. It must print `OK`; fix the table until it does.

   ```bash
   python .claude/skills/session-wrap-up/check_time_log.py
   ```

### 2. Plan and milestone

- `roadmap.md`: tick or annotate the week's lines with the date; add a change-log row for every plan change and every author decision that changes the plan; update "Last updated".
- Current milestone file: tick acceptance criteria and checklist lines only when fully met (see prohibitions).
- `supervisor-feedback.md`: tick an action only when it is done, with a link to where it is.

### 3. AI usage

- `docs/ai-usage.md` → Log: one row per significant AI-produced result of the session (tool, what it produced, how it was checked with test counts, PR or "session PR").
- → Author decisions: one row per decision from the input, with the AI suggestion it concerned and the author's reason.
- → Skill usage: if a skill under `.claude/skills/` was used, one row: skill and version, what it sped up, where it failed or missed something, and the change made to the skill (bump its version and change log when the skill file changes). This feeds the methods chapter (supervisor, 2026-11-11, D1).

### 4. Gates

Run every gate and copy the result lines into the report. A gate that cannot run is reported as not run.

```bash
python -m unittest discover -s tests                    # all OK
python .claude/skills/session-wrap-up/check_time_log.py   # OK
python .claude/skills/docs-and-comments/check_docs.py     # OK (links, folder READMEs, module docstrings)
cd web && npm run lint && npm test && npm run build      # only if web/ changed in the session
git status --short                                       # nothing left uncommitted that belongs to the session
```

Then search the session's diff for things that must not be in the repository: e-mail addresses, real-looking account numbers or names, tokens (`fs_` followed by a long string outside tests), and model identifiers.

```bash
git diff origin/main...HEAD | grep -nE '^\+.*([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}|fs_[A-Za-z0-9_-]{30,}|claude-(opus|sonnet|haiku|fable)|[0-9]{8}-[0-9]{8})' || echo "clean"
```

A hit is checked by hand; synthetic test tokens and `noreply@anthropic.com` in a `Co-Authored-By` trailer are expected.

### 5. Pull request

- Commit with plain English messages that say what changed and why; end each with the attribution trailer the session's instructions give.
- Push the session's branch and open **one** pull request to `main`. Title: what the session delivered, in a few words. The body starts with the attribution lines the session's instructions give (copied exactly, never invented), then: summary of the changes, how it was checked (gate results), what the author should look at, and that the content was produced with Claude Code (AI-usage rule).
- Assign the author (`h270445`). Do not request reviews.
- Watch the pull request's checks until they pass or report the failure.

## Human checkpoints

1. **Before** recording an author decision whose wording is not clear from the session: ask the author to confirm the wording, or leave the row out and say so in the report.
2. **Before** writing an estimated start time: none needed, but the report says that it is estimated so the author can correct it.
3. **After**: the author reads and merges the pull request. Nothing is merged by the agent.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-12 | First version, from the closing steps of the sessions between 2026-10-17 and 2026-11-12, with a checker for the weekly totals. |
| 1.1 | 2026-11-12 | The documentation checker of the docs-and-comments skill joins the self-check. |
