# Android notification-listener spike

- Status: In progress
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

## Consequences

To be written when the questions are answered: the supported format, the `source_ref` rule, the time-zone decision and any reliability limits for the M2 app.
