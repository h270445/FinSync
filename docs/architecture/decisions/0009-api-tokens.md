# 0009. API tokens: one member, one group, stored as a hash

- Status: Proposed
- Date: 2026-11-02

## Context

Until now the API took the caller's identity from the `X-User-Id` and `X-Group-Id` headers, which any client can set. The tunnel of [ADR 0007](0007-how-external-clients-reach-the-api.md) must not be opened before requests are authenticated, and the M2 milestone requires that client-supplied identity headers are no longer trusted and that every endpoint has a cross-group test.

The [technology stack](../technology-stack.md#backend) plans Argon2-hashed API tokens for the Android app and the Sheets script, and password login with a session cookie for the web app. The backend is still the standard library ([ADR 0002](0002-python-stdlib-and-sqlite.md)); Argon2 is not in it.

Each client (one phone, one spreadsheet) acts for one person in one household group.

## Decision

1. **A token belongs to one member of one group.** The request's user and group come from the token alone; `X-User-Id` and `X-Group-Id` are ignored. A member who needs another group gets another token.
2. **Format:** `fs_` followed by 32 random bytes from `secrets` in URL-safe base64 (43 characters). The prefix makes a leaked token easy to recognise in logs and secret scanners.
3. **Only the SHA-256 hash is stored**, with the first 8 characters for display, a name ("Anna phone"), creation time, last use and revocation time. The token is shown once, when created.
4. **Header:** `Authorization: Bearer <token>`. A missing, malformed, unknown or revoked token gets `401` with `WWW-Authenticate: Bearer`; a valid token whose member has left the group gets `403`, because every use case still checks membership.
5. **Issuing** is a command-line tool (`python -m finsync.api.tokens create|list|revoke`) until the web app's token screen exists.

SHA-256 instead of Argon2: a slow password hash protects low-entropy secrets that a person chose. A 256-bit random token cannot be guessed from its hash, so a fast hash gives the same protection and allows a direct lookup by hash. GitHub and other API providers store tokens the same way. Argon2 remains the plan for web passwords.

## Consequences

- No client can read or write another group's data by changing a header; the cross-group tests in `tests/test_auth.py` call every endpoint with another group's token and check that group 1 is unchanged.
- Revoking a token, or removing the member from the group, stops the client at once, without touching other tokens.
- Each request updates the token's last use, one extra write per request; acceptable for the prototype.
- The web app needs a second way in (password and session cookie with CSRF protection, M2); both resolve to the same member and group checks.
- The tunnel may now be opened for tests and the demo, once request size limits are also in place (ADR 0007).
