# 0003. Layered package layout

- Status: Accepted
- Date: 2026-10-09

## Context

The initial prototype kept every module flat in `finsync/`. The planned work adds matching, review, evaluation, new input sources and an LLM categorizer, which would make a flat package hard to navigate and blur which code may access the database.

## Decision

Split `finsync/` into subpackages by layer: `api`, `core`, `ingestion`, `categorization`, `matching`, `storage` (and later `evaluation`). Imports point only downwards (`api → core → domain packages, storage`); domain packages are pure and do not access the database. Each subpackage re-exports its public names in `__init__.py` and documents itself in a `README.md`.

## Consequences

- Matching rules can be unit-tested without a database.
- Each folder's purpose is visible from its README.
- The move was done as pure file moves plus import updates, so open pull requests against the old paths merge with only import-line conflicts.
- `python -m finsync.api` still starts the server (`finsync/api/__main__.py`).
