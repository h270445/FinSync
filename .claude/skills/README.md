# Agent skills

Versioned instructions for the coding agent (Claude Code), one folder per skill with a `SKILL.md`. Claude Code loads a skill when its description fits the task, or when it is named (`/session-wrap-up`). They turn recurring, discipline-heavy FinSync workflows into fixed procedures with a clear input, output, prohibitions, self-checks and human checkpoints (supervisor's request, 2026-10-29 and 2026-11-11, action D1).

| Skill | Version | Use when | Helper |
| --- | --- | --- | --- |
| [endpoint-and-screen-checklist](endpoint-and-screen-checklist/SKILL.md) | 1.0 | Adding or changing an API route or a web screen | – |
| [session-wrap-up](session-wrap-up/SKILL.md) | 1.0 | Closing a working session: time log, plan, AI usage, one pull request | `check_time_log.py` |
| [dev-test-evaluation](dev-test-evaluation/SKILL.md) | 1.0 | Any measurement: tuning, comparing methods, LLM runs | – |
| [bank-notification-privacy](bank-notification-privacy/SKILL.md) | 1.0 | Real bank notification formats, parser patterns and fixtures | `mask_captures.py` |
| [supervisor-status-email](supervisor-status-email/SKILL.md) | 1.0 | Drafting a status e-mail to the supervisor | – |

## Rules

- A skill changes only through a pull request. Every change bumps its version (1.0 → 1.1 for a clarification or a new check, 2.0 when the procedure changes) and adds a row to its change log.
- Each use that taught something (time saved, a miss, a false alarm) is logged in [docs/ai-usage.md](../../docs/ai-usage.md#skill-usage), the evidence for the methods chapter.
- Skills never weaken the project's rules: synthetic data only, group isolation, the frozen matching engine, one pull request per session.
- Helper scripts use the Python standard library only and run from the repository root.
