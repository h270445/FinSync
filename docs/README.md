# FinSync documentation

Everything about FinSync beyond the code lives here. Documents describe the **actual implementation**; anything not built yet is marked *planned* or *proposed*.

## Map

| Folder / file | What it answers |
| --- | --- |
| [overview.md](overview.md) | What FinSync is, the thesis contribution, scope and current status |
| [guides/](guides/README.md) | How to install, run, test and call the system |
| [architecture/](architecture/README.md) | How the system is structured now and where it is heading; decision records |
| [design/](design/README.md) | Detailed designs for individual features (transaction matching first) |
| [evaluation/](evaluation/README.md) | How correctness and quality are measured, datasets and results |
| [planning/](planning/README.md) | Semester roadmap and milestone targets with deadlines |
| [releases/](releases/README.md) | Milestone release notes and the fix log for the final package |
| [ai-usage.md](ai-usage.md) | Where AI tools were used and how their output was checked |

## Conventions

- Language: English, except [releases/status-emails/](releases/status-emails/README.md), which keeps the Hungarian e-mails to the supervisor. File names: lowercase, hyphen-separated.
- Every folder has a `README.md` that lists its contents.
- Status words: **implemented** (in `main` and tested), **in progress**, **planned**, **proposed** (design not yet agreed).
- When code changes behaviour, the matching document changes in the same pull request.
- Architecture decisions are recorded as ADRs in [architecture/decisions/](architecture/decisions/README.md); a decision is never edited after acceptance, only superseded.
- Diagrams are plain text or Mermaid inside Markdown, so they diff and render on GitHub.
