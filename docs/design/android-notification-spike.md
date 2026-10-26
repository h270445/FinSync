# Android notification-listener spike

- Status: In progress (emulator rounds done 2026-10-26; test on the author's Samsung phone with real OTP Bank and Revolut notifications planned for 2026-10-27)
- Date: 2026-10-24
- Code: [clients/android/](../../clients/android/README.md)

The main risk of the Android client is not its UI but reading another app's banking notifications reliably on a real device ([ADR 0005](../architecture/decisions/0005-web-client-first.md)). This spike answers the questions below before the M2 Android app is built. All examples here are anonymised: amounts, merchants and names are made up.

## Questions

| # | Question | Why it matters | Answer |
| --- | --- | --- | --- |
| 1 | Which fields (title, text, big text, sub text, ticker) carry the purchase details, and in what wording? | Parser format for one bank | – |
| 2 | Is the time printed in the text local time, and how does it relate to `postTime`? Is there a time at all? | Time-zone ADR; `happened_at` for matching | – |
| 3 | Does one purchase produce several posts (updates of the same key, group summaries, re-posts after restart)? | Stable `source_ref`, re-delivery vs. new purchase | – |
| 4 | Do declined payments, refunds, transfers or balance messages arrive in a similar format? | What the parser must reject or support | – |
| 5 | Does the listener keep running after a restart, with battery optimisation on, and with the app closed for a day? | Whether background collection is reliable | – |
| 6 | How long after the purchase does the notification arrive? | Matching time window | – |

## Setup

| Item | Value |
| --- | --- |
| Phone, Android version | Samsung, latest Android (exact model and version recorded at the first run) |
| Bank apps and versions | OTP Bank, Revolut (versions recorded at the first run) |
| Test period | – |
| Scope | Only the two bank apps' notifications are read (package-name allowlist); the emulator is used only for the self-sent test notification |

## Observations

Anonymised examples and notes per question are added here as the spike runs.

### 2026-10-26: emulator, simulated notifications

Debug build on an Android 17 (API 37) emulator without Play Store, notifications posted with `adb shell cmd notification post` (synthetic text only). This checks the pipeline, not the bank formats.

- The listener received all three posted notifications with title and text intact (`package` `com.android.shell`, `simulated: true`).
- **Question 3 (rehearsal):** posting twice with the same tag gives two `posted` records with the same `key` (`0|com.android.shell|2020|sim-1|2000`) and different `post_time_ms`. An update is therefore not distinguishable from a re-post by the key alone; the M2 app must derive `source_ref` from the key plus the content, or treat a same-key, same-text post as a re-delivery.
- Android added system **group summary** posts (`group_summary: true`, tag ending in `Aggregate_AlertingSection`, no title or text) with the same post time. The parser must drop group summaries and posts without text.
- The emulator's zone was GMT (`device_zone`), so time-zone behaviour (question 2) can only be judged on the phone.

### 2026-10-26: emulator, notification styles and listener restarts

Debug build with lossless capture (all extras, group key, removal reason) on an Android 16 (API 36) emulator, 4 GB RAM, host GPU; first half repeated on API 37 with the same results. Synthetic text only.

| Case | Observation | Consequence for the M2 app |
| --- | --- | --- |
| Big-text style | Text in `android.text`, `android.template` = `Notification$BigTextStyle`; `android.bigText` empty because adb sets only the content text | Parser reads `android.bigText` first, then `android.text` |
| Inbox style, three lines | Lines in the `android.textLines` array; `android.text` holds only the summary | A bank that groups transactions needs one record per line |
| Messaging style | Messages in `android.messages[]` with `text`, `sender`, `time`; `android.text` is only the last message | Same as inbox: read every message |
| Accented text (á, ő, ű) | Arrives intact | Encoding is not a risk; on Windows pass the whole adb command as one string |
| Repost with the same tag | Same `key`, new text and `post_time_ms`, no `removed` in between | An update is a new version under the same key: `source_ref` = key plus content hash |
| Removal | Snooze: reason 18 `snoozed`; *Clear all*: reason 3 `user_dismissed_all` for every notification and the group summary; single swipe not triggered on the emulator | Removal says nothing about the purchase; ignore it except for diagnostics |
| Group summary | Re-posted with its old post time on every regrouping, `group_summary: true`, no text | Drop |
| Force-stop, then reopen | No `listener_disconnected` (process killed); the post during the stop and one right after reopening were lost; later posts arrived | Missed posts are not replayed by Android; read `activeNotifications` on connect (added to the spike) and accept that dismissed ones are lost |
| Reboot | Listener reconnected by itself without new permission, but only 1–2 minutes after boot; a post 20 s after boot was lost | Same as above; on the phone, watch how long Samsung takes |

The emulator was CPU-bound (listener delays of 1–7 s), so delays measured here say nothing about real delivery times (question 6).

### 2026-10-26: lightweight emulator, missed posts recovered on connect

Android 16 (API 36) image without Google services, 2.5 GB RAM; boot in about 20 s, notifications delivered within 0.2–0.5 s. Debug build with `active_on_connect` (commit `be267c0`).

- **Force-stop:** Android rebound the listener by itself within about 2 s, before the app was reopened, and every notification still in the shade was recorded as `active_on_connect` (including the group summary). The post made during the stop arrived as a normal `posted` record. In the earlier, overloaded run the rebind waited until the app was reopened, so the rebind delay depends on system load.
- **Reboot:** a notification posted about 2.7 s before `listener_connected` was not delivered as `posted` but was recovered as `active_on_connect`; later posts arrived normally. No new permission was needed.
- **For the parser:** `active_on_connect` repeats notifications that were already recorded (same `key` and `post_time_ms`), so `key` plus `post_time_ms` identifies one post; group summaries keep reappearing and are dropped. A notification that was posted and dismissed while the listener was down is lost; this is an Android limit.

## Consequences

To be written when the questions are answered: the supported format, the `source_ref` rule, the time-zone decision and any reliability limits for the M2 app.
