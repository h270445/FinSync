# Architecture overview

This document has two parts: the architecture **as implemented** today, and the **target** architecture, which is built during this semester. The order of work is in the [roadmap](../planning/roadmap.md#plan-by-phase).

## 1. Current architecture (implemented)

A single Python process using only the standard library:

```text
HTTP client
    │  X-User-Id / X-Group-Id headers, JSON body
    ▼
finsync.api          ThreadingHTTPServer + FinSyncRequestHandler
    │
    ▼
finsync.core         FinSyncService: authorization check, validation, use cases
    │
    ├──► finsync.ingestion       notification text parser
    ├──► finsync.categorization  keyword rules
    └──► finsync.storage         SQLite: group_memberships, transactions
```

Each incoming record becomes one row in `transactions`. There is no comparison with existing rows yet, so the same purchase sent twice is stored twice.

## 2. Target architecture

The target separates input sources from one central processing pipeline, so every source feeds the same validation, normalization and matching steps and there is one authoritative transaction history.

```text
Android banking notifications ─┐
                               │
Manual transaction entry ──────┼──> Backend API (authenticated)
                               │         │
Spreadsheet / Google Sheets ───┤         ▼
                               │
Web app (browser) ─────────────┘
                                  Input validation
                                         │
                                         ▼
                                 Transaction normalization
                                         │
                                         ▼
                                   Transaction matching ──► review queue
                                         │                  (confirm / reject / split)
                                         ▼
                               Central transaction database
                               (records, events, decision log)
                                         │
                            ┌────────────┴────────────┐
                            ▼                         ▼
                     Categorization             Group overview
                     Rules / LLM                and reporting
```

### Layers and responsibilities

| Layer | Package | Responsibility | Must not |
| --- | --- | --- | --- |
| Sources | separate clients (Android app, Sheets script) | Capture data, send it to the API | Hold their own transaction history |
| Web UI | `finsync/web/` (planned) | Static HTML/CSS/JS calling the `/v1` API: events, review, corrections, entry, import, tokens ([ADR 0005](decisions/0005-web-client-first.md)) | Call anything but the public API; hold business rules |
| API | `finsync.api` | Authentication, request parsing, size limits, error mapping, serialization | Contain business rules |
| Application | `finsync.core` | Use cases, authorization, transaction boundaries | Parse source formats or build SQL |
| Domain | `finsync.ingestion`, `finsync.matching`, `finsync.categorization` | Parsing, normalization, matching rules, categorization | Access the database, network or clock |
| Persistence | `finsync.storage` | Schema, migrations, queries, atomic writes | Make matching or categorization decisions |
| Evaluation | `finsync.evaluation` (planned) | Replay labelled datasets, compute metrics | Run inside the API |

### Target package layout

```text
finsync/
  api/             HTTP server, routes, auth middleware          (exists)
  core/            FinSyncService, use cases, errors             (exists)
  ingestion/       one parser per source: notifications, csv     (exists: notifications)
  matching/        normalize, fingerprint, scoring, decision     (planned)
  categorization/  rules (baseline), llm (comparison)            (exists: rules)
  storage/         sqlite, migrations                            (exists: sqlite)
  evaluation/      dataset replay and metrics runner             (planned)
  web/             static web app served by the API server       (planned)
tests/
  data/            labelled synthetic datasets                   (planned)
clients/
  android/         notification collector app (Kotlin)           (planned)
  google-sheets/   Apps Script sending sheet rows to the API     (planned)
```

Each client folder gets its own README with build and setup steps when it is created.

### Data model direction

Matching keeps every incoming record unchanged and links records that describe the same purchase to one **event**. Every link, review and correction is an append-only **match decision**. Details: [design/transaction-matching.md](../design/transaction-matching.md#data-model-changes).

```text
transactions (immutable source records) ──event_id──► events (what members see)
          ▲                                               ▲
          └──────────── match_decisions (append-only log) ┘
```

### Key flows

1. **Ingest:** source → API → validate → normalize → store record → match against candidate events in the same group → link, flag for review, or create a new event — all in one database transaction.
2. **Review:** a member lists `needs_review` decisions, confirms or rejects them; a wrong automatic link is undone with `split`. Each action writes a new decision that supersedes the old one.
3. **Query:** members read events (deduplicated) or raw records (with source and `event_id`) for their group only.
4. **Evaluate:** `python -m finsync.evaluation` replays a labelled dataset through a fresh in-memory database and prints precision, recall, false-merge rate and a threshold sweep.

## 3. Cross-cutting principles

* Keep input parsing, business logic, storage, and API handling separated.
* Validate incoming data on the server.
* Avoid unnecessary dependencies and speculative features.
* Preserve transaction source information wherever practical.
* Make uncertain matching decisions reviewable.
* Keep rule-based and LLM-based categorization independently testable.
* Use automated tests to verify correctness and prevent regressions.
* Avoid exposing banking credentials or granting an AI component unrestricted database access.
* Matching never crosses group boundaries; every lookup by id also filters by `group_id`.
* Deterministic, versioned matching (`matcher_version`), so thesis results can be reproduced.

## 4. Technology

| Concern | Now | Direction |
| --- | --- | --- |
| Language | Python (standard library) | Stay on the standard library while it suffices ([ADR 0002](decisions/0002-python-stdlib-and-sqlite.md)) |
| Storage | SQLite | SQLite with migrations; a server database only if multi-user deployment requires it |
| API | `http.server` | Keep; revisit a framework only if routing or auth becomes the bottleneck |
| Tests | `unittest` | Keep; add labelled datasets under `tests/data/` |
| Web UI | none | Plain HTML/CSS/JS, no build step, served by `http.server` ([ADR 0005](decisions/0005-web-client-first.md), proposed) |
| Clients | none | Android notification collector (Kotlin) and Google Sheets script (Phase 2 of the roadmap) |
| LLM | none | External LLM API called with the standard library (`urllib`), only for categorization, output validated |

## 5. Known architectural gaps

- Identity is supplied by the client in headers (no authentication).
- Notification timestamps are assumed UTC.
- Bulk import is not atomic (being fixed in a separate pull request).
- No schema versioning or migrations yet.
