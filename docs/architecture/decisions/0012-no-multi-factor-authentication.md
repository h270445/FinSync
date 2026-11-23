# 0012. No multi-factor authentication in the thesis scope; step-up re-authentication as the next step

- Status: Accepted (proposed 2026-11-19 at the author's request; approved by the supervisor on 2026-11-23, who added the least-privilege rule in point 6)
- Date: 2026-11-19, amended 2026-11-23

## Context

FinSync keeps a household group's spending: amounts, merchants, times, categories, the group's own account numbers and counterparty names for transfer detection, and an e-mail address per member ([security and privacy](../security-and-privacy.md)). The author asked whether this data is sensitive enough to justify multi-factor authentication (MFA), or whether it falls outside the scope of the thesis.

What exists today (checked in the code on 2026-11-19):

- **Web app:** one factor, a password ([ADR 0010](0010-web-sign-in.md)). Sign-in takes an e-mail address or member id and a password, stored as salted scrypt; the session is an `HttpOnly`, `Secure`, `SameSite=Strict` cookie for 12 hours, with a CSRF token on every change. There is no limit on failed sign-in attempts yet, and passwords are set with a command-line tool (`python -m finsync.api.passwords`), not in the web app.
- **Android app and Sheets script:** a per-member, per-group API token stored as a SHA-256 hash ([ADR 0009](0009-api-tokens.md)). Tokens are issued and revoked on the W8 screen only from a web session; an API token gets `403` on `/v1/tokens`, so a leaked phone token cannot issue new tokens or revoke the member's others.
- **Roles:** an admin changes group settings (merchant rules, own accounts, roles). On 2026-11-19 `PUT /v1/members/{member_id}/role` accepted either a web session or an admin's API token; since 2026-11-23 it accepts only the web session (point 6).

What an attacker gains with a member's credentials:

- Read access to the group's spending history and the personal data above: a privacy harm, and a GDPR personal-data breach if it happens in real use.
- The ability to add, confirm, reject or recategorise records, which corrupts the group's figures.
- **No movement of money.** FinSync never holds bank credentials and has no payment function; it only reads bank notification text or data a member enters. A takeover therefore cannot cause a direct financial loss, which is the main reason banks require strong customer authentication (PSD2).

The thesis is about accurate, explainable spending tracking (the main contribution is transaction matching, [ADR 0004](0004-event-based-transaction-matching.md)). The prototype runs locally or behind a temporary tunnel for tests and the demo ([ADR 0007](0007-how-external-clients-reach-the-api.md)), with synthetic data only.

## Decision

1. **No full MFA in the thesis scope.** Neither TOTP (authenticator app codes) nor passkeys (WebAuthn) are built. Both need enrolment, recovery codes and a lost-device process, plus their own tests and UI, which is several days of work outside the thesis's contribution, while the data at risk is read-only spending information without a payment function.
2. **MFA would not protect the phone anyway.** The Android app and the Sheets script authenticate with a long-lived API token, not a sign-in. MFA would guard only the web sign-in and the screens behind it, and those are already the only place where tokens can be issued.
3. **Cheaper controls come first.** The weaknesses that matter more than a missing second factor are listed in ADR 0010 and the security evaluation: no limit on failed sign-in attempts, and no e-mail verification of addresses. A per-login attempt limit belongs to the December security evaluation.
4. **Proposed next step, not implemented now: step-up re-authentication.** Sensitive actions would ask the member to re-enter their password (or, once e-mail sending exists, a fresh one-time code sent by e-mail) if the session's last authentication is older than a few minutes. Candidates:
   - issuing an API token (`POST /v1/tokens`);
   - changing a member's role (`PUT /v1/members/{member_id}/role`), which accepts only the web session since 2026-11-23 (point 6);
   - later, changing the password or e-mail address once the settings screen does it.

   This targets the actions that widen access (a new long-lived token, a new admin), costs one timestamp on the session and one check per such route, and is a common pattern (GitHub's "sudo mode"). It is built only if the author asks for it.
5. **Full MFA is future work.** The thesis's "Limitations and future work" names TOTP or passkeys for the web sign-in as the step to take before FinSync holds real households' data outside a test setting.
6. **Least privilege: actions that widen access work only from a web session** (supervisor, 2026-11-23). Every admin action that widens anyone's access is allowed only from a signed-in web session, never with a long-lived API token from the phone or the Sheets script. Today these are:
   - issuing, listing and revoking API tokens (`/v1/tokens`, since 2026-11-19);
   - changing a member's role (`PUT /v1/members/{member_id}/role`, since 2026-11-23).

   An API token gets `403` on them, even an admin's (`require_web_session` in `finsync/core/auth.py`, tests in `tests/test_tokens_api.py`). Any future action of this kind (inviting a member, changing the password or e-mail address) follows the same rule. Group settings that do not widen access (merchant rules, own accounts) stay available to an admin's token, because they change only how the group's data is labelled. With this rule a compromised phone token is limited, by design, to the data of one member in one group: it cannot create further credentials or raise any member's role.

## Consequences

- One factor protects the web sign-in. A stolen or guessed password gives full access to that member's groups until the password is changed (which ends the member's sessions) or the session expires. scrypt slows offline guessing; online guessing is slowed only by the scrypt check per attempt until the attempt limit exists.
- A stolen API token still gives read and write access to the member's data in one group, but cannot issue more tokens or change any role, even when it belongs to an admin; revoking it stops it at once ([ADR 0009](0009-api-tokens.md)).
- Step-up re-authentication (point 4) and the attempt limit remain the next steps; they would apply to the same web-session-only routes as point 6.
- The decision is recorded in [security and privacy](../security-and-privacy.md) and in the thesis map, so the defence question "why no MFA?" has a written answer.
- If FinSync later gains a payment, export or bank-connection feature, or is used with real households outside a test setting, this decision must be revisited, because the harm of a takeover then grows.
