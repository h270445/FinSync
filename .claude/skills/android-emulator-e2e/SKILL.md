---
name: android-emulator-e2e
description: Use after any change to the FinSync Android app (clients/android) or to the notification ingest, to build the app and test it end to end on an emulator against a local API with made-up notifications. Runs on the author's Windows computer through Remote Control.
---

# Android emulator end-to-end test

- Version: 1.2 (2026-11-24)
- Owner: Bence Varga
- Why it exists: the Android app can only be built and run on the author's computer (Android SDK, emulator). The first M2 test on 2026-11-12 showed that a fixed sequence (build, emulator, local API, simulated notifications, checks through the API, the outbox and the screen) catches real bugs, including two that no unit test saw. Doing it by hand took several manual steps and one environment trap (a stale `JAVA_HOME`).

## Input

- The branch to test, and what changed (app, server ingest or both).
- The mode: **test** (the cases below, the default), **demo** (the M2 demo of [docs/guides/demo.md](../../../docs/guides/demo.md) on the emulator, see "Demo mode"), or **real phone** (only when the author asks, see "Real-phone variant").
- The author's computer with Android Studio's SDK, at least one AVD, and the repository at `C:\Users\User\StudioProjects\FinSync`.

## Output

1. A PASS/FAIL table for the cases below, each with its evidence (API JSON, outbox content, the status lines from a UI dump), the time of the build, the boot and the tests, and the free memory before the emulator starts and during the cases.
2. A screenshot of the main screen, saved next to the app (`clients\android\m2-emulator-test.png`), never committed.
3. A list of bugs found, with file and line and a proposed fix. The test session does not fix behaviour on its own; only compile errors may be fixed, and each fix is reported.

## Prohibitions

- **No real phone and no real notification**, except in the real-phone variant the author asked for. Before installing, `adb devices` must list only `emulator-*` devices; otherwise stop. Never read, count or pipe `captures.jsonl`, an export or any notification from a real bank app ([bank-notification-privacy](../bank-notification-privacy/SKILL.md)).
- Only the made-up texts of the cases below, or new ones in the same masked shapes.
- Never switch branches over uncommitted changes: `git status` first; untracked IDE folders (`.idea/`) are fine, anything else stops the run.
- A fresh database in a temporary folder for every run; never the author's `finsync.db`.
- Never commit the screenshot, the test database or the token. Never print the token in the report.
- Do not push behaviour changes from the test session; propose them.

## Steps

1. **Prerequisites.**
   - JDK 17–23 for Gradle 8.11.1. Do not trust `JAVA_HOME`: check that it exists and `java -version` is 17–23. Android Studio's own JDK (25) is too new. On this computer `C:\Program Files\Eclipse Adoptium\jdk-21.0.7.6-hotspot` works.
   - `adb` and `emulator` from `%LOCALAPPDATA%\Android\Sdk\platform-tools` and `\emulator`.
   - **Free memory.** The computer has 7.7 GB of RAM and the emulator alone takes about 1.3 GB. Read the free memory with `(Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory` (KiB). Below about 2.5 GB, stop and ask the author to close memory-heavy programs (browser, Discord, Steam), then read it again. Write both values in the report, and the value once more after the emulator has booted and during the cases, so later runs show how much it matters (the slow first run on 2026-11-12 could not be explained afterwards because nothing was measured). On 2026-11-24: 1.44 GB before, 2.40 GB after the author closed Discord, 0.74 GB with the emulator booted from its snapshot; the run still worked.
