# API reference

Status: describes the endpoints **implemented** in `finsync/api/server.py`.

## Common rules

- Every request needs an API token, `Authorization: Bearer fs_...`, or the web app's session cookie (see [`/v1/session`](#post-v1session)). The token or the session decides the member and the group; `X-User-Id` and `X-Group-Id` headers are ignored ([ADR 0009](../architecture/decisions/0009-api-tokens.md), [ADR 0010](../architecture/decisions/0010-web-sign-in.md)). A token wins over a cookie.
- With the session cookie, every `POST`, `PUT`, `PATCH` and `DELETE` also needs `X-CSRF-Token: <csrf_token>` from the session; without it the answer is `403` and nothing is written.
- A signed-in member issues and revokes their own tokens on the web app's settings screen (W8, [`/v1/tokens`](#get-v1tokens-post-v1tokens-post-v1tokenstoken_idrevoke)). On the server, `python -m finsync.api.tokens create --user <member> --group <group> --name <what for>` and `... revoke <id>` still work, for example for the first member; see [getting started](getting-started.md#create-an-api-token).
- Request and response bodies are JSON objects. `POST` and `PUT` bodies are limited to 64 KiB, and to 1 MiB for `/v1/transactions/bulk` and `/v1/imports`.
- Validation errors are `400`, not FastAPI's usual `422`.
- The OpenAPI schema is served at `/openapi.json`, with an interactive page at `/docs`; `python -m finsync.api --openapi` prints it without starting the server.

| Status | When |
| --- | --- |
| `201` | Created |
| `200` | Read succeeded |
| `400` | Invalid JSON, validation error (`{"error": "..."}`) |
| `401` | No token, or a malformed, unknown or revoked one (`WWW-Authenticate: Bearer`); no valid session; a failed sign-in |
| `403` | The member is no longer in the group, a member who is not an admin changes a group setting (merchant rules, own accounts, roles, the LLM schedule), the member is not in the named group at sign-in, a cookie request without a valid CSRF token, or an API token used on `/v1/tokens`, `PUT /v1/members/{member_id}/role` or `PUT /v1/llm-settings` (web session only, least privilege, ADR 0012) |
| `404` | Unknown path, or an id that does not exist in the requested group |
| `409` | A review action that no longer fits, such as answering a decision twice; a file that was already imported; a second merchant rule for the same merchant or a second entry for the same own account; demoting the group's last admin; a category change on a transfer or on an event split into lines; asking the model about a settled category, without a model on the server or over the group's monthly budget |
| `413` | A body over the size limit |

## Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/v1/session` | Sign in to the web app: sets the session cookie, returns the CSRF token |
| `GET` | `/v1/session` | The signed-in member and group, and the CSRF token (for example after a reload) |
| `DELETE` | `/v1/session` | Sign out: ends the session and clears the cookie |
| `POST` | `/v1/notifications/ingest` | Parse, categorize, and store a supported notification-like text payload |
| `POST` | `/v1/transactions` | Create a manual transaction |
| `POST` | `/v1/transactions/bulk` | Create multiple transactions from a structured payload |
| `POST` | `/v1/imports` | Import a spreadsheet export (CSV or XLSX), or preview it with `dry_run` |
| `GET` | `/v1/transactions` | List transactions accessible within the requested group |
| `GET` | `/v1/events` | List the group's events (one per purchase), each with its source records |
| `GET` | `/v1/events/{event_id}/decisions` | The event's decision history: links, reviews, answers and splits |
| `GET` | `/v1/matches/review` | List uncertain matches waiting for a member |
| `POST` | `/v1/matches/{decision_id}/confirm` | Confirm: the record joins the candidate event |
| `POST` | `/v1/matches/{decision_id}/reject` | Reject: the record stays separate and the pair is not proposed again |
| `POST` | `/v1/events/{event_id}/split` | Move one record out of an event (undo a wrong link) |
| `PUT` | `/v1/events/{event_id}/category` | Confirm or change the event's category; optionally teach the group's merchant memory |
| `PUT` | `/v1/events/{event_id}/mixed` | Mark the event as a purchase of several kinds (no amounts), or unmark it |
| `PUT` | `/v1/events/{event_id}/category-lines` | Split the amount into category lines, or remove the split |
| `PUT` | `/v1/events/{event_id}/transfer` | Mark the event as a transfer within the group, or undo it |
| `GET` | `/v1/events/{event_id}/category-changes` | The event's category change log |
| `POST` | `/v1/events/{event_id}/llm-suggestion` | Ask the language model about one uncertain event now |
| `GET` | `/v1/llm-settings` | W8: when the group's LLM run asks the model, and the month's spending |
| `PUT` | `/v1/llm-settings` | W8: an admin sets the LLM schedule and budget (web session only) |
| `GET` | `/v1/overview` | W2: a month's totals per currency, category and member over deduplicated events |
| `GET` | `/v1/members` | W8: the group's members and their roles |
| `PUT` | `/v1/members/{member_id}/role` | W8: an admin makes a member `admin` or `member` (web session only) |
| `GET` | `/v1/own-accounts` | W8: the group's own accounts and counterparties (records naming one are transfers) |
| `POST` | `/v1/own-accounts` | W8: add an account number or a name (admin) |
| `DELETE` | `/v1/own-accounts/{account_id}` | W8: delete an entry (admin; answers it as it was) |
| `GET` | `/v1/tokens` | W8: the signed-in member's API tokens in this group (web session only) |
| `POST` | `/v1/tokens` | W8: issue an API token, shown once (web session only) |
| `POST` | `/v1/tokens/{token_id}/revoke` | W8: revoke one of the member's own tokens (web session only) |
| `GET` | `/v1/merchant-rules` | W8: the group's merchant → category rules and the allowed categories |
| `POST` | `/v1/merchant-rules` | W8: add a rule (admin) |
| `PUT` | `/v1/merchant-rules/{rule_id}` | W8: change a rule's merchant or category (admin) |
| `DELETE` | `/v1/merchant-rules/{rule_id}` | W8: delete a rule (admin; answers it as it was) |

