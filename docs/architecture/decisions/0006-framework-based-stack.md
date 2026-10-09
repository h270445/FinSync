# 0006. Framework-based stack: FastAPI, PostgreSQL, React

- Status: Proposed (supersedes [0002](0002-python-stdlib-and-sqlite.md) when accepted)
- Date: 2026-10-09

## Context

ADR 0002 chose the Python standard library and SQLite so the prototype runs with no installation. The committed semester scope has since grown to three clients (web, Android, Google Sheets), token and password authentication, concurrent writes from several members, schema migrations and an LLM categorizer. With the standard library, routing, validation, authentication and migrations would all be hand-written. The author also wants to learn and show current industry tools. The supervisor advised (2026-10-09) to build on the existing backend instead of rebuilding it and to keep the semester's time for the matching core.

## Decision

Adopt the stack in [technology-stack.md](../technology-stack.md) this semester, building on the existing backend: parsing, categorization and matching are carried over; the HTTP and storage layers are replaced.

- Backend: FastAPI, Pydantic, SQLAlchemy 2.0, Alembic, PostgreSQL, Uvicorn.
- Web frontend: React with TypeScript and Vite, TanStack Query, Tailwind CSS with shadcn/ui, types generated from the OpenAPI schema.
- Android: Kotlin with Jetpack Compose, WorkManager and Room.
- Google Sheets: Apps Script in TypeScript, managed with clasp.
- Delivery: Docker Compose for local runs and hosting, GitHub Actions for CI.

The layered layout of [ADR 0003](0003-layered-package-layout.md) stays; matching, ingestion and categorization remain framework-free Python.

## Consequences

- Validation, OpenAPI documentation, migrations and typed clients come from the tools instead of hand-written code.
- Running the system needs Docker (or Python, Node and PostgreSQL installed); the getting-started guide changes accordingly.
- Matching serializes per group with a transaction-scoped PostgreSQL advisory lock instead of SQLite's `BEGIN IMMEDIATE`.
- The first week of Phase 1 is spent on the switch; fallback if M1 is at risk: keep FastAPI and SQLAlchemy on SQLite until M2.
- More dependencies to keep up to date; versions are pinned in lock files.
