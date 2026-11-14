# `clients/android/` — notification-listener spike

A throwaway Android app (Kotlin, Jetpack Compose) that answers the open questions about reading banking notifications on a real device before the M2 Android app is built ([roadmap](../../docs/planning/roadmap.md), Oct 19–25 side track). It logs bank notifications on the phone and, since 2026-11-12, forwards OTP Bank transactions to the FinSync API (see [Forwarding](#forwarding-to-finsync-m2-otp-bank)).

Findings go in [docs/design/android-notification-spike.md](../../docs/design/android-notification-spike.md).

## What it records

The spike watches only the bank apps listed in [`BankApps.kt`](app/src/main/java/hu/finsync/spike/BankApps.kt), matched by package name (the `id=` in the app's Play Store link):

| App | Package |
| --- | --- |
| OTP Bank | `hu.otpbank.mobile` |
| Revolut | `com.revolut.revolut` |
| K&H | `hu.kh.smartbanking` (added 2026-10-27) |

Debug builds also watch `com.android.shell`, the sender of notifications posted with adb, so simulated bank text can be tested without a purchase (see below). Release builds never do. Every record carries `simulated: true` unless it came from a bank app.

Android delivers every notification to a listener; the spike drops anything from another app before reading its content, so nothing about other apps is stored, not even their names.

| Data | Where | Content |
| --- | --- | --- |
| Notifications of the watched bank apps that look like transactions (an amount with a currency), and the app's own test notifications | `captures.jsonl` in app-private storage | package, key, id, tag, `postTime`, `when`, channel, category, group-summary and ongoing flags, title, text, big text, sub text, ticker, group key, group, sort key; every extra under its own key (text values in full, for example InboxStyle lines and MessagingStyle messages; icons and other objects by type name only); device time and time zone |
| Other bank notifications (marketing, news) | `captures.jsonl`, `kind: "other"` | channel, category, extras keys and masked texts only (letters `a`/`A`, digits `9`); key as a hash |
| Removed notifications | `captures.jsonl` | key hash and removal reason (click, user dismissed, app cancelled, ...) |
| Listener connect and disconnect | `captures.jsonl` | type and device time; on connect, every watched notification still in the shade is recorded as `active_on_connect`, so posts missed while the listener was down are not lost |

Nothing leaves the phone unless **Export** is pressed. Exported data contains real personal data and is **never committed**: only anonymised format descriptions (made-up amounts, merchants and names) go into the repository.

## Target device

Samsung Galaxy A13 on Android 14 / One UI 6.1 (`compileSdk` and `targetSdk` 36, `minSdk` 26). Samsung's battery management may stop background listeners: if records stop arriving, add the app under *Settings → Battery → Background usage limits → Never sleeping apps* and note it in the findings.

## Running it

1. Install [Android Studio](https://developer.android.com/studio) (it brings the SDK), open `clients/android/` and let Gradle sync. Gradle 8.11.1 runs on JDK 17–23, not on the JDK 25 bundled with recent Android Studio versions: from the command line set `JAVA_HOME` to such a JDK (for example one downloaded in Android Studio under *Settings → Build Tools → Gradle → Gradle JDK*). The first `gradlew assembleDebug` downloads Gradle and the SDK platform and took about 13 minutes.
2. **Emulator first:** create a virtual device with the latest Android image and press **Run**. Press **Access**, allow notification access for *FinSync notification spike*, then **Test**: a notification in the FinSync format appears and is logged. This checks the listener without a bank app.
3. **Real phone:** enable developer options and USB debugging on the Samsung, connect it and press **Run** with the phone selected. Repeat the access step. The bank apps only produce real notifications on the phone where the accounts are signed in, so questions 1–6 of the findings are answered here, not on the emulator.
4. The main screen shows whether OTP and Revolut are installed and how many of their notifications were captured. Make a few small card purchases; also try a phone restart and a day with the app closed.
5. **Export** shares a snapshot of the log as a `captures.jsonl` file (through a FileProvider, so long logs do not hit the intent size limit); anonymise it before pasting anything into the findings document.

## Simulated bank notifications (debug builds)

With the emulator or the phone connected, post any text; it is captured as `simulated`:

```bash
adb shell cmd notification post -t "OTP Bank" sim-1 "Kártyás vásárlás: -4 500 HUF, Teszt Bolt, 2026.10.24 13:45"
adb shell cmd notification post -S bigtext -t "Revolut" sim-2 "Paid 4 500 HUF at Test Shop"
```

On Windows (PowerShell) pass the whole command as one string, otherwise the quotes are split:

```powershell
adb shell "cmd notification post -t 'OTP Bank' sim-1 'Kartyas vasarlas: -4500 HUF, Teszt Bolt'"
```

`adb shell cmd notification help` lists the other styles (`-S inbox`, `-S messaging`) and their options. The parser must ignore group summaries (`group_summary: true`, no text), which Android adds on its own.

Reposting with the same tag (`sim-1`) updates the notification under the same key, which is how question 3 (updates versus new posts) can be rehearsed. Simulated text only tests the pipeline; the real formats, times and delays come from the bank apps on the phone.

## Forwarding to FinSync (M2, OTP Bank)

Since 2026-11-12 the app also sends OTP Bank transaction notifications to `POST /v1/notifications/ingest`:

- **Allow-list:** only a notification from `hu.otpbank.mobile` whose text matches a known OTP pattern ([`OtpFormat.kt`](app/src/main/java/hu/finsync/spike/OtpFormat.kt): signed amount and currency first, then a comma and the counterparty, or a merchant in capitals) leaves the phone. Every other bank notification is only counted per bank and channel ("Dropped on the phone"). Debug builds also forward simulated notifications (adb or the **Test** button).
- **What is sent:** text, title, `posted_at` (the post time as an ISO 8601 instant) and `source_ref` (the number at the end of the notification tag) and `device_zone` (the phone's zone id, for diagnosis only, ADR 0008).
- **No duplicates:** each matched notification goes into an outbox file first; WorkManager sends it when a network is available and retries with backoff. The server treats the same four fields as a re-delivery, and the phone remembers what it has sent, so a notification re-read on reconnect is not sent again. `400` (not a transaction for the server) drops it, `401`/`403` waits for a new token.
- **Setup:** enter the server address and the member's API token on the main screen and press **Save**. On the emulator the local API is `http://10.0.2.2:8080` (start it with `--host 0.0.0.0`); plain HTTP works only in debug builds, a release build needs the HTTPS tunnel ([ADR 0007](../../docs/architecture/decisions/0007-how-external-clients-reach-the-api.md)).
- **Known limits:** the token is not encrypted yet; the spike's capture log still runs next to forwarding; an updated notification (same key, new post time) would be sent as a new purchase, which the OTP app has not been seen doing.

## Rules for this folder

- Synthetic data only in code, tests and docs; real captures never leave the phone ([bank-notification-privacy skill](../../.claude/skills/bank-notification-privacy/SKILL.md)).
- The parser rule exists twice, here (gate) and in `finsync/ingestion/notifications.py` (authority); change both together, with the same test cases (`OtpFormatTest.kt`, `tests/test_android_ingest.py`).
