---
name: docs-and-comments
description: Use when writing or changing FinSync code or docs, and before a session's pull request, to keep code comments, module docstrings, READMEs, ADRs and the thesis map in a state that a newcomer, the supervisor or the defence committee can understand quickly. Includes a link and docstring checker.
---

# Documentation and code comments

- Version: 1.0 (2026-11-12)
- Owner: Bence Varga
- Why it exists: the thesis, the report and the defence in Szakdolgozat II. are written from what is in the repository now: why something was built this way, what was decided and what was measured. Without a fixed habit, that knowledge ends up in chat history and commit messages, the docs drift from the code (on 2026-11-12 the project overview still listed review, measurement, authentication, the web app and Android as "planned", all built by then) and comments explain what the code does instead of why. The author asked for this skill on 2026-11-12.

## Input

- The change at hand (the diff, or the files about to be written), or a request to review the documentation.

## Output

1. Comments, docstrings and docs updated in the same change as the code, never in a later "docs" session.
2. `python .claude/skills/docs-and-comments/check_docs.py` prints OK.
3. When the change adds a decision, a measurement, a limitation or an answer to a likely defence question: a link in [docs/thesis-map.md](../../../docs/thesis-map.md).
4. In the report: which docs were touched and why, and anything left stale on purpose.

## Prohibitions

- No comment that repeats the code (`# increment the counter`). A comment says **why**: the reason, the invariant it protects, the rule or ADR it follows, or the trap it avoids.
- No outdated comment left in place. When the code changes, the comment changes or goes; never append "(update: ...)".
- No history in comments ("changed on Nov 3 because..."). History goes into the commit message, the ADR or the change log of the document.
- No long design text in code. More than about five lines of explanation belongs in a design doc or ADR, and the code links it in one line (`# Budapest wall-clock time, ADR 0008.`).
- No Hungarian in code, comments or repo docs, except the files that are Hungarian by rule (status e-mails, the web UI strings). No English UI text.
- No real personal or financial data in examples, docstrings or docs; the synthetic members and shops only.
- Never edit an accepted ADR's decision. Add a dated implementation note under its consequences or follow-up, or supersede it with a new ADR.
- Never describe planned work as done. Status words are the ones in [docs/README.md](../../../docs/README.md#conventions): implemented, in progress, planned, proposed.

## Rules

### Code

- **Every module starts with a docstring**: one line saying what the module is for, then, if needed, its main rule and a link to the design or ADR. The checker enforces this for `finsync/`.
- **Public classes and functions** get a docstring when the name and type hints do not already say everything: units, time zones, what `None` means, what is raised, and why a non-obvious choice was made.
- **Constants that came from a measurement or a decision** carry a short comment with where they came from (`AUTO_LINK_THRESHOLD` → the result file that chose it).
- **Tests** are named as sentences (`test_a_retry_is_a_re_delivery`) and comment the scenario only when the data does not make it clear; made-up texts say which real shape they follow.
- Kotlin and TypeScript follow the same rules (KDoc or TSDoc for the file's purpose, comments for why).

### Docs

Which document changes with which kind of change:

| Change | Document |
| --- | --- |
| API route or response | [docs/guides/api.md](../../../docs/guides/api.md) (see the endpoint-and-screen-checklist skill) |
| Decision with alternatives (technology, security, data model) | A new ADR in [docs/architecture/decisions/](../../../docs/architecture/decisions/README.md), status Proposed until the author accepts it, and its row in the index |
| Author's decision without an ADR | The "Author decisions" table in [docs/ai-usage.md](../../../docs/ai-usage.md#author-decisions) and the roadmap change log |
| Measurement | A result file in [docs/evaluation/results/](../../../docs/evaluation/README.md) with a "Findings" section and its row in the evaluation README |
| What a package does or its rules | That package's `README.md` |
| Something built or no longer planned | The status lines in [docs/overview.md](../../../docs/overview.md#current-implementation-status) and the design doc's status |
| Setup or a command | [docs/guides/getting-started.md](../../../docs/guides/getting-started.md) or the client README |
| New Markdown file or folder | The README of its folder (the checker finds a missing link) |

A package README answers, in this order: what the package is for, how it works in a few paragraphs (enough to read the code with), its rules, and where its design lives. Diagrams are Mermaid inside Markdown ([docs/README.md](../../../docs/README.md#conventions)), so the six design views the supervisor asked for (action D2) stay diffable.

### Thesis material

[docs/thesis-map.md](../../../docs/thesis-map.md) maps the thesis chapters and the likely defence questions to evidence in the repository. It links; it never copies numbers, so it cannot go stale on its own. Add a row or a link when a session produces: an ADR, a result file, an author's decision, a known limitation, or an answer to a question the committee could ask. A question whose evidence is still missing is marked *open*, which also shows what the remaining work must deliver.

## Steps

1. While coding: write the module docstring and the why-comments together with the code, not afterwards.
2. Before committing: go through the table under "Docs" against the diff and update every document a row names.
3. Run the checker and fix what it lists:

   ```bash
   python .claude/skills/docs-and-comments/check_docs.py
   ```

4. Read the diff once more for the prohibitions: comments that repeat code, comments that no longer match, planned work called done.
5. Update the thesis map if the change produced material for it.

## Self-check

- The checker prints OK (it checks relative links and their `#anchors`, folder READMEs listing their files, and module docstrings under `finsync/`). A run that was not done is reported as not run.
- The checker cannot see whether a sentence is still true. For each document touched, read the paragraph around the change; for the overview, compare its "Implemented" list with the M2 checklist.

## Human checkpoints

1. **Before** a new ADR or a change to an ADR's status: the author decides; the agent writes it as Proposed.
2. **After**: the author reads the thesis map now and then and adds the chapter outline the department expects once it is known; the current outline is a working one.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-12 | First version, at the author's request. First use: the checker found nine modules without a docstring, and an unlisted design document; the overview's status list was rewritten (it still called built features planned); the thesis map was started. |
