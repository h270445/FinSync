# Architecture Decision Records

Each significant, hard-to-reverse decision gets one short record: the context, the decision, and its consequences. Records are numbered and never rewritten after acceptance; a changed decision gets a new record that supersedes the old one.

## Index

| # | Title | Status |
| --- | --- | --- |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-python-stdlib-and-sqlite.md) | Python standard library and SQLite for the prototype | Accepted |
| [0003](0003-layered-package-layout.md) | Layered package layout | Accepted |
| [0004](0004-event-based-transaction-matching.md) | Event-based, rule-scored transaction matching | Proposed |

## Template

Copy this into `NNNN-short-title.md`:

```markdown
# NNNN. Title

- Status: Proposed | Accepted | Superseded by NNNN
- Date: YYYY-MM-DD

## Context
What forces the decision; what was known at the time.

## Decision
What we do.

## Consequences
What becomes easier, what becomes harder, what follow-up work it creates.
```
