---
name: endpoint-and-screen-checklist
description: Use when adding or changing a FinSync API route (finsync/api/server.py) or a web screen (web/src/pages), for example W1, W2, W6, W7, W8 or a new /v1 endpoint. Enforces group isolation, the error contract, OpenAPI and type sync, Hungarian UI text, tests and docs.
---

# Endpoint and screen checklist

- Version: 1.0 (2026-11-12)
- Owner: Bence Varga
- Why it exists: every new route has to pass the same isolation, error and schema checks, and every new screen has to stay in step with the generated API types. Done by hand, one of them was easy to forget. The supervisor named "a group-isolation and OpenAPI-sync check for new endpoints" as a skill candidate (2026-11-11, action D1).

## Input

- What to build: the route (method, path, request and response shape) or the screen (W-number from [docs/design/user-interface.md](../../../docs/design/user-interface.md)).
- Where it is planned: the roadmap line, M2 checklist item or supervisor action it serves.

If the request does not say who may call the route, what a member of another group gets, or what an invalid body returns, take the rules below. If the design leaves something open that changes behaviour (for example what a total includes), stop and ask (checkpoint 1).

## Output

1. Code, tests and docs in the working tree, all gates in "Self-check" green.
2. A short report in the reply: the checklist below with each line marked done, not needed (with the reason) or open, plus the gate results with test counts.

## Prohibitions

