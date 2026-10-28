# Android notification-listener spike

- Status: In progress (emulator rounds done 2026-10-26; phone test with real OTP Bank, Revolut and K&H notifications started 2026-10-27)
- Date: 2026-10-24
- Code: [clients/android/](../../clients/android/README.md)

The main risk of the Android client is not its UI but reading another app's banking notifications reliably on a real device ([ADR 0005](../architecture/decisions/0005-web-client-first.md)). This spike answers the questions below before the M2 Android app is built. All examples here are anonymised: amounts, merchants and names are made up.

## Questions

| # | Question | Why it matters | Answer |
| --- | --- | --- | --- |
| 1 | Which fields (title, text, big text, sub text, ticker) carry the purchase details, and in what wording? | Parser format for one bank | – |
| 2 | Is the time printed in the text local time, and how does it relate to `postTime`? Is there a time at all? | Time-zone ADR; `happened_at` for matching | – |
| 3 | Does one purchase produce several posts (updates of the same key, group summaries, re-posts after restart)? | Stable `source_ref`, re-delivery vs. new purchase | – |
| 4 | Do declined payments, refunds, transfers or balance messages arrive in a similar format? | What the parser must reject or support | Partly: OTP transfer and purchase share the amount-first format; Revolut also posts marketing on the same channel (2026-10-28), see [non-transaction notifications](#non-transaction-notifications) |
| 5 | Does the listener keep running after a restart, with battery optimisation on, and with the app closed for a day? | Whether background collection is reliable | – |
| 6 | How long after the purchase does the notification arrive? | Matching time window | – |

## Setup

| Item | Value |
| --- | --- |
| Phone, Android version | Samsung Galaxy A13 (SM-A136B), Android 14 (API 34), One UI 6.1 |
| Bank apps and versions | OTP Bank `hu.otpbank.mobile` 2.163.3 (package name confirmed), Revolut `com.revolut.revolut` 10.153.1, K&H `hu.kh.smartbanking` (watched since 2026-10-27) |
| Test period | From 2026-10-27: debug build installed over USB, listener access granted, a simulated notification captured on the phone |
| Scope | Only the bank apps' notifications are read (package-name allowlist); the emulator is used only for the self-sent test notification |

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

### 2026-10-27: first real notification (OTP Bank, outgoing transfer)

Galaxy A13, Android 14. Content was never read in clear text: the summary below was produced on the author's machine with every letter replaced by `a`/`A` and every digit by `9`.

| Field | Masked value or observation |
| --- | --- |
| Channel, category | `otp-mobile-bank`, none; not a group summary, not ongoing |
| Style | Big text; only `android.title`, `android.text` and `android.bigText` carry text, `text` equals `bigText` |
| `title` | `Aaaaaaaa aaaaaaaa` (two words) |
| `text` | `-9 999 Aa, Aaaaa Aaaaaa Aaaaaa`: signed amount with a space as thousands separator, a two-letter currency (presumably `Ft`), a comma, then the counterparty name |
| Time | No time in the text; `post_time_ms` and `when_ms` differ by 0.04 s |
| `tag` | `AAA-Aaaaaaaaaaaa:999999999`, apparently a transaction id |
| Repeats | One post, no update, no group summary |

First answers: question 1 (OTP transfer): one `text` field carries amount, direction (sign), currency and counterparty. Question 2: the notification prints no time, so `happened_at` must come from `post_time_ms`, an absolute instant; this simplifies the time-zone decision. Question 3: the `tag` looks like a stable transaction id and is the best `source_ref` candidate, to be confirmed with more notifications. No Revolut notification was recorded for this transfer.

### 2026-10-28: first real card purchase (OTP Bank) and a day of listening

Masked the same way (letters `a`/`A`, digits `9`); content never read in clear text.

| Field | Purchase | Transfer (2026-10-27) |
| --- | --- | --- |
| Channel, style | `otp-mobile-bank`, big text | same |
| `title` | `Aaaaaaa aaaaaaaa!` | `Aaaaaaaa aaaaaaaa` |
| `text` (= `bigText`) | `-9 999 Aa aaaaaaaa aaaaaaaaa aaaaaaaaaa a AAAAAAAAAA AAAAAA 99. aaaaaaaaaaaa.` | `-9 999 Aa, Aaaaa Aaaaaa Aaaaaa` |
| `tag` | `AAA-Aaaaaaaaaaaa:999999999` | same pattern; `id` is always 0 |
| Time | none in the text; `when` equals `post_time_ms` (5 ms) | same |
| Repeats | one post, no update, no group summary | same |

- **Question 1:** both kinds start with the signed amount and the currency; the transaction kind follows from the title, and the merchant (upper case, inside a sentence) or the counterparty (after a comma) needs a pattern per kind. One OTP parser with two patterns covers both.
- **Question 2:** no printed time; `happened_at` comes from `post_time_ms`, an absolute instant.
- **Question 3:** the tag ends in a nine-digit number in both kinds, most likely a transaction id: the `source_ref` candidate. `active_on_connect` after each reinstall repeated a notification still in the shade with the same `key` and `post_time_ms`, so those two fields deduplicate it.
- **Question 5:** no disconnect for about 22 hours (from the reinstall on Oct 27, 23:09 to the evening of Oct 28), without the *Never sleeping apps* setting; the purchase arrived normally.
- **Revolut:** one notification that is not a transaction (a name in the title, a date, no amount); the parser must reject it. Revolut puts the whole notification text into the `tag`, so the `key` carries content: keys must not be logged or stored unmasked.

## Next: real device (2026-10-27)

The USB install and the live test on the Samsung are moved to 2026-10-27. The emulator answered what it can; the checks below need the real phone and bank apps.

- Install the debug build over USB (README, *Running it*, step 3), grant notification access and record the phone model, Android and bank app versions in *Setup*; confirm the OTP Bank package name.
- Questions 1, 2 and 6 from a few small card purchases: which extras carry the text (`android.bigText`, `android.textLines`, `android.messages`), the printed time against `post_time_ms`, and the delay after paying.
- Question 4 cheaply: a transfer between family members in the mobile bank shows the transfer format on both sides (outgoing and incoming) without a purchase; these are the records the planned `transfer` direction must recognise ([categorization](categorization.md#money-transfers)).
- Question 5: a phone restart and a day with the app closed; check how long after boot `listener_connected` and `active_on_connect` appear, and whether Samsung's battery management stops the listener.
- A single swipe dismissal (not triggered on the emulator), to see its removal reason.

## Non-transaction notifications

Bank apps also post marketing, news and security messages; the Revolut notification of 2026-10-28 was one, on the same channel as transactions and with the whole text repeated in its `tag` and `key`. Proposed on 2026-10-28; the author asked for it in this pull request:

**In the spike (from 2026-10-28):** every bank notification is still recorded, because question 4 needs to see what else the banks send, but only a likely transaction is kept in full. A notification is a *transaction candidate* when any of its texts contains an amount with a currency (`-4 500 Ft`, `1,234.56 HUF`, `€4.50`; [`TransactionFilter.kt`](../../clients/android/app/src/main/java/hu/finsync/spike/TransactionFilter.kt)). Anything else is stored as `kind: "other"` with its channel, category, extras keys and masked texts only (letters `a`/`A`, digits `9`); its key is stored only as a hash. Removal records also carry only the key hash.

**In the M2 app (rule):**
- Accept, do not reject: a notification is forwarded only when it matches a known pattern of that bank (signed amount and currency plus a known title per transaction kind). Everything else is dropped on the phone and never reaches the API. A list of marketing phrases is not kept, because new wording would slip through silently.
- The channel is a cheap pre-filter where a bank separates marketing from transactions; Revolut does not, so the pattern decides.
- Of dropped notifications only counts per bank and channel are kept. If a bank sends notifications but none matches for days, its format probably changed and the pattern needs an update; the status screen shows this.
- The server parser keeps rejecting unsupported text with `400`; the app treats that as "not a transaction" and does not retry.

## Consequences

To be written when the questions are answered: the supported format, the `source_ref` rule, the time-zone decision and any reliability limits for the M2 app.
