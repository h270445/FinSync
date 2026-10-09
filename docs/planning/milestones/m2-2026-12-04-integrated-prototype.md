# M2 — Integrated prototype

- Deadline: 2026-12-04 23:59
- Tag: `v0.3.0`
- Status: planned
- Internal target: 2026-11-27

## Expected result (course)

The core flows committed for the semester work together, with proper data handling, basic error handling and tests.

## Acceptance criteria

- [ ] All sources go through the same matching pipeline: Android notifications (one bank format), spreadsheet-export files and manual entries (Google Sheets rows if the script is built).
- [ ] Demo: a notification on the phone and the same purchase imported from a spreadsheet appear as one event, while two separate purchases of the same amount on the same day stay two events.
- [ ] Uncertain matches can be listed, confirmed and rejected in the web app; a wrong link can be split; every action is logged and supersedes the previous decision.
- [ ] Requests are authenticated with per-user tokens; client-supplied identity headers are no longer trusted.
- [ ] Every endpoint has a cross-group access test (403/404, nothing written).
- [ ] Malformed input, oversized bodies and failing bulk imports leave the database unchanged and return a clear 400.
- [ ] The LLM categorizer runs behind the same interface as the rule-based one and its output is validated against the category list.

## Checklist

- [ ] Authentication and request size limits.
- [ ] Review and correction endpoints with tests.
- [ ] Web app: event list, event detail with split and category correction, review queue (manual entry, file import and token management if time allows).
- [ ] Android app (notification listener, token setup, sending, retry) with its README.
- [ ] File import with `import_batch_id` and `source_ref`; Sheets script if time allows.
- [ ] LLM categorizer and labelled categorization dataset.
- [ ] Docs updated (API reference, security status, client setup in the guides).
- [ ] Release notes, tag `v0.3.0`, e-mail.