These endpoints describe the current prototype. They do not imply that direct Android or Google Sheets integrations are available.

### `POST /v1/session`

No token needed. `login` is the member's e-mail address (any case) or member id; `group_id` is needed only if the member belongs to several groups.

```json
{"login": "anna@example.com", "password": "...", "group_id": "lakas"}
```

Response `200` with the cookie `finsync_session` (`HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/v1`, 12 hours):

```json
{"user_id": "anna", "group_id": "lakas", "expires_at": "2026-11-13T09:00:00+00:00", "csrf_token": "3f9c..."}
```

`401` with one message for an unknown login, a member without a password and a wrong password; `400` without a `group_id` when the member is in several groups; `403` when the member is not in the named group. Passwords are set with `python -m finsync.api.passwords set --user <member> [--email <address>]`.

`GET /v1/session` returns the same body for a valid cookie (`401` otherwise). `DELETE /v1/session` needs the CSRF token, ends the session on the server and answers `204`.

### `POST /v1/notifications/ingest`

```json
{"message": "CARD PURCHASE -1234.56 HUF at Tesco on 2026-09-01 13:45"}
```

The Android app sends the notification text with its title, the phone's post time and, when the notification carries one, the bank's transaction number:

```json
{"message": "-4 990 Ft ... PELDABOLT KFT ...", "title": "...", "posted_at": "2026-11-12T09:15:00.123+00:00", "source_ref": "000000101", "device_zone": "Europe/Budapest"}
```

`posted_at` must be an ISO 8601 instant with an offset; it becomes `happened_at` ([ADR 0008](../architecture/decisions/0008-notification-time-and-calendar-day.md)). A format that prints no time (OTP Bank) needs it, otherwise `400`. `device_zone` is the phone's zone id at capture; it is optional, kept with the raw record for diagnosis only (travel abroad, a wrong phone clock) and never changes the time or the calendar day, and a value that does not look like a zone id is left out rather than refused. The other four fields together identify the notification, so sending the same one again (a retry) is answered with `exact_duplicate` and counted once, while two identical texts with different references or times are two purchases. A text that matches no supported format is `400`; the app then drops it and does not retry.

Response `201`: `{"transaction_id": 1, "event_id": 1, "match_outcome": "separate"}`. `match_outcome` is `separate`, `auto_linked`, `needs_review` or `exact_duplicate` ([matching design](../design/transaction-matching.md)). Supported formats are listed in [finsync/ingestion/README.md](../../finsync/ingestion/README.md).

### `POST /v1/transactions`

```json
{
  "amount": "-4990",
  "currency": "HUF",
  "description": "Monthly bus pass",
  "merchant": "BKK",
  "happened_at": "2026-09-05T07:00:00+00:00"
}
```

