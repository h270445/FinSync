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
| 2026-10-09 | Claude Code | Whole-word categorization fix | Unit tests; awaiting author review | #2 |
| 2026-10-09 | Claude Code | Atomic bulk import, amount validation | Unit and HTTP tests; awaiting author review | #3 |
| 2026-10-09 | Claude Code | Documentation structure, package layout, roadmap | Existing tests pass after the move; reviewed and merged by the author | #4 |
| 2026-10-09 | Claude Code | UI plan, Figma prompt plan, technology stack, ADR 0005 and 0006 (proposed) | Awaiting author review | this PR |

## Author decisions

Decisions made by the author, as opposed to suggested by an AI tool. Filled in by the author.

| Date | Decision | AI suggestion it concerned (if any) | Reason |
| --- | --- | --- | --- |
| 2026-10-09 | Web app before the Android app; React for the web app | UI plan (PR #5) | Easier testing; learning and portfolio |
| 2026-10-09 | Status e-mails kept in the repository in Hungarian | – | Backup and traceability of reports |