- Never take the member or the group from the body, the query, the path or an `X-User-Id`/`X-Group-Id` header. Identity comes from the `Caller` dependency (the API token) only ([ADR 0009](../../../docs/architecture/decisions/0009-api-tokens.md)).
- Never let a storage query over group data (transactions, events, decisions, members, rules) run without `group_id` in its `WHERE` clause. An id from another group answers `404`, never `403` and never data.
- Never return `422`. Validation errors go through the existing handlers and answer `400` with `{"error": "..."}`.
- Never hand-edit `web/openapi.json` or `web/src/api/schema.d.ts`. They are generated.
- Never skip, delete or loosen an existing test to get green, including the route list in `tests/test_auth.py`.
- Never make the matching engine (`finsync/matching/`) more complex; it is frozen (supervisor, 2026-11-11). Wiring a new route to it is fine.
- Never put real names, amounts, merchants, account numbers or e-mail addresses in fixtures, tests, screenshots or docs. Use the synthetic members (`anna`, `balint`, `user-a`...) and made-up shops.
- No English text in the web UI; the UI is Hungarian only (author's decision, 2026-11-07). Code, comments and repo docs stay in English.
- No new Python or npm dependency without asking (checkpoint 2).

## Checklist

### Backend

- [ ] Service method in `finsync/core/service.py` that starts with `self.ensure_authorized(user_id, group_id)`; writes go through one transaction so a failure leaves the database unchanged.
- [ ] Storage method in `finsync/storage/sqlite.py` that filters by `group_id`; returns `None` (mapped to `NotFoundError`) for an id outside the group.
- [ ] A schema change bumps `SCHEMA_VERSION` with a `_migrate_to_N` step and a test that an older database is upgraded (see `test_a_version_2_database_gets_the_token_table`). This needs checkpoint 1.
- [ ] Route in `finsync/api/server.py` with `caller: Caller`, a Pydantic `...In` model for the body and a `...Out` model as the return type, so the OpenAPI schema is complete. Errors are raised as the core exceptions (`ValueError` → 400, `NotFoundError` → 404, `ConflictError` → 409, `AuthorizationError` → 403), not as `HTTPException`.
- [ ] A body that can exceed 64 KiB in normal use is a design question (only `/v1/transactions/bulk` has the 1 MiB limit). Ask instead of raising the limit.

### Tests

- [ ] The route is added to `ENDPOINTS` in `tests/test_auth.py` (path parameters as `{event}`/`{decision}`, or extend the replacement in `test_every_route_is_listed`). A POST route also gets its body in `_body`, and `test_another_groups_member_cannot_read_or_change_group_1` gets the expected answer for it (404 for a foreign id, 200 without group 1 data for a list, 201 into the caller's own group for a create).
- [ ] Behaviour tests in the test file of the feature (`test_review.py`, `test_finsync_service.py`, ...): the normal case, the empty case, and the database left unchanged after a refused write.
- [ ] A route with a body gets a malformed-body case in `test_malformed_requests_get_a_clear_400` (`tests/test_api_limits.py`).
- [ ] A new response model is used by the route, so `test_the_openapi_schema_describes_what_the_api_does` covers it (no 422, bearer security on every operation).

### OpenAPI and types

- [ ] From `web/`, with the Python virtual environment activated: `npm run gen:api` (it runs `python -m finsync.api --openapi`; `$PYTHON` overrides which Python).
- [ ] `git diff web/openapi.json web/src/api/schema.d.ts` shows only the new or changed route and models. Other changes usually come from a different Pydantic version (seen on 2026-11-12: a `pattern` on `Decimal | str` fields appears or disappears). Do not commit those; note them in the report.
- [ ] New response types get an alias in `web/src/api/client.ts` (`export type X = components['schemas']['XOut']`).

### Web screen

- [ ] Query or mutation hook in `web/src/api/queries.ts`; a mutation that changes events, reviews or totals invalidates the affected queries (review actions use `useInvalidateAll`).
- [ ] Page in `web/src/pages/`, wired in `web/src/App.tsx` in place of its `PlaceholderPage` route.
- [ ] Loading, error and empty states with `LoadingRows`, `ErrorState` and `EmptyState` from `web/src/components/states.tsx`; a refused action shows the backend's error message.
- [ ] Hungarian labels, Hungarian number and date formatting through `web/src/lib/format.ts`.
- [ ] Vitest test next to the page (`*.test.tsx`, see `ReviewPage.test.tsx`) for the behaviour that matters: the main action, a refusal, the empty state.
- [ ] Usable at 360 px wide and at 1280 px (screenshots when a browser is available).

### Docs

- [ ] `docs/guides/api.md`: endpoint table row, a section with a request and response example, and any new status code in the status table.
- [ ] `docs/design/user-interface.md`: the screen's row (the API column names the endpoints it now uses; "planned" removed once they exist).
- [ ] `docs/architecture/security-and-privacy.md` when the change touches authentication, sessions, tokens or what data is stored.
- [ ] `finsync/api/README.md` when the HTTP layer's rules change.
- [ ] M2 checklist ([milestones/m2-...](../../../docs/planning/milestones/m2-2026-12-04-integrated-prototype.md)) and the supervisor action in [supervisor-feedback.md](../../../docs/planning/supervisor-feedback.md) ticked only when the whole criterion is met; otherwise note what is done in brackets, as the existing lines do.

## Self-check

Run every gate and copy the result lines into the report. A gate that cannot run (for example no Node in the environment) is reported as not run, never as passed.

```bash
python -m unittest discover -s tests            # all OK; the count grows by the new tests
python -m finsync.api --openapi | diff - web/openapi.json   # empty, or only the known Pydantic drift
cd web && npm run lint && npm test && npm run build          # no lint errors, all Vitest tests pass, build succeeds
git diff --stat                                              # only the files the checklist expects
```

Then read the diff once more against the prohibitions, specifically: every new SQL statement has `group_id`; no new route reads a header other than `Authorization`; no English string in `web/src/pages`; nothing in the fixtures looks like real personal data.

## Human checkpoints

1. **Before** a database schema change, a change to authentication, session or error semantics, or when the design leaves a behaviour open: stop and ask the author, with a recommended option.
2. **Before** adding a dependency: ask, naming the package, version and why the standard library or an existing dependency is not enough.
3. **After**: the author reads the diff before the session's pull request is merged. The report lists anything the gates do not cover (for example a screen not tried in a browser).

## Change log

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-12 | First version, derived from the W4 decision history change (PR #25) and the token and size-limit tests. |
