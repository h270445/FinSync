# 0005. Web app as the main user interface, built before the Android app

- Status: Proposed
- Date: 2026-10-09

## Context

FinSync needs screens for listing events, reviewing uncertain matches, correcting wrong links, manual entry, file import and token management. The roadmap commits an Android app and a Google Sheets script, but neither is suited to these tasks: the Android app forwards notifications in the background, and the Sheets script only sends rows. Review and correction (roadmap item 2) therefore had no user interface. A reviewer must also be able to run and try the system from the repository guide alone.

## Decision

- Build a **web app** as the main user interface: desktop browser first, responsive down to phone width.
- Implement it as static HTML, CSS and plain JavaScript in `finsync/web/`, served by the existing stdlib HTTP server and using the same `/v1` JSON API as the other clients (consistent with [ADR 0002](0002-python-stdlib-and-sqlite.md)).
- Keep the **Android app minimal** (setup and status screens); its main risk, notification access on a real device, is still addressed by the October spike.
- Design screens in Figma as visual references; generated code is not used ([design](../../design/user-interface.md)).

## Consequences

- Review and correction become demonstrable in a browser; testing needs no device or emulator.
- The web app is one more component in the semester scope; it is kept small by having no build step and a fixed list of screens.
- The API must serve the web app's needs (event list with records, decision history), which the matching design already plans.
- Serving static files adds a route to the stdlib server; the web app must use the same authentication as the other clients once tokens exist.
- If plain JavaScript becomes unmanageable, adopting a framework is a new decision.
