# Family pilot readiness (closed use on family members' phones)

- Written: 2026-11-24
- Owner: Bence Varga
- Status: **proposed** (assessment and plan; nothing in it is built yet)

The author asked when FinSync can be installed on family members' phones for closed, real use, and said that a proper, complete end-user licence agreement (EULA) must exist first. This page records what is missing, an honest estimate, and the order of work. It does not move any course deadline: the M2 package still goes out on **2026-11-27** and M2 closes on **2026-12-04** (M2 closing schedule in PR #38).

## Estimate

| Step | Earliest | Condition |
| --- | --- | --- |
| Legal drafts (EULA, privacy notice) | 2026-11-24 (this session, drafts) | The author reads them and fills the placeholders; a lawyer's review is recommended ([legal/](../legal/README.md)) |
| Blockers B1–B7 built and checked | **2026-12-19** (Sat) | Built on the December work days next to the planned security and privacy evaluation (Dec 7–13), which covers several of them; nothing of M2 moves |
| Pilot start: the author plus one family member | **2026-12-19 – 12-20** | All blockers closed, both documents accepted |
| Rest of the family | **2026-12-21 – 2027-01-03** (holidays) | One week without incidents; installation in person |
| Fallback if December runs over | **2027-01-16** (after M3) | M3 (due 2027-01-15) has priority over the pilot |

The estimate assumes two work sessions a week in December (Friday and Saturday) and about four sessions of pilot work in total. It is a guess, not a commitment; the hosting decision (B1: EU VPS) was made on 2026-11-24, so the remaining unknown is the provider set-up.

## What exists today (2026-11-24)

- Server: FastAPI on PostgreSQL or SQLite, per-member API tokens (hashed), web sign-in with scrypt passwords, `Secure` session cookie and CSRF token, group isolation tested on every endpoint, admin/member roles, request size limits ([security and privacy](../architecture/security-and-privacy.md)).
- Android: the notification-listener spike app with OTP Bank forwarding, outbox and retry, tested on the emulator and with one real purchase on the author's phone ([spike findings](../design/android-notification-spike.md)).
- LLM categorization: off by default per group; when on, only one record's merchant, description and amount go to the Anthropic API (PR #40, [ADR 0011](../architecture/decisions/0011-llm-categorization-layer.md)).
- Reachability: the API runs locally and is exposed only through a temporary HTTPS tunnel for tests and the demo ([ADR 0007](../architecture/decisions/0007-how-external-clients-reach-the-api.md)).

## Blockers (must be closed before any family member installs the app)

| # | Blocker | Why | Work |
| --- | --- | --- | --- |
| B1 | **Always-on hosting with HTTPS** | Today the API runs only while the author's computer and a tunnel are up. Family phones need a stable address. The Android outbox survives outages, but the web app does not. | **Decided (author, 2026-11-24): a small VPS in the EU** with Caddy for HTTPS (no tunnel). Provider: **Hetzner** for now (author, 2026-11-24), with a to-do: **compare the options again before the VPS is deployed** (Hetzner, OVHcloud, Scaleway, AWS Lightsail in Frankfurt: current prices, data-centre country, data-processing agreement, US access for a US company). Post-quantum key exchange is not a criterion between them, because TLS ends in Caddy on the VPS; a Caddy built with a recent Go uses hybrid X25519MLKEM768 with browsers on any provider (whether the Android client negotiates it is to be checked). The provider becomes a processor in the privacy notice and needs a data-processing agreement. On it: PostgreSQL, secrets outside the repository, daily encrypted backups with one tested restore, a separate database from development and evaluation. The hosting location goes into the privacy notice. |
| B2 | **Family build of the Android app** | The spike app keeps a full capture log (`captures.jsonl`, full notification text) and has an **Export** button; the token is stored unencrypted; the build is debug-signed. | A release build signed with the author's own key (key kept outside the repository, with a backup); capture log and Export removed or disabled in release builds; token in the Android Keystore (EncryptedSharedPreferences); a first-start screen with links to the EULA and the privacy notice before notification access is requested; a version number shown in the app. Distribution: the signed APK installed in person (sideloading); Google Play is not needed for a closed circle. |
| B3 | **Accounts for real people** | Members are added on the command line and passwords are set by the author; there is no password change and no limit on failed sign-ins. | A member changes their own password; failed sign-in limit (already a December security-evaluation item, [ADR 0010](../architecture/decisions/0010-web-sign-in.md)); a one-time initial password handed over in person. |
| B4 | **Data-subject rights and retention** | The notice promises access, export and erasure; today none has a feature, and the decision log is append-only. | An admin command that exports one member's data (JSON/CSV) and one that erases a member's records and pseudonymises their entries in the log; a retention rule for raw notification payloads (proposal: 12 months, then the raw text is cleared and the parsed fields stay); documented in the notice. |
| B5 | **LLM boundary for real data** | Real merchant names and descriptions would leave the server. | The family group's schedule stays `never` unless every member agreed in the privacy notice's opt-in; Anthropic's commercial terms and data-processing terms checked and linked in the notice; the monthly cost cap set. |
| B6 | **EULA and privacy notice accepted** | The author's condition. | Drafts in [legal/](../legal/README.md); the author fills the placeholders, ideally a lawyer reviews them, and each family member accepts them before installation (signed paper or a dated e-mail reply). |
| B7 | **Thesis data separation** | Real family data must never enter the measurements, the repository or an AI session ([bank-notification-privacy skill](../../.claude/skills/bank-notification-privacy/SKILL.md), [dev-test-evaluation skill](../../.claude/skills/dev-test-evaluation/SKILL.md)). | The pilot database is separate; the thesis reports only synthetic data; the supervisor is told about the pilot in the next status e-mail, only as "a closed family test started", without data. |

## Should be done, but not blocking a closed pilot

- **Multi-factor authentication.** [ADR 0012](../architecture/decisions/0012-no-multi-factor-authentication.md) names TOTP or passkeys as the step before FinSync holds real households' data *outside a test setting* and says the decision is revisited if FinSync is used with real households. A closed, time-limited family pilot is treated here as a test setting; if the pilot turns into permanent use, MFA comes first. This is an author decision to confirm.
- **Step-up re-authentication** before issuing a token or changing a role (ADR 0012's proposed next step).
- **Other banks.** Only OTP Bank notifications are forwarded; family members with another bank can use manual entry or file import.
- **Monitoring.** A simple health check and an alert when backups fail.
- **Forgotten password by e-mail** (roadmap future work); until then the author resets passwords.

## Out of scope for the pilot

Google Play publication, payments, a direct bank connection, use outside the family.

## Legal note

The GDPR does not apply to processing "by a natural person in the course of a purely personal or household activity" (GDPR Art. 2(2)(c)). A family-only installation run by the author privately may fall under this exemption, but whether it does depends on the facts (for example the link to the university thesis, or a server rented from a company). The privacy notice is drafted as if the GDPR applied, because that is the safe side and because the family should know what happens to their data either way. None of this is legal advice; see [legal/](../legal/README.md).
