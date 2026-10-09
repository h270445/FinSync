# Project overview

FinSync is a personal and community-focused financial tracking project designed primarily for couples, families, and roommates who want to maintain a consistent overview of their shared expenses.

The project explores how financial transactions from different sources can be collected, normalized, and reconciled into a reliable, auditable record. Its main engineering challenge is **transaction matching across data sources**: detecting duplicate records without incorrectly merging separate financial events.

The repository is the foundation for a BSc thesis project (Szakdolgozat I. in autumn 2026, continued in Szakdolgozat II.).

## Project goals

The main goal is to develop and evaluate a system that can:

* Collect financial transaction data from multiple input sources.
* Normalize incoming data into a consistent transaction model.
* Identify potential duplicates while preserving distinct transactions.
* Allow uncertain matches to be reviewed and incorrect matches to be corrected.
* Compare rule-based and LLM-based transaction categorization.
* Apply and evaluate security and privacy requirements appropriate for sensitive financial data.

## Current implementation status

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
* **Modular backend structure:** Separate packages for API, application core, ingestion, categorization, matching and storage ([finsync/README.md](../finsync/README.md)).
* **Automated tests:** A test suite is included in the repository ([tests/README.md](../tests/README.md)).

### Planned — not yet implemented

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

Which of these items belong to this semester and which to Szakdolgozat II. is set in the [roadmap](planning/roadmap.md#semester-scope).

## Main thesis contribution: transaction matching

Different input sources may represent the same financial event. For example, a purchase could be imported from a banking notification and later entered manually through a spreadsheet.

Simply comparing transaction amounts and timestamps is not sufficient. Two separate purchases may have the same amount and occur close together, while duplicate records may differ slightly in their descriptions or timestamps.

The planned matching process will investigate how to:

1. Identify potential duplicates using available transaction attributes.
2. Distinguish duplicate records from separate but similar transactions.
3. Handle incomplete or ambiguous information without silently making unreliable decisions.
4. Preserve source information and make matching decisions traceable.
5. Allow incorrect matches to be corrected.

The matching strategy and its thresholds will be evaluated against a prepared dataset with known expected outcomes. The proposed design is in [design/transaction-matching.md](design/transaction-matching.md); the evaluation method is in [evaluation/evaluation-plan.md](evaluation/evaluation-plan.md).
