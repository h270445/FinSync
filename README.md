# FinSync — Shared Financial Tracking Prototype

FinSync is a personal and community-focused financial tracking project for couples, families, and roommates who want a consistent overview of their shared expenses. Its main engineering challenge is **transaction matching across data sources**: detecting duplicate records without incorrectly merging separate financial events.

This repository contains an early backend prototype and is the foundation for a BSc thesis project.

## Thesis commitment (Szakdolgozat I., autumn 2026)

**Target users and scenario.** A shared household of 2–4 people (a couple or roommates) who track their common expenses. Anna's phone captures a 4 500 Ft SPAR card purchase from the bank notification; later Bálint records the same purchase from the shared spreadsheet. FinSync must count it once. If two separate 4 500 Ft purchases happened on the same day, it must keep both.

**The hard part.** The sources do not give clean, independent data, and equal amount and time alone are not enough to decide. FinSync has to decide which information makes two records the same purchase, when to ask a member for confirmation, and how a wrong link is corrected, while keeping every decision traceable ([matching design](docs/design/transaction-matching.md)).

**Committed capabilities** (details and priority order in the [roadmap](docs/planning/roadmap.md#semester-scope)):

1. Records from bank notifications, manual entry and spreadsheet imports end up in one reviewable list of purchases (events).
2. Duplicates are linked across sources, look-alike separate purchases stay separate, and uncertain cases go to a member for confirmation.
3. Every record keeps its source, and every link, confirmation, rejection and split is logged and can be undone.
4. Members are authenticated and see only their own group's data.
5. Rule-based and LLM-based categorization are compared on the same hand-labelled transactions; a member can correct the suggested category.

**How correctness is verified.**

- A labelled synthetic dataset with repeated deliveries, duplicates across sources, look-alike separate purchases and faulty or incomplete input. Metrics: duplicates found, separate purchases wrongly merged, cases sent to review. Compared with a naive baseline that stores every row separately ([evaluation plan](docs/evaluation/evaluation-plan.md)).
- Categorization: accuracy, error patterns, time and cost of both methods on the same labelled set.
- Automated tests for each flow and a cross-group access test for every endpoint. Synthetic data only.

**Implemented today vs planned.**

- *Implemented:* an HTTP API with parsing of two predefined notification text patterns, manual and bulk entry, keyword-based categorization, SQLite storage, group-membership checks and five tests.
- *Planned:* matching and duplicate detection, review and correction, authentication (identity is currently supplied by the request), the Android app, spreadsheet and Google Sheets input, LLM categorization, the web app and the evaluation runner.

**Effort and experience.**

- Planned weekly effort: two working days per week (Friday and Saturday). Time spent is logged in [docs/planning/time-log.md](docs/planning/time-log.md).
- Experience with the planned technologies: React, Docker, PostgreSQL and AWS from university course projects, and a mobile-first website. New for this project: a complete Android app, LLM integration and Google Sheets integration.

## Quick start

Requires Python 3.10+ and no third-party packages.

```bash
python -m finsync.api                    # API on http://127.0.0.1:8080
python -m unittest discover -s tests     # run the tests
```

Details: [docs/guides/getting-started.md](docs/guides/getting-started.md).

## Documentation

| Topic | Where |
| --- | --- |
| Goals, thesis contribution, current status | [docs/overview.md](docs/overview.md) |
| Running and API reference | [docs/guides/](docs/guides/README.md) |
| Architecture and decision records | [docs/architecture/](docs/architecture/README.md) |
| Transaction matching design | [docs/design/transaction-matching.md](docs/design/transaction-matching.md) |
| Evaluation plan and results | [docs/evaluation/](docs/evaluation/README.md) |
| Semester roadmap and milestones | [docs/planning/](docs/planning/README.md) |
| Release notes | [docs/releases/](docs/releases/README.md) |
| AI usage | [docs/ai-usage.md](docs/ai-usage.md) |

Start at [docs/README.md](docs/README.md) for the full map and conventions.

## Repository layout

```text
finsync/            backend package (each subfolder has a README)
  api/              HTTP server and routes
  core/             use cases and authorization
  ingestion/        input parsers
  categorization/   rule-based categorizer
  matching/         transaction matching (planned)
  storage/          SQLite persistence
tests/              unittest suite
docs/               documentation
```

## Security note

The demo membership and client-supplied identity headers are intended for local development only and are not authentication. Use synthetic data only.

## License

See [LICENSE](LICENSE).
