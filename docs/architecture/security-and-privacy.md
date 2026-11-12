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
| Parameterised SQL | Implemented |
| Server-side validation of manual input | Implemented (amount, currency, description, timestamp) |
| Authentication | Implemented: per-member API tokens stored as SHA-256 hashes ([ADR 0009](decisions/0009-api-tokens.md)); web sign-in with e-mail or member id and a scrypt-hashed password, an HttpOnly `Secure` `SameSite=Strict` session cookie and a CSRF token on every change ([ADR 0010](decisions/0010-web-sign-in.md)). Client identity headers are ignored. No limit on failed sign-in attempts yet. |
| Personal data | Member ids, group ids and, for sign-in, an e-mail address per member; passwords only as salted hashes, tokens and sessions only as SHA-256 hashes |
| Request size limits | Implemented: 64 KiB per request, 1 MiB for bulk import, 413 above it; the bytes that arrive are counted, so chunked bodies cannot bypass it |
| Audit trail | Planned through `match_decisions` |

## Rules

- All initial development and evaluation use synthetic test data.
- Banking credentials are never collected or stored; only notification text or user-entered data.
- An LLM component never gets direct database access; it receives only the fields it needs and its output is validated before use.

How these properties are tested is in [evaluation-plan.md](../evaluation/evaluation-plan.md#3-security-and-privacy).
