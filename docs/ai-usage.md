# AI usage

The course requires documenting significant use of AI tools and how their results were checked. The author remains responsible for the correctness of generated code and text.

## Rules

- Every pull request that contains significant AI-generated code or text says so in its description.
- Generated code is merged only after the author has read it and the tests pass; behaviour-changing code gets new tests.
- Generated designs and documents are reviewed against the code before they are marked Accepted.
- No real personal or financial data is shared with AI tools.

## Log

| Date | Tool | What it produced | How it was checked | PR / commit |
| --- | --- | --- | --- | --- |
| 2026-10-01 | GitHub Copilot agent | Initial MVP backend flow | Unit tests; reviewed and merged by the author | #1 |
| 2026-10-09 | Claude Code | Matching and duplicate detection design (proposed) | Under review by the author | – |
| 2026-10-09 | Claude Code | Whole-word categorization fix | Unit tests; awaiting author review | #2 |
| 2026-10-09 | Claude Code | Atomic bulk import, amount validation | Unit and HTTP tests; awaiting author review | #3 |
| 2026-10-09 | Claude Code | Documentation structure, package layout, roadmap | Existing tests pass after the move; awaiting author review | this PR |
