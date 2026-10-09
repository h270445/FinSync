# User interface

- Status: **Proposed** (not implemented)
- Date: 2026-10-09
- Decision record: [ADR 0005](../architecture/decisions/0005-web-client-first.md)
- Figma prompts: [figma-prompts.md](figma-prompts.md)
- Exported screens: [ui/](ui/README.md)

## Summary

FinSync has three clients with different jobs. Only one of them is a full user interface:

| Client | Job | Amount of UI |
| --- | --- | --- |
| **Web app** (desktop browser first, usable on a phone) | Everything a member looks at or decides: events, match review, corrections, manual entry, file import, tokens | Full UI, built first |
| **Android app** | Reads supported banking notifications in the background and sends them to the ingest endpoint | Two screens: setup and status |
| **Google Sheets script** | Sends new sheet rows to the bulk endpoint | No own UI; the sheet is the UI (a menu item at most) |

The web app is built first because the review and correction flow (roadmap item 2) needs a screen, it is the easiest client to test and demonstrate, and reviewers can open it without installing anything. Android is not a UI problem: its risk is notification access on a real device, which the October spike covers.

## Technology (proposed)

React with TypeScript (Vite), Tailwind CSS and shadcn/ui components in `web/`, calling the same `/v1` JSON API as the other clients; the Android app uses Kotlin and Jetpack Compose. Details and reasons: [technology stack](../architecture/technology-stack.md).

Consequence for design work: Figma Make also generates React with Tailwind, so its code can be a **starting point** for a component. It is never committed as generated: it is rewritten to use the project's components, the typed API client and TanStack Query, and reviewed like any other code.

## Screens

UI text is Hungarian, amounts in HUF (`12 990 Ft`), dates `2026. 10. 09.`. All example data is synthetic.

### Web app

| # | Screen | Purpose | API (current or planned) | Needed by |
| --- | --- | --- | --- | --- |
| W1 | Sign in | E-mail and password (session cookie); choose a group if the member belongs to several | Password login and session endpoints (planned, M2) | M2 |
| W2 | Overview | Month totals per category and per member; count of events waiting for review | `GET /v1/events` | M2 |
| W3 | Events | Deduplicated list: date, merchant, amount, category, source badges (notification, sheet, manual, file), review flag; filter by month, member, category, source | `GET /v1/events` | M1 side track (read-only) |
| W4 | Event detail | The records behind one event, raw payload, source reference, import batch, decision history; **Split** action; category correction | `GET /v1/events`, `POST /v1/events/{id}/split` | M2 |
| W5 | Review queue | Two records side by side, score and feature breakdown (amount, time, merchant), **Same purchase** / **Different purchases** | `GET /v1/matches/review`, `POST /v1/matches/{id}/confirm`, `.../reject` | M2 |
| W6 | Add transaction | Manual entry form; after saving, show the match outcome | `POST /v1/transactions` | M2 |
| W7 | Import file | Upload a spreadsheet export, preview rows, import, summary per outcome (new, linked, needs review, re-delivery, rejected rows with reasons) | `POST /v1/transactions/bulk` | M2 |
| W8 | Settings (if time allows) | Group members; create and revoke API tokens for the Android app and the Sheets script (token shown once) | Token endpoints (planned, M2) | M2 |

### Android app

| # | Screen | Purpose |
| --- | --- | --- |
| A1 | Setup | Server URL, API token, notification-access permission, supported bank apps |
| A2 | Status | Last notifications sent, waiting queue, errors, a test-send button |

## Design principles

- **Traceability is visible.** Every event shows which sources it came from; nothing is merged silently.
- **Uncertainty is explicit.** Events waiting for review are marked in every list and counted on the overview.
- **Every correction is reversible** and shows who did it and when.
- **Plain, accessible layout:** one accent colour, readable tables, keyboard-usable, WCAG AA contrast, works from 360 px width.
- **Data minimization:** the UI shows only the group's own data; raw payloads are behind an explicit "show raw" toggle.

## Design workflow

1. **Wireframes** (low fidelity, greyscale) for W3, W5 and A1 first: they carry the main risk and the demo.
2. **One styled key screen** (W5 review queue) to fix the visual language: colours, type, spacing, badges.
3. Remaining screens in the same style.
4. Review each screen against this document and the API; record the outcome in the [AI-usage log](../ai-usage.md).
5. Export approved frames to [ui/](ui/README.md) and link them from here.

Figma is the design tool (prompt-based generation with Figma Make or First Draft, then manual editing). Low-fidelity wireframes are enough for most screens; the thesis is judged on the working prototype, not on pixel-perfect mockups.

## Storing design output

| Output | Where | In git? |
| --- | --- | --- |
| Figma file (source of truth) | Figma cloud; link in [ui/README.md](ui/README.md) | Link only |
| Approved screen exports (PNG, 1x or 2x) | `docs/design/ui/` | Yes, small and referenced from docs and the thesis |
| Raw or work-in-progress exports | `docs/design/ui/exports/` (local only) | No; ignore rule pending |
| `.fig` backups | Outside the repository | No |
| Figma Make generated code | Copied into `web/` only after rewriting and review | Only the reviewed version |

Figma keeps the design in its cloud, so there is usually nothing local to ignore; teams commit only the curated images their docs reference and ignore bulk export folders. The `exports/` ignore rule is pending ([ui/README.md](ui/README.md)).

## Open questions

- Is Hungarian-only UI enough, or does the thesis demo need English labels too?