2. **Branch and backend tests.** From the repository root (all later paths are relative to it): `git status`, `git fetch`, `git checkout <branch>`, `git pull`; activate `.venv`, `pip install -r requirements.txt`, `python -m unittest discover -s tests`. In PowerShell, pip's stderr shows as `NativeCommandError` even on success; judge by `$LASTEXITCODE`, and do not wrap commands in `cmd /c` (it ignores PowerShell's current folder).
3. **Build.** In `clients\android`, directly in PowerShell: `.\gradlew.bat testDebugUnitTest assembleDebug *> <tmp>\build.log` and check `$LASTEXITCODE` (about 2.5 minutes, 1 minute when incremental). Return to the repository root.
4. **Emulator.** `emulator -list-avds`, start one (`FinSync_API36` exists) with `Start-Process` so the window opens and the shell does not wait, `adb wait-for-device`, then poll `adb shell getprop sys.boot_completed` until `1` (about 2.5 minutes from a cold boot, under 10 s from the Quick Boot snapshot). Check `adb devices` (emulators only).
5. **Local API.** Temporary database; `python -m finsync.api.tokens --db <tmp>\e2e.db create --user anna --group lakas --name Emulator`, capturing the `fs_...` line into a variable or a file in the temporary folder without echoing it; start `python -m finsync.api --host 0.0.0.0 --port 8080 --db <tmp>\e2e.db` in the background (`Start-Process` with its output redirected to log files in the temporary folder; the virtual environment's `python.exe` starts a child process, so stop the server later by its port, not by the PID `Start-Process` returned) and poll `http://127.0.0.1:8080/openapi.json` until it answers (5–8 s); a curl right after the start fails.
6. **Clean state.** A reused emulator still holds the previous run's notifications and app data (sent keys, counters, outbox), which would be re-sent or skew the counts. `adb uninstall hu.finsync.spike` (ignore "not installed"); clear the notification shade: `adb shell cmd statusbar expand-notifications`, tap "Clear all" (its bounds from a UI dump), `adb shell cmd statusbar collapse`; `adb shell "dumpsys notification --noredact | grep -c pkg=com.android.shell"` must print 0.
7. **Install and configure.** `adb install -r clients\android\app\build\outputs\apk\debug\app-debug.apk`; `adb shell pm grant hu.finsync.spike android.permission.POST_NOTIFICATIONS`; build `forwarder.xml` (`server_url` `http://10.0.2.2:8080`, `token` from the captured value) in the temporary folder, push it to `/data/local/tmp`, then `adb shell run-as hu.finsync.spike cp /data/local/tmp/forwarder.xml shared_prefs/` (create `shared_prefs` first), and delete both copies (the copied file ends up `rw-rw-rw-`, harmless on the emulator and rewritten by **Save**); `adb shell am force-stop hu.finsync.spike`; `adb shell cmd notification allow_listener hu.finsync.spike/hu.finsync.spike.SpikeListenerService`; start the app with `adb shell monkey -p hu.finsync.spike 1` and leave it in the foreground.
8. **Cases** (post with `adb shell "cmd notification post -S bigtext -t '<title>' <tag> '<text>'"`, one quoted string in PowerShell; for A, B and E poll the API for up to 60 s; for C and D, which prove that nothing happens, wait a fixed 20 s). Counters come from `adb shell run-as hu.finsync.spike cat shared_prefs/forwarder.xml` (`dropped:...` and `sent`), read before C, after C and after D; the screen is not a source for them:

   | Case | Notification | Expected |
   | --- | --- | --- |
   | A purchase | `sim-otp-1`: `-4 990 Ft erteken vasarolt a PELDABOLT KFT 12. uzleteben.` | event PELDABOLT KFT, -4990 HUF, `card_purchase`, `android_notification` |
   | B transfer | `sim-otp-2`: `-12 000 Ft, Minta Anna` | event Minta Anna, -12000 HUF, `outgoing_transfer` |
   | C marketing | `sim-otp-3`: `Nyerj 10 EUR jovairast!` | no event; "Dropped on the phone" grows by exactly 1 |
   | D reconnect | `disallow_listener`, then `allow_listener`; proof of the reconnect: `adb shell dumpsys notification` lists `SpikeListenerService} (user 0)` again | still 2 events, no new POST in the API log, dropped count unchanged |
   | E offline | stop the API, post `sim-otp-4`: `-2 500 Ft erteken vasarolt a MINTA PEKSEG uzleteben.` | one line in `run-as hu.finsync.spike cat files/outbox.jsonl`; after restarting the API on the same database, 3 events within 3 minutes and an empty outbox |
   | F status screen | with the app in the foreground since step 7 (`dumpsys activity activities` shows it as `topResumedActivity`), read the status lines from a UI dump, tap Refresh, read them again; `pidof hu.finsync.spike` is the same before and after | the second read shows `Waiting: 0, sent: 3, refused by server: 0`, `Last: ... sent (201)`, dropped 1 (the screen does not refresh by itself while the app is open) |

   Events: `curl -H "Authorization: Bearer <token>" http://127.0.0.1:8080/v1/events`.
9. **Evidence.** Read the status lines from `adb shell uiautomator dump /sdcard/ui.xml` and `adb shell cat /sdcard/ui.xml` (`text="..."`), more reliable than reading a screenshot. Take the screenshot with `adb shell screencap -p /sdcard/shot.png`, `adb pull /sdcard/shot.png clients\android\m2-emulator-test.png`, `adb shell rm /sdcard/shot.png` (`adb exec-out ... >` in Windows PowerShell 5.1 writes a broken PNG). If a "System UI isn't responding" dialog appears, tap its "Wait" button (found in the UI dump) and take the screenshot again.
10. **Clean up.** Skip this step only when the author asked to leave the run open (for example to watch a demo); then give the stop commands of "Demo mode" in the report. Stop the API, delete the temporary database and the token file, clear the notification shade, then stop the emulator with `adb emu kill` (it frees about 1.3 GB of RAM on this 7.7 GB computer; the emulator saves a Quick Boot snapshot, so the next start takes seconds instead of a cold boot, and step 6 clears the old state anyway; clearing the shade first keeps the snapshot clean). Then `adb devices` must list no emulator. Never end it with `taskkill`: that saves no snapshot and can damage the AVD. If the author already closed the emulator window, `adb devices` is empty and `adb emu kill` answers "no emulator detected": that is fine (closing the window also saves the snapshot). Leave it running only if the author says another run follows soon. Nothing committed.

## Demo mode

For the author's dry run of the M2 demo, or to show it. Steps 1–4 and 6–7 as above, with these differences:

- **Step 5 uses the demo seed** instead of a new token: `python -m finsync.api.demo --db <tmp>\demo.db --export-dir <tmp>` (it refuses an existing file). Capture the `fs_...` token from its output into `<tmp>	oken.txt` without echoing it (print the output with the token replaced by `fs_<REDACTED>`); the web sign-in and the export path it prints are not secret. Read `GET /v1/overview` once before any step: on a fresh seed the expense total is 31 090 Ft with 3 uncertain events.
- **Step 8 is the demo's step 1a only:** post case A with the tag `demo-1` and poll for the PELDABOLT KFT event of -4990 with source `android_notification`. Tap Refresh before the UI dump and the screenshot (the screen does not refresh by itself); the screenshot goes to `clientsndroid\m2-demo-emulator.png`, never committed.
- **The web app** for the author: in `web\`, `npm install` when `package.json` changed, then `npm run dev` in the background (http://localhost:5173, it forwards `/v1` to the API). Sign-in `anna` / `finsync-demo-2026`.
- **The other demo steps through the API**, so they are checked even when nobody clicks: `POST /v1/imports` with `{"content": <the CSV text>}` (expected `auto_linked`, `separate`, `separate`, the linked row in the PELDABOLT event, which then has the sources `android_notification` and `file_import`); two MINTA KAVEZO events of -1200; one item in `GET /v1/matches/review`, confirmed with `POST /v1/matches/{decision_id}/confirm`; `GET /v1/overview` after each step. The numbers to compare with are in the guide's step 5 (31 090 → 38 480 → 35 980 Ft). Leave out the steps the author wants to click (on 2026-11-24: the categories and the split).
- **Leaving it running:** when the author wants to watch, skip step 10 and give these stop commands (PowerShell, repository root): `& "$env:LOCALAPPDATA\Android\Sdk\platform-toolsdb.exe" emu kill`; `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8080 -State Listen).OwningProcess`; the same with port 5173; `Remove-Item -Recurse -Force <tmp>`. When asked to stop it, do step 10 and stop the web server too.

## Real-phone variant

Only when the author asks for it, on the author's own phone, with [bank-notification-privacy](../bank-notification-privacy/SKILL.md) in force (first used on 2026-11-20–21). Differences from the test mode:

- `adb devices` lists the phone and no other physical device; say in the report which one (model only).
- The phone reaches the API over the USB cable: `adb reverse tcp:8080 tcp:8080` and the server address `http://127.0.0.1:8080` instead of `10.0.2.2`; the API may then listen on `127.0.0.1`.
- **No uninstall and no clearing of app data** in step 6: the phone keeps its own captures. Configure the server and the token on the app's screen (the author types the token, or the preferences are pushed as in step 7 when the author agrees), never by overwriting files the author did not ask to replace.
- The made-up cases A–F run as above. A real purchase is the author's own step: report only its outcome (sent, dropped, status code) and, on the server, the presence, kind and shape of fields. Never display, count by content or pipe the real notification's text, amount or merchant, the outbox or `captures.jsonl`.
- Clean up: `adb reverse --remove tcp:8080`, stop the API and delete the temporary database; the app stays on the phone.

