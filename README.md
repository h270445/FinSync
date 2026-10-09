# FinSync — Shared Financial Tracking Prototype

FinSync is a personal and community-focused financial tracking project for couples, families, and roommates who want a consistent overview of their shared expenses. Its main engineering challenge is **transaction matching across data sources**: detecting duplicate records without incorrectly merging separate financial events.

This repository contains an early backend prototype and is the foundation for a BSc thesis project.

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