`merchant` is optional. `amount` must be non-zero, `currency` a 3-letter code, `happened_at` ISO 8601 (a time without an offset is Europe/Budapest time; a date without a time, such as `2026-09-05`, is stored as a day-precision value). Optional: `direction` (`expense` or `income`, sets the sign of `amount`) and `source_ref` (a stable client reference such as a sheet row id; resending the same row with the same reference is recognised as an exact duplicate). Response `201`: `{"transaction_id": 2, "event_id": 1, "match_outcome": "auto_linked"}`.

### `POST /v1/transactions/bulk`

```json
{"rows": [ { "amount": "-1000", "currency": "HUF", "description": "Taxi", "happened_at": "2026-09-06T10:00:00+00:00" } ]}
```

Each row has the same fields as a manual transaction. The import is atomic: if any row is invalid (for example a non-object row, a zero or non-finite amount), nothing is stored and the `400` error names the row (`Row 1: Amount cannot be zero`). All rows share one `import_batch_id`. Response `201`: `{"transaction_ids": [3], "results": [{"transaction_id": 3, "event_id": 2, "match_outcome": "separate"}]}`.

### `POST /v1/imports`

```json
{
  "content": "Könyvelés dátuma;Összeg;Közlemény;Partner;Tranzakció azonosító\n2026.09.05.;-4 500;Kártyás vásárlás;PELDABOLT KFT;000000101\n",
  "mapping": {"date": "Könyvelés dátuma", "amount": "Összeg", "description": "Közlemény",
              "merchant": "Partner", "reference": "Tranzakció azonosító"},
  "dry_run": true
}
```

Send exactly one of `content` and `xlsx_base64`. `content` is a CSV file as text; the client decodes it (for example from Windows-1250). `xlsx_base64` is an XLSX workbook encoded as base64; the server reads the first sheet, cell values only (a formula counts as its last saved result), and turns date and number cells into the same text a CSV would hold. Row numbers in errors are then the sheet's row numbers. A file that is not a readable workbook answers `400`. The delimiter (`,`, `;` or tab) is detected from the header. `mapping` names the file's columns, ignoring case; its defaults are FinSync's generic headers `date`, `amount`, `description`, `merchant`, `currency`, `reference`, and `default_currency` is `HUF`. `date`, `amount` and `description` are required; the others are used when the file has them. Amounts may use a space or a dot for thousands and a comma for decimals (`-4 500`, `-4.990,50`); dates are `2026-09-05` or `2026.09.05.` and are stored as calendar days (an export carries the booking date).

- `dry_run: true` answers `200` with every parsed row (`line`, `happened_on`, `amount`, `currency`, `description`, `merchant`, `reference`), every row error (`{"line": 3, "error": "invalid amount 'x'"}`) and `already_imported`; nothing is stored.
- Otherwise the whole file is imported or nothing is: one bad row answers `400` naming up to five lines, a file that was already imported (same content, whatever its line ends) answers `409`. Response `201`: `{"import_batch_id": "file-<sha256>", "already_imported": false, "rows": [...], "errors": [], "results": [{"transaction_id": 4, "event_id": 3, "match_outcome": "separate"}], "summary": {"separate": 1}}`.

Each row goes through matching as a `file_import` record of the member. The `reference` column, when the export has one, identifies the booking: a later, overlapping export repeats it, so known rows come back as `exact_duplicate` even if the description is worded differently. Without it, a row is identified by its values and by how many identical rows came before it in the file, so an overlapping export still adds only its new rows. A second identical row within one file gets its own event and goes to review against the first (`needs_review`): it may be a second purchase (two equal tickets) or an error in the export.

### `GET /v1/transactions`

Response `200`:

```json
{"transactions": [{
  "id": 1, "user_id": "demo-user", "group_id": "demo-group",
  "amount": "-1234.56", "currency": "HUF",
  "description": "card_purchase:Tesco", "merchant": "Tesco",
  "category": "groceries", "source": "android_notification",
  "happened_at": "2026-09-01T13:45:00+00:00", "happened_at_precision": "minute",
  "created_at": "...", "event_id": 1, "duplicate_of_id": null
}]}
```

### `GET /v1/events`

