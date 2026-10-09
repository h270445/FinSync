# 0002. Python standard library and SQLite for the prototype

- Status: Accepted
- Date: 2026-10-09 (records the choice made in the initial prototype)

## Context

The prototype must be runnable by reviewers from the repository guide alone, and the thesis focus is the matching logic, not infrastructure.

## Decision

Use Python with only the standard library (`http.server`, `sqlite3`, `unittest`, `decimal`) and SQLite as the database.

## Consequences

- Setup is a single command with no package installation.
- Matching and evaluation stay reproducible on any machine.
- Routing, authentication and migrations must be written by hand; if they grow too large, a framework or a server database is a new decision with its own record.
- SQLite write concurrency is limited; atomic matching uses `BEGIN IMMEDIATE` transactions.
