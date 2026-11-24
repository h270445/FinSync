# Security and privacy

Security and privacy are treated as a separate design and evaluation area because the application handles sensitive financial information.

## Planned areas of investigation

* Authentication and authorization, including attempts to access another group's data.
* Server-side input validation and handling of malformed requests.
* Data minimization and limiting access to information required for a given operation.
* Protection of credentials and other secrets.
* Traceability of relevant operations and data changes.
* Restricting AI components to explicitly authorized operations and treating their outputs as untrusted input.

Privacy requirements will be considered during design, with GDPR principles such as data minimization and appropriate access and retention controls taken into account where applicable. Compliance will not be claimed solely because these measures are implemented; applicable legal requirements must be assessed against the final system and its intended use.

## Current state

| Control | Status |
| --- | --- |
| Group membership check on every use case | Implemented |
| Roles within a group | Implemented (2026-11-19): `admin` or `member` per membership; group settings (merchant rules, own accounts, roles) change only by an admin, and the last admin cannot be demoted. Role changes only from a web session (2026-11-23, least privilege below) |
| Parameterised SQL | Implemented |
| Server-side validation of manual input | Implemented (amount, currency, description, timestamp) |
| Authentication | Implemented: per-member API tokens stored as SHA-256 hashes ([ADR 0009](decisions/0009-api-tokens.md)); web sign-in with e-mail or member id and a scrypt-hashed password, an HttpOnly `Secure` `SameSite=Strict` session cookie and a CSRF token on every change ([ADR 0010](decisions/0010-web-sign-in.md)). Client identity headers are ignored. Tokens are issued and revoked on the W8 screen only from a web session: an API token cannot manage tokens, so a leaked phone token cannot issue new ones or revoke the member's others; a member sees only their own tokens. Role changes are also web-session only (least privilege, [ADR 0012](decisions/0012-no-multi-factor-authentication.md) point 6). No limit on failed sign-in attempts yet. |
| Least privilege for API tokens | Implemented (2026-11-23, supervisor's rule): every action that widens access (issuing or revoking API tokens, changing a member's role, and any later invite or credential change) works only from a signed-in web session, never with a long-lived phone or Sheets token; an API token gets `403` even when it belongs to an admin. A compromised phone token is limited to one member's data in one group ([ADR 0012](decisions/0012-no-multi-factor-authentication.md) point 6) |
| Multi-factor authentication | Not in the thesis scope ([ADR 0012](decisions/0012-no-multi-factor-authentication.md), Accepted 2026-11-23): the data is spending information without a payment function. Step-up re-authentication for issuing tokens and changing roles is proposed as the next step; TOTP or passkeys are future work |
| Personal data | Member ids, group ids and, for sign-in, an e-mail address per member; the group's own account numbers and counterparty names for transfer detection (entered by an admin, visible to the group's members); passwords only as salted hashes, tokens and sessions only as SHA-256 hashes |
| Request size limits | Implemented: 64 KiB per `POST` or `PUT` request, 1 MiB for bulk import, 413 above it; the bytes that arrive are counted, so chunked bodies cannot bypass it |
| Audit trail | Planned through `match_decisions` |

## Rules

- All initial development and evaluation use synthetic test data.
- Banking credentials are never collected or stored; only notification text or user-entered data.
- An LLM component never gets direct database access; it receives only the fields it needs and its output is validated before use. The categorization layer ([ADR 0011](decisions/0011-llm-categorization-layer.md)) sends one record's merchant, description and amount, uses a JSON schema with the allowed categories plus `unknown`, and treats any other answer as `unknown`; the measurement uses synthetic data only.
- The outbound model call is optional and off by default. Wired into the live flow on 2026-11-24 ([`finsync/core/llm_schedule.py`](../../finsync/core/llm_schedule.py)): the server has a model only when `FINSYNC_ANTHROPIC_API_KEY` is set; a group's schedule is `never` until an admin changes it from the web session (an API token gets 403, the same least-privilege rule as roles); a member may ask about one event; a monthly budget per group stops the calls; every call is logged in `llm_calls` (who asked, which event, tokens, cost); a person's category always wins, also when it is made during a call. It is the only place where FinSync data leaves the server, and the same data-minimization rule applies: one record's merchant, description and amount, never member ids, e-mail addresses, account numbers, counterparty names or other records. A local OpenAI-compatible model behind the same interface keeps the data on the server. Design views [5](design-views.md#5-layered-architecture) and [6](design-views.md#6-security-authentication-and-group-isolation) show this boundary once the wiring exists (supervisor, 2026-11-23).

How these properties are tested is in [evaluation-plan.md](../evaluation/evaluation-plan.md#3-security-and-privacy).