Response `200`: `{"events": [{"id": 1, "amount": "-1234.56", "currency": "HUF", "direction": "expense", "happened_at": "...", "merchant": "Tesco", "category": "groceries", "category_source": "dictionary", "category_confidence": "low", "uncertain": true, "mixed": false, "lines": [], "lines_match_amount": null, "remember_merchant": null, "category_agreement": null, "llm_due_at": null, "primary_transaction_id": 1, "review_state": "clear", "transactions": [ ... ]}]}`. Display values come from the primary record (a notification first, then the earliest). `review_state` is `needs_review` while an uncertain match waits for a member.

The category fields ([categorization design](../design/categorization.md#review-in-the-web-app)):

- `category_source`: who decided: `user` (a member; never overwritten by automation, also when records are linked or split later), `merchant_rule` (the group's rule), `dictionary` or `keyword` (the built-in Hungarian dictionary), `llm`, `own_account` (a transfer by the own-accounts list), `none`. `category_confidence` is `high` or `low`; `uncertain` is true for a `low` category no member settled on a spending event, the web app's "suggestion"; income is never uncertain and never sent to the model (author's decision, 2026-11-24).
- `mixed`, `lines`: see the correction routes below. `lines_match_amount` is `false` when the lines no longer add up to the amount (a record was split off after they were saved): the overview then counts the whole amount under `category` until a member fixes them.
- `remember_merchant`: the merchant name to offer "always use this for …" with; `null` when no rule may be learned (a merchant on the mixed-assortment list, a mixed or split event, a transfer).
- `category_agreement`: for an `llm` category, the share of the model's five answers that agreed. `llm_due_at`: when the group's scheduled run will ask the model, `null` when it will not.
- Every record in `transactions` has its own `category_source` and `category_confidence`.

### `PUT /v1/events/{event_id}/category`

```json
{"category": "clothing", "remember": false}
```

Confirms (same category) or changes the category; it becomes the member's decision (`user`, `high`). With `"remember": true`, the group's merchant memory learns it, only when the event's `remember_merchant` is set (otherwise `400` and nothing changes). Response `200`: `{"event": { ... }, "merchant_rule_outcome": null, "merchant_rule": null}`. With `remember`, `merchant_rule_outcome` is `created`, `confirmed` (the rule already said so; `times_confirmed` grows), `updated` (an admin changed the rule) or `kept` (the group's rule names another category; only an admin changes it, so the correction stays on the event). `409` for a transfer or an event split into lines.

### `PUT /v1/events/{event_id}/mixed`

`{"mixed": true}` marks the purchase as several kinds without amounts; the whole amount stays under `category` and the overview reports it in `mixed_amount`. Response `200`: the event. `409` for a transfer.

### `PUT /v1/events/{event_id}/category-lines`

```json
{"lines": [{"category": "groceries", "amount": "-9000"}, {"category": "clothing", "amount": "-3000"}]}
```

Two to 20 lines, each an allowed category once, each amount non-zero with the event's sign, adding up to the event's amount exactly (`400` with the reason otherwise). They replace the previous set as one logged change; `{"lines": []}` removes the split. The event's `category` becomes the category of the largest line, as the member's decision. The lines stay on the event when a record is split off. Response `200`: the event. `409` for a transfer.

### `PUT /v1/events/{event_id}/transfer`

`{"transfer": true}` gives the event and its records the direction and category `transfer` (left out of every total, never matched to a purchase); `false` gives the records the direction of their amount's sign again and the category the categorizer gives them, without the own-accounts list. Response `200`: the event. `409` when the event is split into lines.

### `GET /v1/events/{event_id}/category-changes`

Response `200`: `{"changes": [{"id": 1, "kind": "category", "old_value": {"category": "groceries", "source": "dictionary", "confidence": "low"}, "new_value": {"category": "clothing", "source": "user", "confidence": "high"}, "changed_by": "balint", "created_at": "..."}]}`, oldest first. `kind` is `category`, `mixed`, `lines` or `transfer`; a change that changes nothing is not logged.

### `POST /v1/events/{event_id}/llm-suggestion`

No body. Asks the language model about one uncertain event now, in every schedule mode. Only the primary record's merchant, description and amount are sent; the call is logged. At or above the measured threshold (0.40 share of five answers) the answer is settled (`llm`, `high`); below it the event keeps its suggestion, or gets the model's top answer as one, or becomes `uncategorized` ("Bizonytalan"). A member's decision made during the call wins. Response `200`: the event. `409` when the category is settled, the server has no model (`FINSYNC_ANTHROPIC_API_KEY` not set), or the group's monthly budget is used up.

### `GET /v1/llm-settings`, `PUT /v1/llm-settings`

```json
{"mode": "daily", "hours_after": 24, "run_time": "20:00", "weekday": 6, "monthly_budget_usd": "1.00"}
```

`mode` is `never` (default: nothing is sent), `after_arrival` (`hours_after` hours after the record arrived, 1 to 336), `daily` (at `run_time`, Budapest time) or `weekly` (on `weekday`, 0 = Monday, at `run_time`). Saving gives every uncertain event of the group its due time (`never` clears them); the server checks for due events every 5 minutes, group by group, while the month's spending stays below `monthly_budget_usd` (0 to 100). Every member reads the setting; only an admin changes it, and only from the web session. Response `200`: the setting with `spent_this_month_usd`, `budget_exhausted`, `available` (the server has a model), `model`, `updated_by`, `updated_at`. Design: [when the LLM is called](../design/categorization.md#when-the-llm-is-called-proposed-by-the-author-2026-11-19).

### `GET /v1/events/{event_id}/decisions`

Response `200`: `{"decisions": [{"id": 3, "transaction_id": 2, "candidate_event_id": 1, "outcome": "needs_review", "score": 0.8, "features": { ... }, "matcher_version": "...", "decided_by": "system", "supersedes_id": null, "superseded": true, "created_at": "..."}, {"id": 4, "outcome": "confirmed", "decided_by": "user-1", "supersedes_id": 3, "superseded": false, ...}]}`. Every decision that names the event as candidate or concerns one of its current records, oldest first. `decided_by` is `system` for the matcher, otherwise the member's id; `superseded` is true when a later decision answered or undid it. An event of another group returns `404`.

### `GET /v1/matches/review`

Response `200`: `{"reviews": [{"decision_id": 4, "score": 0.8, "features": {"a": 1.0, "t": 1.0, "m": 0.3333, "delta": "0d", "score": 0.8, "runner_up": null}, "transaction": { ... }, "candidate_event": { ... }}]}`. `features` explains the score: amount `a`, time `t`, merchant `m`; an identical manual row carries `identical_row_of_id` instead.

### `POST /v1/matches/{decision_id}/confirm` and `/reject`

No body. Response `200`: `{"transaction_id": 2, "event_id": 1, "match_outcome": "confirmed"}` (or `"rejected"`). The answer is written to the decision log with the member's id; answering the same decision again returns `409`.

### `POST /v1/events/{event_id}/split`

```json
{"transaction_id": 1}
```

Moves that record, with its re-deliveries, to a new event and logs a `split` decision. Response `200`: `{"transaction_id": 1, "event_id": 3, "match_outcome": "split"}`. Naming a re-delivery returns `400`, an event with a single record `409`.

Design: [matching design](../design/transaction-matching.md#user-flow-and-api).

### `GET /v1/overview`

Query: `month=YYYY-MM` (optional; without it, the current month in Budapest time). Response `200`:

```json
{
  "month": "2026-11",
  "months": ["2026-11", "2026-10"],
  "totals": [{"key": "all", "currency": "HUF", "expense": "241370", "income": "420000",
              "event_count": 9, "review_count": 1, "review_amount": "8200",
              "uncertain_count": 2, "uncertain_amount": "16200", "mixed_count": 1, "mixed_amount": "12000"}],
  "categories": [{"key": "housing_utilities", "currency": "HUF", "expense": "185000", "income": "0",
                  "event_count": 1, "review_count": 0, "review_amount": "0"}],
  "members": [{"key": "anna", "currency": "HUF", "expense": "31680", "income": "420000",
               "event_count": 5, "review_count": 0, "review_amount": "0"}],
  "transfer_count": 0
}
```

The rules ([`finsync/core/overview.py`](../../finsync/core/overview.py)):

- Sums are over **events**, so a purchase reported by a notification and a sheet row counts once.
- An event belongs to the Europe/Budapest calendar month of its primary record ([ADR 0008](../architecture/decisions/0008-notification-time-and-calendar-day.md)) and to the member whose primary record it is.
- `expense` and `income` are positive sums, never netted; every currency has its own rows.
- Events with the direction `transfer` are left out of every sum and only counted in `transfer_count`.
- Events waiting for review are **in** the sums and also counted in `review_count`, with their amount in `review_amount`: if the flagged record turns out to be the same purchase as another, the total is that much lower.
- An event split into category lines counts each line under its category in `categories`; any other event counts its whole amount under its category. Lines that no longer add up to the amount are ignored until fixed.
- On the month totals, `uncertain_count`/`uncertain_amount` are the events whose category is only a suggestion and `mixed_count`/`mixed_amount` the events marked mixed without lines: how much of the category split may be inaccurate. They are `0` on category and member rows.
- `months` lists the months that have events, newest first. A month in the wrong format returns `400`.

### `GET /v1/members`

Response `200`: `{"members": [{"user_id": "anna", "email": "anna@example.org", "role": "admin", "is_me": true}, {"user_id": "balint", "email": null, "role": "member", "is_me": false}]}`. `email` is the sign-in address, `null` for a member without a web password.

**Roles** (author's decision, 2026-11-19; Alembic revision 0003): an `admin` changes the group's settings (merchant rules, own accounts, roles), a `member` reads them and works with the group's data. The first member of a new group is its admin; members added later are `member`; members who existed before revision 0003 became admins. `python -m finsync.api.members add|list|set-role` manages members on the server.

### `PUT /v1/members/{member_id}/role`

`{"role": "admin"}` or `{"role": "member"}`, only by an admin and only with the web session cookie and the CSRF token: an API token gets `403`, even an admin's, so a leaked phone token cannot make anyone an admin (least privilege, [ADR 0012](../architecture/decisions/0012-no-multi-factor-authentication.md) point 6, since 2026-11-23). Returns the member list as `GET /v1/members` does. Demoting the group's last admin returns `409`; a member of another group returns `404`.

### `GET`, `POST /v1/own-accounts`, `DELETE /v1/own-accounts/{account_id}`

The group's own accounts and counterparties for transfers within the group ([categorization design](../design/categorization.md#money-transfers)). Every member reads the list; only an admin adds or deletes entries.

`POST` takes `{"label": "12345678-87654321"}` or `{"label": "MINTA ANNA"}` and returns `201` with `{"id": 1, "label": "...", "kind": "account", "match_key": "1234567887654321", "created_by": "anna", "created_at": "..."}`. A label with at least 8 digits is an `account`, matched when its digits appear in a record's merchant and description digits; anything else is a `name`, matched when all its words are words of the merchant or description. A new record that matches gets `direction` and `category` `transfer`: matching never links it to a purchase, and `GET /v1/overview` leaves it out of the sums. The list applies to records stored after the entry. The same entry twice returns `409`, a label with neither a word nor 8 digits `400`.

### `GET /v1/tokens`, `POST /v1/tokens`, `POST /v1/tokens/{token_id}/revoke`

Only with the web session cookie (and the CSRF token for the two `POST`s). An API token gets `403`, so a leaked phone token cannot issue new tokens or revoke the member's others. A member sees and revokes only their own tokens in the session's group.

`POST /v1/tokens` with `{"name": "Anna phone"}` (1–80 characters) returns `201`:

```json
{"token": "fs_...", "record": {"id": 4, "name": "Anna phone", "prefix": "fs_m2PNP", "created_at": "...", "last_used_at": null, "revoked_at": null}}
```

`token` appears only in this answer; only its SHA-256 hash is stored ([ADR 0009](../architecture/decisions/0009-api-tokens.md)). `GET /v1/tokens` returns `{"tokens": [<record>, ...]}`, newest first. Revoking returns the record with `revoked_at` set (revoking again returns it unchanged); another member's token, or one in another group, returns `404`.

### `GET`, `POST /v1/merchant-rules`, `PUT`, `DELETE /v1/merchant-rules/{rule_id}`

The group's merchant → category rules, the first layer of the hybrid categorizer ([categorization design](../design/categorization.md#order-of-precedence)). Every member reads them; only an admin creates, changes or deletes them (`403` otherwise).

`POST` and `PUT` take `{"merchant": "SPAR", "category": "groceries"}`. The category must be one of the nine allowed categories; `GET` lists them next to the rules: `{"rules": [{"id": 1, "merchant": "SPAR", "merchant_key": "spar", "category": "groceries", "created_by": "anna", "created_at": "...", "updated_at": "..."}], "categories": ["groceries", "eating_out", ...]}`.

`merchant_key` is what is matched: the merchant's words, lowercase and without accents, store numbers and company suffixes ("Spar 0123 Kft." → `spar`). A rule applies to a new record when every word of its key is a word of the record's merchant (or, without one, of its description); with several, the one with more words wins. A second rule with the same key returns `409`. A rule changes only records stored after it, not existing events.
