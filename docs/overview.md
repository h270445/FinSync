# Project overview

FinSync is a personal and community-focused financial tracking project designed primarily for couples, families, and roommates who want to maintain a consistent overview of their shared expenses.

The project explores how financial transactions from different sources can be collected, normalized, and reconciled into a reliable, auditable record. Its main engineering challenge is **transaction matching across data sources**: detecting duplicate records without incorrectly merging separate financial events.

The repository is the foundation for a BSc thesis project (built in Szakdolgozat I., autumn 2026; refined and written up in Szakdolgozat II.).

## Project goals

The main goal is to develop and evaluate a system that can:

* Collect financial transaction data from multiple input sources.
* Normalize incoming data into a consistent transaction model.
* Identify potential duplicates while preserving distinct transactions.
* Allow uncertain matches to be reviewed and incorrect matches to be corrected.
* Compare rule-based and LLM-based transaction categorization.
* Apply and evaluate security and privacy requirements appropriate for sensitive financial data.

## Current implementation status

Status on 2026-11-25 (M2 closing package, [v0.3.0 notes](releases/v0.3.0.md)). The flow that runs today:

`Android notification / manual entry / bulk rows / spreadsheet export → Parsing and normalisation → Matching (event, decision log) → Hybrid categorization (group rules, Hungarian dictionary, optional LLM) → SQLite or PostgreSQL storage → Review and correction in the web app`

### Implemented

* **Ingestion:** the OTP Bank notification format and the synthetic prototype formats ([ingestion](../finsync/ingestion/README.md)); manual entries; atomic bulk import; CSV and XLSX import of spreadsheet exports with a preview, column mapping and refusal of a file imported before ([API](guides/api.md#post-v1imports)). Times without an offset are read as Europe/Budapest ([ADR 0008](architecture/decisions/0008-notification-time-and-calendar-day.md)).
* **Transaction matching (main contribution):** every record is linked to an event; exact re-deliveries, confident cross-source matches and uncertain cases are told apart by an explainable rule-based score, and each decision is logged with its reason ([design](design/transaction-matching.md)). Frozen at `rules-3` after measurement.
* **Review and correction:** uncertain matches are listed, confirmed or rejected, a wrong link can be split, and every action supersedes the previous decision.
* **Measured matching results:** synthetic labelled datasets, a leak-free dev/test protocol and the store-every-row baseline ([results](evaluation/README.md)).
* **Hybrid categorization:** the group's merchant rules, then a Hungarian merchant and keyword dictionary, then an optional LLM layer with an abstention threshold ("Bizonytalan"); measured against the rule-based baseline ([result](evaluation/results/2026-11-24-categorization-hybrid.md), [ADR 0011](architecture/decisions/0011-llm-categorization-layer.md)). The LLM runs in the live flow only when a group admin turns it on, within a monthly budget ([ADR 0013](architecture/decisions/0013-llm-in-the-live-flow.md)).
* **Category correction:** confirm or change a category, mark a purchase as mixed, split it into category lines, mark a record as a transfer; every change is logged, and merchant memory learns only from non-mixed merchants ([design](design/categorization.md#review-in-the-web-app)).
* **Money transfers:** records to or from the group's own accounts and counterparties are transfers and left out of the totals.
* **Authentication:** per-member API tokens for the Android app ([ADR 0009](architecture/decisions/0009-api-tokens.md)); password sign-in for the web app with an HttpOnly session cookie and CSRF protection ([ADR 0010](architecture/decisions/0010-web-sign-in.md)); admin and member roles; actions that widen access only from a web session ([ADR 0012](architecture/decisions/0012-no-multi-factor-authentication.md)); every endpoint has a cross-group access test.
* **HTTP API:** FastAPI with an OpenAPI schema and request size limits ([API guide](guides/api.md)).
* **Web app:** sign-in, overview with totals by month, category and member (W2), event list and detail with split, category correction and decision history (W3, W4), review queue, manual entry (W6), file import with preview (W7), settings with members, roles, API tokens, merchant rules, own accounts and the LLM schedule (W8) ([web/](../web/README.md)).
* **Android app:** forwards OTP Bank transaction notifications with an outbox and retries that never create a second event; tested on the emulator and on the real phone ([clients/android/](../clients/android/README.md)).
* **Storage and structure:** SQLAlchemy and Alembic on SQLite or PostgreSQL 16 (Docker Compose), the whole test suite runs on both ([ADR 0006](architecture/decisions/0006-framework-based-stack.md)); separate packages for API, core, ingestion, categorization, matching and storage ([finsync/](../finsync/README.md)); automated tests ([tests/](../tests/README.md)).
* **Demo:** a seeded synthetic group and a step-by-step [demo guide](guides/demo.md).

### Planned — not yet implemented

* **Google Sheets script:** only if time allows (lowest priority of the M2 buffer).
* **Android:** the token is still kept in plain app preferences; the split of the setup and status screens (A1/A2) is a later cleanup.
* **Security and privacy evaluation:** access-control boundaries, input validation, data minimisation, written up for the thesis.
* **Thesis manuscript** and the M3 preliminary package ([M3](planning/milestones/m3-2027-01-15-preliminary-package.md)).

The [roadmap](planning/roadmap.md) holds the order and dates, and the [M2 milestone](planning/milestones/m2-2026-12-04-integrated-prototype.md) what is still open.

All of these items are committed for this semester (Szakdolgozat I.), the Android app and spreadsheet input in a reduced scope; the order and dates are in the [roadmap](planning/roadmap.md#semester-scope).

## Main thesis contribution: transaction matching

Different input sources may represent the same financial event. For example, a purchase could be imported from a banking notification and later entered manually through a spreadsheet.

Simply comparing transaction amounts and timestamps is not sufficient. Two separate purchases may have the same amount and occur close together, while duplicate records may differ slightly in their descriptions or timestamps.

The matching process addresses how to:

1. Identify potential duplicates using available transaction attributes.
2. Distinguish duplicate records from separate but similar transactions.
3. Handle incomplete or ambiguous information without silently making unreliable decisions.
4. Preserve source information and make matching decisions traceable.
5. Allow incorrect matches to be corrected.

The matching strategy and its thresholds are evaluated against prepared datasets with known expected outcomes ([results](evaluation/README.md)). The design is in [design/transaction-matching.md](design/transaction-matching.md); the evaluation method is in [evaluation/evaluation-plan.md](evaluation/evaluation-plan.md).
