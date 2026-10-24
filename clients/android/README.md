# `clients/android/` — notification-listener spike

A throwaway Android app (Kotlin, Jetpack Compose) that answers the open questions about reading banking notifications on a real device before the M2 Android app is built ([roadmap](../../docs/planning/roadmap.md), Oct 19–25 side track). It only logs; it does not send anything to the FinSync API yet.

Findings go in [docs/design/android-notification-spike.md](../../docs/design/android-notification-spike.md).

## What it records

| Data | Where | Content |
| --- | --- | --- |
| Notifications of the selected bank app (and the app's own test notifications) | `captures.jsonl` in app-private storage | package, key, id, tag, `postTime`, `when`, channel, category, group-summary and ongoing flags, title, text, big text, sub text, ticker; device time and time zone |
| Every other app | shared preferences | package name and count only, no content |
| Listener connect and disconnect | `captures.jsonl` | type and device time |

Nothing leaves the phone unless **Export** is pressed. Exported data contains real personal data and is **never committed**: only anonymised format descriptions (made-up amounts, merchants and names) go into the repository.

## Running it

1. Open `clients/android/` in Android Studio (Ladybug or newer, JDK 17) and let it sync.
2. Enable USB debugging on the phone, connect it and press **Run**.
3. In the app press **Access** and allow notification access for *FinSync notification spike*.
4. Press **Test**: a notification in the supported FinSync format appears and is logged; this checks the listener without a purchase.
5. Wait for (or trigger) any notification from the bank app, press **Refresh**, tick the bank's package in the list.
6. From then on, every bank notification is logged. Make a few small card purchases; also try a phone restart and a day with the app closed.
7. **Export** shares the log as text; anonymise it before pasting anything into the findings document.

## Rules for this folder

- Spike code: no API calls, no tokens, no network permission.
- The M2 app (setup and status screens, WorkManager sending, Room queue, encrypted token, see [technology stack](../../docs/architecture/technology-stack.md#android)) replaces this code; the spike's findings decide its parser and `source_ref`.
