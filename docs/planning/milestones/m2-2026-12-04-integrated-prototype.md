# M2 — Integrated prototype

- Deadline: 2026-12-04 23:59
- Tag: `v0.3.0`
- Status: planned
- Internal target: 2026-11-27

## Expected result (course)

The core flows committed for the semester work together, with proper data handling, basic error handling and tests.

## Acceptance criteria

- [ ] All sources go through the same matching pipeline: Android notifications (one bank format), spreadsheet-export files and manual entries (Google Sheets rows if the script is built).
- [ ] Demo: a notification on the phone and the same purchase imported from a spreadsheet appear as one event, while two separate purchases of the same amount on the same day stay two events.
- [ ] Uncertain matches can be listed, confirmed and rejected in the web app; a wrong link can be split; every action is logged and supersedes the previous decision.
- [x] Requests are authenticated: per-user API tokens for the Android app (and Sheets script), password login with a secure session cookie and CSRF protection for the web app; client-supplied identity headers are no longer trusted (tokens 2026-11-02, web sign-in 2026-11-12, [ADR 0010](../../architecture/decisions/0010-web-sign-in.md)).
- [x] Every endpoint has a cross-group access test (403/404, nothing written) (`tests/test_auth.py`, 2026-11-02).
- [ ] Malformed input, oversized bodies and failing bulk imports leave the database unchanged and return a clear error: 400 for malformed input, 413 for an oversized body (`tests/test_api_limits.py`, 2026-11-07; failing bulk imports were already atomic).
- [ ] The LLM categorizer runs behind the same interface as the rule-based one and its output is validated against the category list.
- [ ] Hybrid categorizer (Hungarian merchant and keyword layer, then model/LLM layer for mixed merchants) with an abstention threshold; coverage vs. accuracy, latency and cost measured on the 200-item dataset (supervisor, 2026-11-11).
- [ ] ADR 0008 implemented: `posted_at` and `ingested_at` stored separately, offset-less times read as Europe/Budapest.
- [ ] The test suite runs on SQLite and on PostgreSQL behind `FinSyncStorage`; the SQLite run stays fast.
- [ ] The web app is a whole: W2 overview with group totals by month, category and member; W4 decision history from the API; W6 manual entry; W7 bulk import preview; W8 settings with members, API tokens (create, revoke) and merchant–category rule overrides.
- [ ] One versioned agent skill in the repository, and the six design views in `docs/` (skills done 2026-11-12: five in [`.claude/skills/`](../../../.claude/skills/README.md); design views open).

## Checklist

- [x] Authentication and request size limits (API tokens done 2026-11-02, [ADR 0009](../../architecture/decisions/0009-api-tokens.md); request size limits done 2026-11-07 with the FastAPI switch; web password login done 2026-11-12, [ADR 0010](../../architecture/decisions/0010-web-sign-in.md)).
- [ ] Review and correction endpoints with tests.
- [ ] Web app: event list, event detail with split and category correction, review queue (manual entry, file import and token management if time allows).
- [ ] Android app (notification listener, token setup, sending, retry) with its README (done 2026-11-12 and tested on the emulator; open: the test on the real phone, and the token kept in plain preferences).
- [ ] File import with `import_batch_id` and `source_ref`; Sheets script if time allows.
- [ ] LLM categorizer and labelled categorization dataset (dataset done 2026-11-08: `tests/data/categorization_eval.csv`, 200 synthetic items).
- [ ] Money transfers: `transfer` direction for records to or from the group's own accounts and counterparties (per-group list), excluded from spending and income totals.
- [ ] Category correction, the "mixed" flag and category lines (lines add up to the event amount; totals follow them).
- [x] HTTP layer on FastAPI with an OpenAPI schema (ADR 0006 step 1, 2026-11-07).
- [ ] Storage on SQLAlchemy, Alembic and PostgreSQL with Docker Compose (ADR 0006 step 2, Nov 16–22, time-boxed).
- [ ] Docs updated (API reference, security status, client setup in the guides).
- [ ] Release notes, tag `v0.3.0`, e-mail.
