# Design views

- Status: **Draft** (2026-11-14). Views 3–6 are first drafts drawn from the code and the design documents; all six are finalised at the end of November, after the W2, W7 and W8 screens are settled, and before M2 (2026-12-04).
- Asked for by the supervisor: six design views that form one coherent frame ([feedback, action D2](../planning/supervisor-feedback.md#2026-11-11--reply-to-the-m1-e-mail)).
- Notation: [Mermaid](https://mermaid.js.org/), which GitHub renders, so each view is versioned and reviewed like code. Names (states, routes, packages, screen ids) are the ones used in the code, so the views can be checked against it.

| # | View | State |
| --- | --- | --- |
| 1 | Use-case diagram | Planned (end of November) |
| 2 | Page flow: W1–W8 and Android A1–A2 | Planned (end of November) |
| 3 | [Ingest, match, store or review](#3-ingest-match-store-or-review) | Draft |
| 4 | [Event and decision states](#4-event-and-decision-states) | Draft |
| 5 | [Layered architecture](#5-layered-architecture) | Draft |
| 6 | [Security: authentication and group isolation](#6-security-authentication-and-group-isolation) | Draft |

## 3. Ingest, match, store or review

Every input path runs through the same steps, synchronously on each insert ([matching design](../design/transaction-matching.md#matching-approach)). Thresholds are those of `rules-3`.

```mermaid
flowchart TD
    A1[Android notification<br/>POST /v1/notifications/ingest] --> V
    A2[Manual entry, W6<br/>POST /v1/transactions] --> V
    A3[Bulk import<br/>POST /v1/transactions/bulk] --> V
    V{Valid input and<br/>caller in the group?} -- no --> E[400 / 403, nothing stored]
    V -- yes --> N[Normalise: Decimal amount and sign,<br/>UTC instant or calendar day ADR 0008,<br/>merchant key, category rules]
    N --> F{Same fingerprint<br/>already stored?}
    F -- "yes, notification or row with source_ref" --> D1[Store as re-delivery:<br/>exact_duplicate, joins the original's event]
    F -- "yes, manual row without reference" --> R
    F -- no --> C[Candidates: same group, currency, direction,<br/>equal amount, time window,<br/>channel slot free]
    C --> S[Score S = 0.4·amount + 0.3·time + 0.3·merchant]
    S --> T{Best S and runner-up}
    T -- "S ≥ 0.95, no runner-up within 0.10,<br/>passes the strict gate" --> L[auto_linked: record joins the event]
    T -- "0.60 ≤ S < 0.95, close runner-up,<br/>strict gate or contested link" --> R[needs_review: own event,<br/>shown in the W5 review queue]
    T -- "S < 0.60 or no candidate" --> P[separate: new event]
    D1 & L & R & P --> W[(Record, event and decision<br/>stored in one transaction)]
```

## 4. Event and decision states

Decisions are append-only: a later decision supersedes an earlier one for the same record, nothing is overwritten. The event itself only carries `review_state`.

```mermaid
stateDiagram-v2
    direction LR
    state "Decision of a new record" as decision {
        [*] --> separate
        [*] --> exact_duplicate
        [*] --> auto_linked
        [*] --> needs_review
        needs_review --> confirmed: member, Ugyanaz a vásárlás
        needs_review --> rejected: member, Két külön vásárlás
        auto_linked --> split: member splits the record out
        confirmed --> split: member splits, also the undo in W5
    }
    state "Event review_state" as event {
        state "needs_review" as needs_review_event
        [*] --> clear
        clear --> needs_review_event: a record awaits review, or a later record contests a link
        needs_review_event --> clear: confirmed or rejected
    }
    note right of decision
        rejected pairs are never proposed again.
        A re-delivery always moves with its original.
    end note
```

## 5. Layered architecture

```mermaid
flowchart TB
    subgraph Clients
        AND[Android app<br/>clients/android, Kotlin]
        WEB[Web app<br/>web/, React + TypeScript]
        CLI[CLI tools<br/>tokens, passwords]
    end
    subgraph API["finsync.api (FastAPI)"]
        R[Routes, request and response models,<br/>body size limit, OpenAPI schema]
        AUTH[Caller dependency:<br/>Bearer token or session cookie + CSRF]
    end
    subgraph CORE["finsync.core"]
        SVC[FinSyncService: use cases,<br/>membership check, validation]
        TOK[TokenService, sessions, passwords]
    end
    subgraph DOMAIN[Pure rules]
        ING[finsync.ingestion<br/>notification parsers, local time]
        CAT[finsync.categorization<br/>keyword rules]
        MAT[finsync.matching<br/>normalise, fingerprint, score, decide]
    end
    STO[(finsync.storage<br/>SQLAlchemy Core, Alembic<br/>SQLite or PostgreSQL)]
    EVAL[finsync.evaluation<br/>datasets, offline runners]

    AND -- HTTPS JSON --> R
    WEB -- same origin /v1 --> R
    R --> AUTH --> SVC
    CLI --> TOK
    SVC --> ING & CAT & MAT
    SVC --> STO
    TOK --> STO
    EVAL --> MAT & CAT
```

A layer calls only the layers below it; the matching, parsing and categorization packages have no database or HTTP access ([overview](overview.md#layers-and-responsibilities)).

## 6. Security: authentication and group isolation

```mermaid
sequenceDiagram
    autonumber
    participant C as Client (Android app or browser)
    participant A as finsync.api
    participant K as finsync.core
    participant D as Storage
    alt Android app or script
        C->>A: request with Authorization: Bearer fs_…
        A->>D: look up SHA-256(token), not revoked
    else Web app
        C->>A: request with session cookie (HttpOnly, Secure, SameSite=Strict)<br/>and X-CSRF-Token on every change
        A->>D: look up SHA-256(session), not expired, check CSRF token
    end
    D-->>A: member and group of the token or session
    Note over A: identity never comes from the body,<br/>the query or X-User-Id / X-Group-Id headers
    A->>K: use case with (member, group)
    K->>D: ensure_authorized(member, group)
    K->>D: every query filtered by group_id
    D-->>K: rows of this group only (an id from another group: not found)
    K-->>A: result or error
    A-->>C: 2xx, or 400 / 401 / 403 / 404 / 413 as {"error": "…"}
```

Details: [ADR 0009](decisions/0009-api-tokens.md) (API tokens), [ADR 0010](decisions/0010-web-sign-in.md) (web sign-in), [security and privacy](security-and-privacy.md); every endpoint has a cross-group test in `tests/test_auth.py`.
