# `clients/android/` — notification-listener spike

A throwaway Android app (Kotlin, Jetpack Compose) that answers the open questions about reading banking notifications on a real device before the M2 Android app is built ([roadmap](../../docs/planning/roadmap.md), Oct 19–25 side track). It only logs; it does not send anything to the FinSync API yet.

Findings go in [docs/design/android-notification-spike.md](../../docs/design/android-notification-spike.md).

## What it records

The spike watches only the bank apps listed in [`BankApps.kt`](app/src/main/java/hu/finsync/spike/BankApps.kt), matched by package name (the `id=` in the app's Play Store link):

| App | Package |
| --- | --- |
| OTP Bank | `hu.otpbank.mobile` (to be confirmed from the Play Store link) |
| Revolut | `com.revolut.revolut` |

Debug builds also watch `com.android.shell`, the sender of notifications posted with adb, so simulated bank text can be tested without a purchase (see below). Release builds never do. Every record carries `simulated: true` unless it came from a bank app.

Android delivers every notification to a listener; the spike drops anything from another app before reading its content, so nothing about other apps is stored, not even their names.

| Data | Where | Content |
| --- | --- | --- |
| Notifications of the watched bank apps and the app's own test notifications | `captures.jsonl` in app-private storage | package, key, id, tag, `postTime`, `when`, channel, category, group-summary and ongoing flags, title, text, big text, sub text, ticker; device time and time zone |
| Listener connect and disconnect | `captures.jsonl` | type and device time |

Nothing leaves the phone unless **Export** is pressed. Exported data contains real personal data and is **never committed**: only anonymised format descriptions (made-up amounts, merchants and names) go into the repository.

## Target device

Samsung phone on the latest Android (`compileSdk` and `targetSdk` 36, `minSdk` 26). Samsung's battery management may stop background listeners: if records stop arriving, add the app under *Settings → Battery → Background usage limits → Never sleeping apps* and note it in the findings.

## Running it

1. Install [Android Studio](https://developer.android.com/studio) (it brings the SDK and JDK), open `clients/android/` and let Gradle sync. Accept any suggested Android Gradle Plugin update.
2. **Emulator first:** create a virtual device with the latest Android image and press **Run**. Press **Access**, allow notification access for *FinSync notification spike*, then **Test**: a notification in the FinSync format appears and is logged. This checks the listener without a bank app.
3. **Real phone:** enable developer options and USB debugging on the Samsung, connect it and press **Run** with the phone selected. Repeat the access step. The bank apps only produce real notifications on the phone where the accounts are signed in, so questions 1–6 of the findings are answered here, not on the emulator.
4. The main screen shows whether OTP and Revolut are installed and how many of their notifications were captured. Make a few small card purchases; also try a phone restart and a day with the app closed.
5. **Export** shares the log as text; anonymise it before pasting anything into the findings document.

## Simulated bank notifications (debug builds)

With the emulator or the phone connected, post any text; it is captured as `simulated`:

```bash
adb shell cmd notification post -t "OTP Bank" sim-1 "Kártyás vásárlás: -4 500 HUF, Teszt Bolt, 2026.10.24 13:45"
adb shell cmd notification post -S bigtext -t "Revolut" sim-2 "Paid 4 500 HUF at Test Shop"
```

Reposting with the same tag (`sim-1`) updates the notification under the same key, which is how question 3 (updates versus new posts) can be rehearsed. Simulated text only tests the pipeline; the real formats, times and delays come from the bank apps on the phone.

## Rules for this folder

- Spike code: no API calls, no tokens, no network permission.
- The M2 app (setup and status screens, WorkManager sending, Room queue, encrypted token, see [technology stack](../../docs/architecture/technology-stack.md#android)) replaces this code; the spike's findings decide its parser and `source_ref`.
