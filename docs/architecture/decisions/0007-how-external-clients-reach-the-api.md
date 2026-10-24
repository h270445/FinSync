# 0007. How the Google Sheets script and the Android app reach the API

- Status: Proposed
- Date: 2026-10-24

## Context

The Google Sheets script runs on Google's servers (Apps Script `UrlFetchApp`), not on the author's machine, so it can only call an API that is reachable from the public internet over HTTPS. The Android app has the same need as soon as the phone is not on the same Wi-Fi as the development machine (mobile data, a demo elsewhere). The API runs locally (`docker compose up`, SQLite fallback until M2), and the project has no budget or need for permanent hosting this semester. The Sheets script is conditional ([roadmap](../../planning/roadmap.md#semester-scope)); the Android app (one bank format) is committed for M2.

Options considered:

| Option | For | Against |
| --- | --- | --- |
| **A. HTTPS tunnel to the local API** (for example Cloudflare Tunnel or ngrok) | No server to run or pay for; real HTTPS; both clients use the same URL; can be started only for tests and the demo | URL may change between runs (quick tunnels) unless a named tunnel is set up; the API is public while the tunnel runs, so token authentication must be in place first |
| **B. Small hosted server** (VPS with Caddy, as in the [technology stack](../technology-stack.md)) | Stable URL; closest to a real deployment | Cost, operating work and a second environment to keep in sync; not needed for the thesis claims |
| **C. Server pulls from the sheet** (Google Sheets API with a service account) | Nothing is exposed; no script in the sheet | A second, Google-specific credential and code path; the server must poll; does not help the Android app |
| **D. Local network only** | Simplest for development | Sheets script cannot work at all; Android works only on the same Wi-Fi |

## Decision

- Clients reach the API through **an HTTPS tunnel to the locally running API** (option A), started only for client tests and the demo. During day-to-day Android development the phone may use the local network address (option D).
- The tunnel is started only after **per-user API tokens** are implemented (M2, Nov 2–8); until then no client is exposed to the internet.
- The base URL is configuration, not code: a setting in the Android app's setup screen and a Script Property in the Sheets script, next to the token.
- Hosting (option B) is revisited only if a reviewer needs a permanently running instance.

## Consequences

- No hosting cost or second environment this semester; the demo needs one extra command, documented in the setup guide.
- If a quick tunnel is used, its URL changes on every start, so the Sheets script and the Android app must be re-pointed; a named tunnel avoids this.
- While the tunnel runs, the API is on the public internet: token authentication, request size limits and the cross-group tests (M2) are prerequisites, not follow-ups.
- The Sheets script keeps the push model of the [technology stack](../technology-stack.md#google-sheets-optional-this-semester) (`POST /v1/transactions/bulk` with a token); no Google credentials are stored on the server.