## Self-check

Before reporting PASS, each case has its evidence in the report: the event list JSON for A, B and E, the outbox content for E, the dropped count before and after C and D, and the UI dump lines for F. A case without evidence is reported as not checked.

## Human checkpoints

1. **Before** the run: the author approves the Remote Control session (it uses their computer). The request also asks them to close memory-heavy programs such as the browser for a faster run.
2. **After**: the author reads the bug list and decides which fixes go into the pull request. A test on the real phone with a real purchase is the author's own step; only its outcome (sent, dropped, status code) is reported, never the text.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-12 | First version, from the first M2 emulator run (all cases passed; found the status screen not refreshing and dropped notifications counted again on reconnect). |
| 1.1 | 2026-11-12 | After its first use: clean state before installing, counters read from the app's preferences, fixed waits for C and D, a real check of the refresh in F, screenshot through `adb pull`, paths from the repository root, token never echoed, no `cmd /c`, reconnect proof without touching `captures.jsonl`; free memory checked and reported, and the author asked to close memory-heavy programs; the emulator is stopped at the end. |
| 1.2 | 2026-11-24 | After the M2 demo dry run and the real-phone run: a demo mode (seed with its token captured, web dev server, the other demo steps checked through the API, leaving it running with stop commands), a real-phone variant (`adb reverse`, no uninstall, outcome only), free memory read after the boot too, background start and stop of the API by its port, and what to do when the emulator window was closed already. |
