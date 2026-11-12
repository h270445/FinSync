# 0010. Web sign-in: e-mail or member id, scrypt password hash, HttpOnly session cookie

- Status: Proposed
- Date: 2026-11-12

## Context

M2 requires password login for the web app, with a secure session cookie and CSRF protection, next to the API tokens of the Android app ([ADR 0009](0009-api-tokens.md)). Until now the web app took an API token pasted into the sign-in page and kept it in `sessionStorage`, which is acceptable only for development: a browser must not keep a long-lived secret where scripts can read it ([technology stack](../technology-stack.md)).

The [technology stack](../technology-stack.md) planned Argon2 for passwords and a `SameSite=Lax` cookie with an `Origin` check and a double-submit CSRF token. Argon2 is not in the Python standard library and would be a new dependency. Members are identified by a member id (`anna`); the [UI design](../../design/user-interface.md) planned e-mail sign-in. The author decided on 2026-11-12 that members have an e-mail address, because later features such as a forgotten-password e-mail need it, and that the same sign-in field also accepts the member id.

## Decision

1. **Sign-in name:** one field takes the member's e-mail address or member id. A value with `@` is looked up as an e-mail address (stored in lower case, unique per member); anything else as a member id. A member id therefore cannot contain `@`.
2. **Password storage:** salted scrypt from the standard library (`hashlib.scrypt`), with N=2^14, r=8, p=5, one of the settings in the OWASP Password Storage Cheat Sheet, about 0.2 s per check. The parameters are stored with each hash, so they can be raised later without breaking old hashes. Passwords are 10 to 256 characters. Setting a new password ends the member's open sessions.
3. **Same answer for every failure:** an unknown login, a member without a password and a wrong password all get `401` with the same message, and an unknown login still runs one scrypt check, so the answer time does not reveal whether a member exists.
4. **Session:** `POST /v1/session` opens a session for one member of one group, like a token. The member names the group only if they belong to several (otherwise `400`). The session secret (`fss_` plus 32 random bytes) goes only into the `finsync_session` cookie: `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/v1`, 12 hours. Only its SHA-256 hash is stored (as for tokens, a 256-bit random secret needs no slow hash). `DELETE /v1/session` ends the session on the server.
5. **CSRF:** every state-changing request made with the cookie must send the session's CSRF token in `X-CSRF-Token`; otherwise `403`, and nothing is written. The token is derived from the session secret (`sha256("csrf:" + secret)`), returned by `POST` and `GET /v1/session`, and kept in memory by the web app. A page on another site can neither read it nor send the cookie (`SameSite=Strict`), so the check has two independent layers. The `Origin` check of the earlier plan is left out because these two layers already cover it.
6. **Both ways in, one check:** the data endpoints accept either a bearer token or the session cookie. A token wins if both are present. Both resolve to a member and a group, and every use case still checks membership, so a member who leaves the group gets `403` with either.
7. **Managing passwords:** a command-line tool, `python -m finsync.api.passwords set --user <member> [--email <address>]`, until the settings screen (W8) exists.

## Consequences

- The web app holds no secret in JavaScript-readable storage. After a reload it asks `GET /v1/session` whether the cookie is still valid. Any `401` returns the member to the sign-in page.
- The `Secure` cookie needs HTTPS or `localhost`. The Vite dev server on `localhost` works; opening the dev server by a LAN address over plain HTTP does not.
- E-mail addresses are new personal data. They are stored only for signing in, and the data-minimisation review (December) covers them. No e-mail is sent yet, so forgotten-password and address verification are future work.
- No limit on failed sign-in attempts yet. scrypt makes each guess slow, and the prototype runs locally or behind a temporary tunnel ([ADR 0007](0007-how-external-clients-reach-the-api.md)). A per-login attempt limit belongs to the security evaluation.
- The tests use a cheaper scrypt setting to keep the suite fast, and one test checks that the production setting is stored with each hash.
- Switching groups means signing out and in again; a group switcher can come with W8.
