# FinSync — Shared Financial Tracking Prototype

FinSync is a personal and community-focused financial tracking project designed primarily for couples, families, and roommates who want to maintain a consistent overview of their shared expenses.

The project explores how financial transactions from different sources can be collected, normalized, and reconciled into a reliable, auditable record. Its main engineering challenge is **transaction matching across data sources**: detecting duplicate records without incorrectly merging separate financial events.

This repository contains an early backend prototype and serves as the foundation for a BSc thesis project.

## Project Goals

The main goal is to develop and evaluate a system that can:

* Collect financial transaction data from multiple input sources.
* Normalize incoming data into a consistent transaction model.
* Identify potential duplicates while preserving distinct transactions.
* Allow uncertain matches to be reviewed and incorrect matches to be corrected.
* Compare rule-based and LLM-based transaction categorization.
* Apply and evaluate security and privacy requirements appropriate for sensitive financial data.

## Current Implementation Status

The repository currently contains a minimal backend flow:

`Notification-like text / manual input → Parsing → Normalization → Rule-based categorization → SQLite storage → Group-scoped access`

### Implemented

* **Notification text parsing:** Deterministic parsing for a limited set of supported notification formats.
* **Normalized transactions:** Conversion of supported input data into a common transaction representation.
* **Manual transaction creation:** API endpoint for creating individual transactions.
* **Bulk transaction input:** API endpoint for importing multiple transactions from structured payloads, including rows prepared from a spreadsheet export.
* **Rule-based categorization:** Basic deterministic transaction categorization.
* **Persistent storage:** SQLite-based transaction persistence.
* **Group membership checks:** Read and write operations check whether the supplied user identifier belongs to the requested group.
* **Modular backend structure:** Separate modules for parsing, categorization, storage, business logic, and API handling.
* **Automated tests:** A test suite is included in the repository.

### Planned — Not Yet Implemented

* **Transaction matching:** Reconciliation of records originating from different input sources.
* **Duplicate detection:** Identification of likely duplicates while avoiding false merges of separate transactions.
* **Match review and correction:** Handling of uncertain matches, user confirmation, and correction of incorrect decisions.
* **Source traceability:** Recording where a transaction originated and how matching decisions were made.
* **Android integration:** Collection of supported banking notification data on an Android device.
* **Google Sheets integration:** Direct integration for convenient manual and bulk data entry.
* **LLM-based categorization:** Comparison of language-model categorization against the existing rule-based baseline.
* **Authentication and stronger access control:** Establishing user identity rather than trusting a client-supplied identifier.
* **Security and privacy evaluation:** Testing access-control boundaries, input validation, data minimization, and other relevant safeguards.

The items above describe intended development work, not completed functionality. The current parser supports only predefined notification formats; the repository does not yet provide a complete Android notification collector or direct Google Sheets integration.

## Main Thesis Contribution: Transaction Matching

Different input sources may represent the same financial event. For example, a purchase could be imported from a banking notification and later entered manually through a spreadsheet.

Simply comparing transaction amounts and timestamps is not sufficient. Two separate purchases may have the same amount and occur close together, while duplicate records may differ slightly in their descriptions or timestamps.

The planned matching process will investigate how to:

1. Identify potential duplicates using available transaction attributes.
2. Distinguish duplicate records from separate but similar transactions.
3. Handle incomplete or ambiguous information without silently making unreliable decisions.
4. Preserve source information and make matching decisions traceable.
5. Allow incorrect matches to be corrected.

The matching strategy and its thresholds will be evaluated against a prepared dataset with known expected outcomes.

## Evaluation Plan

### 1. Transaction Matching

A test dataset will contain examples of duplicate transactions, distinct transactions with similar attributes, incomplete records, and conflicting input data.

The evaluation will measure:

* **Duplicate detection precision:** How many records identified as duplicates are genuine duplicates.
* **Duplicate detection recall:** How many actual duplicates are successfully identified.
* **False merge rate:** How often separate financial events are incorrectly combined.
* **Missed duplicate rate:** How often duplicate records remain separate.
* **Ambiguous case handling:** Whether uncertain cases are flagged for review instead of being merged automatically.

The evaluation will also consider the ability to trace and correct matching decisions.

### 2. Transaction Categorization

The existing rule-based categorizer will serve as a baseline for comparison with a planned LLM-based approach.

Both approaches will be evaluated on the same manually labeled dataset using measures such as:

* Categorization accuracy.
* Performance on ambiguous or unfamiliar transaction descriptions.
* Consistency and error patterns.
* Response time and, where applicable, estimated operating cost.

The goal is to determine where an LLM provides a measurable benefit over deterministic rules, rather than assuming that an AI-based solution is inherently better.

### 3. Security and Privacy

Security and privacy will be treated as a separate evaluation area because the application handles sensitive financial information.

