# Technology stack

- Status: **Proposed** ([ADR 0006](decisions/0006-framework-based-stack.md)); the current implementation still uses the standard-library prototype described in [overview.md](overview.md#1-current-architecture-implemented)
- Date: 2026-10-09

This is the target stack for FinSync, introduced in two stages (see [Staging](#staging)), chosen from the current requirements: transaction matching across sources, review and correction, traceability, three clients (web, Android, Google Sheets), token authentication, LLM categorization, measurable evaluation, and a setup someone else can run. A second goal is that the stack is current industry practice, for learning and for the author's portfolio.

## Summary

```text
Browser ── React + TypeScript (Vite) ──┐
Android ── Kotlin + Jetpack Compose ───┼── HTTPS / JSON ──> FastAPI (Python) ──> PostgreSQL
Google Sheets ── Apps Script ──────────┘     │  SQLAlchemy + Alembic
                                              ├── matching, ingestion, categorization (pure Python)
                                              └── LLM provider (categorization only)

Local and deployment: Docker Compose (api, web, db) · CI: GitHub Actions
```

## Backend

| Concern | Choice | Why |
| --- | --- | --- |
| Language | **Python 3.12 or newer** | The matching, parsing and evaluation code already exists in Python and stays; strong data and LLM tooling for the evaluation. |
| Web framework | **FastAPI** | Request and response models with validation (Pydantic) replace hand-written parsing and error mapping; dependency injection fits the "current user and group" check on every endpoint; generates an OpenAPI description used for the API reference and the typed frontend client. Widely used, good for a portfolio. |
| Validation | **Pydantic v2** | Comes with FastAPI; one model per request body gives consistent 400/422 errors and request size limits in one place. |
| Database access | **SQLAlchemy 2.0** (Core and ORM, typed) | Explicit transactions and row locks, which the matching step needs; the same models work against PostgreSQL in production and in tests. |
| Migrations | **Alembic** | Replaces the hand-written schema versioning planned for Phase 1; every schema change is a reviewed, reversible file. |
| Database | **PostgreSQL** (current stable major version) | Real concurrent writers (several members and clients), row-level locks and transaction-scoped advisory locks for "match one record per group at a time", `JSONB` for raw payloads, and the database used in industry. |
| Authentication | **Argon2-hashed API tokens** for the Android app and Sheets script; **password login with an HttpOnly session cookie** for the web app | Clients cannot keep a password but can store a revocable token; browsers should not keep long-lived secrets in JavaScript-readable storage. Both resolve to the same user and group checks. |
| LLM | Official SDK of one provider, called only from `finsync.categorization` | Behind the categorizer interface, sends only description and merchant, output validated against the category list. Provider chosen in November. |
| Server | **Uvicorn** | The standard ASGI server for FastAPI. |

The layer rules of [ADR 0003](decisions/0003-layered-package-layout.md) stay: `finsync.api` becomes the FastAPI routers, `finsync.core` keeps the use cases, `finsync.storage` becomes the SQLAlchemy repositories, and `finsync.matching`, `finsync.ingestion` and `finsync.categorization` stay pure Python with no framework imports. This is what makes the switch cheap: the thesis logic does not depend on the framework.

## Web frontend

| Concern | Choice | Why |
| --- | --- | --- |
| Framework | **React 19 + TypeScript** | The most widely used UI library; strict typing catches API mismatches. Figma Make generates React, so its output can be used as a starting point after review. |
| Build tool | **Vite** | Fast development server, simple static build. A single-page app is enough: no server-side rendering is needed for a signed-in tool, so Next.js would only add a second server. |
| Routing | **React Router** | Standard client-side routing for the eight screens. |
| Server state | **TanStack Query** | Caching, loading and error states and refetch after a review action, without writing it by hand. |
| API client | **openapi-typescript** types generated from the FastAPI schema | Frontend and backend cannot drift apart silently. |
| Forms | **React Hook Form + Zod** | Typed validation for manual entry, import mapping and sign-in. |
| Styling and components | **Tailwind CSS + shadcn/ui** (Radix primitives) | Accessible components (dialogs, tabs, tables) copied into the repository rather than a heavy component library; matches Figma Make's output style. |
| Charts | **Recharts** | Only the overview bar chart needs one. |
| Formatting | `Intl.NumberFormat('hu-HU')`, `Intl.DateTimeFormat` | HUF and Hungarian dates without an extra library; the UI is Hungarian only. |

Angular was considered: it is complete and opinionated, but heavier for eight screens, and Figma Make output would not carry over. Vue or Svelte are lighter but less common in job requirements.

## Android

| Concern | Choice | Why |
| --- | --- | --- |
| Language and UI | **Kotlin + Jetpack Compose (Material 3)** | Current Android standard; the app has two screens. |
| Notification access | `NotificationListenerService` | The only supported way to read other apps' notifications. |
| Sending and retry | **WorkManager** with a local queue in **Room** | Sends survive restarts and offline periods; each notification carries a stable `source_ref`, so retries are re-deliveries, not new purchases. |
| HTTP | **Retrofit + OkHttp** (kotlinx.serialization) | Standard, typed HTTP client. |
| Token storage | **DataStore**, encrypted with an Android Keystore key | The token never sits in plain text. |

## Google Sheets

| Concern | Choice | Why |
| --- | --- | --- |
| Script | **Google Apps Script** (TypeScript, pushed with **clasp**) | Runs inside the sheet; clasp keeps the code in `clients/google-sheets/` under version control. |
| Sending | `UrlFetchApp` to `POST /v1/transactions/bulk` with an API token in Script Properties | Uses the same endpoint and token model as the other clients. |

## Quality, tooling and delivery

| Concern | Choice | Why |
| --- | --- | --- |
| Python packages | **uv** with `pyproject.toml` and a lock file | Fast, reproducible installs. |
| Python tests | **pytest** (runs the existing `unittest` tests unchanged), **httpx** test client | One runner for unit, API and integration tests. |
| Database in tests | PostgreSQL started by Docker Compose (locally) or as a GitHub Actions service | Tests run against the same database as production; matching's locking is tested for real. |
| Python lint and types | **Ruff** (lint and format), **mypy** | One fast linter; typed domain code. |
| Frontend tests | **Vitest + React Testing Library**; **Playwright** for a few end-to-end flows (sign in, review a match) | Unit tests for components, one browser test per key flow. |
| Frontend lint | **ESLint + Prettier**, TypeScript `strict` | |
| Containers | **Docker + Docker Compose**: `db`, `api`, `web` | With PostgreSQL and a Node build, one `docker compose up` is the simplest way for someone else to run the system. |
| Reverse proxy (when hosted) | **Caddy** | Automatic HTTPS in front of the API and the built frontend. |
| CI | **GitHub Actions**: lint, type check, tests (with PostgreSQL), frontend build | Every pull request is checked; the milestone tags are built from green `main`. |
| Evaluation | `python -m finsync.evaluation` against a temporary PostgreSQL database | Same code path as production; results reproducible from the repository. |

## Repository layout (target)

```text
finsync/            Python backend (FastAPI app, domain, storage)
migrations/         Alembic migrations
tests/              pytest suite and labelled datasets (tests/data/)
web/                React + TypeScript frontend (Vite)
clients/android/    Kotlin app
clients/google-sheets/  Apps Script (TypeScript, clasp)
docker-compose.yml  db, api, web
```

## What is deliberately not used

| Not used | Reason |
| --- | --- |
| Next.js / server-side rendering | Signed-in tool, no SEO; would add a second server. |
| Redux or another global store | Server state lives in TanStack Query; the remaining UI state is local. |
| Microservices, message queues | One backend and one database are enough; matching must run inside one database transaction. |
| Firebase, Firestore | Would replace the relational model and the matching transaction. |
| Kubernetes | Docker Compose on one host covers the demo and later hosting. |
| An ORM-free raw SQL layer | SQLAlchemy Core still allows explicit SQL where matching needs it. |

## Staging

Following the supervisor's advice (2026-10-09) to build on the existing backend and keep the semester's time for the core, the stack is introduced in two stages:

| Stage | Backend | Web | Clients | Delivery |
| --- | --- | --- | --- | --- |
| **Szakdolgozat I.** (this semester) | Existing standard-library backend and SQLite, extended with matching, review, tokens and migrations by hand ([ADR 0002](decisions/0002-python-stdlib-and-sqlite.md)) | React, TypeScript, Vite, TanStack Query, Tailwind CSS, shadcn/ui | Android (Kotlin, Compose) for one bank format; spreadsheet file import; Sheets script if time allows | Local run, GitHub Actions for tests |
| **Szakdolgozat II.** | FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL; the API contract stays the same | Unchanged | Fuller Android and Sheets clients | Docker Compose, hosting if needed |

The matching, ingestion and categorization packages are pure Python, so the backend migration does not touch the thesis logic. The web app talks only to the `/v1` API, so it does not change either. The second stage can start earlier only if all M2 acceptance criteria are met ahead of schedule.