Planned areas of investigation include:

* Authentication and authorization, including attempts to access another group's data.
* Server-side input validation and handling of malformed requests.
* Data minimization and limiting access to information required for a given operation.
* Protection of credentials and other secrets.
* Traceability of relevant operations and data changes.
* Restricting AI components to explicitly authorized operations and treating their outputs as untrusted input.

Privacy requirements will be considered during design, with GDPR principles such as data minimization and appropriate access and retention controls taken into account where applicable. Compliance will not be claimed solely because these measures are implemented; applicable legal requirements must be assessed against the final system and its intended use.

The current group membership checks do not constitute complete authentication. In the current prototype, the user identifier is supplied by the client, so stronger identity verification is required before the system can safely handle real users' financial data.

All initial development and evaluation should use synthetic test data.

## Planned Architecture

The intended architecture separates input sources from the central transaction-processing logic.

```text
Android banking notifications ─┐
                               │
Manual transaction entry ──────┼──> Backend API
                               │         │
Spreadsheet / Google Sheets ───┘         ▼
                                  Input validation
                                         │
                                         ▼
                                 Transaction normalization
                                         │
                                         ▼
                                   Transaction matching
                                         │
                                         ▼
                               Central transaction database
                                         │
                            ┌────────────┴────────────┐
                            ▼                         ▼
                     Categorization             Group overview
                     Rules / LLM                and reporting
```

This diagram represents the planned architecture, not the current implementation. The current prototype uses SQLite; the final database and integration choices may evolve as requirements are refined.

The central database is intended to be the authoritative source of transaction records. Input sources should feed data into the same processing pipeline rather than maintain separate, conflicting transaction histories.

## Technology and Design Principles

The current prototype uses:

* **Python** for backend logic.
* **SQLite** for persistent storage.
* **HTTP API endpoints** for transaction operations.
* **Python unittest** for automated tests.

Further technology choices will be made as the architecture develops.

The project follows these design principles:

* Keep input parsing, business logic, storage, and API handling separated.
* Validate incoming data on the server.
* Avoid unnecessary dependencies and speculative features.
* Preserve transaction source information wherever practical.
* Make uncertain matching decisions reviewable.
* Keep rule-based and LLM-based categorization independently testable.
* Use automated tests to verify correctness and prevent regressions.
* Avoid exposing banking credentials or granting an AI component unrestricted database access.

## Running the Current Prototype

Run the backend from the repository root:

```bash
python -m finsync.api
```

The server listens on:

`http://127.0.0.1:8080`

### API Endpoints

All current endpoints require these headers:

* `X-User-Id`
* `X-Group-Id`

A default demo membership (`demo-user` in `demo-group`) is created for local demonstration.

| Method | Endpoint                   | Purpose                                                                 |
| ------ | -------------------------- | ----------------------------------------------------------------------- |
| `POST` | `/v1/notifications/ingest` | Parse, categorize, and store a supported notification-like text payload |
| `POST` | `/v1/transactions`         | Create a manual transaction                                             |
| `POST` | `/v1/transactions/bulk`    | Create multiple transactions from a structured payload                  |
| `GET`  | `/v1/transactions`         | List transactions accessible within the requested group                 |

These endpoints describe the current prototype. They do not imply that direct Android or Google Sheets integrations are available.

**Security note:** The demo membership and client-supplied identity headers are intended for local development only. They must not be treated as production authentication.

## Running the Tests

From the repository root:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

The test suite should be executed locally to verify the current implementation. Additional tests will be developed for transaction matching, ambiguous cases, authorization boundaries, and the evaluation scenarios described above.

## Development Roadmap

The planned milestones are:

1. **Validate the existing prototype:** Run the application and tests, inspect current behavior, and document any limitations.
2. **Define the matching problem:** Specify transaction identity, candidate matching attributes, ambiguous cases, and correction behavior.
3. **Implement and evaluate matching:** Build a test dataset with known outcomes and measure duplicate detection and false merges.
4. **Integrate the input sources:** Add the selected Android and spreadsheet data flows according to the agreed project scope.
5. **Evaluate categorization approaches:** Compare the rule-based baseline with an LLM-based implementation.
6. **Evaluate security and privacy:** Test authorization, validation, data handling, and relevant safeguards.
7. **Prepare the final prototype and thesis documentation:** Document architecture, design decisions, test results, limitations, and conclusions.

The exact scope of mobile and spreadsheet integration will be adjusted to preserve enough time for the core matching functionality and its evaluation.

## Academic Context

FinSync is being developed as a BSc thesis project in Business Informatics.

The primary contribution is the design, implementation, and evaluation of a reliable transaction-matching process for financial records arriving from multiple sources. The project will assess its effectiveness through reproducible tests and documented results, while treating AI-assisted categorization and security/privacy evaluation as additional engineering and evaluation areas.
