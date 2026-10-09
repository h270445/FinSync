# M2 — Integrated prototype

- Deadline: 2026-12-04 23:59
- Tag: `v0.3.0`
- Status: planned

## Expected result (course)

The core flows committed for the semester work together, with proper data handling, basic error handling and tests.

## Acceptance criteria

- [ ] All three sources (notification text, manual entry, spreadsheet-export import) go through the same matching pipeline.
- [ ] Uncertain matches can be listed, confirmed and rejected; a wrong link can be split; every action is logged and supersedes the previous decision.
- [ ] Requests are authenticated with per-user tokens; client-supplied identity headers are no longer trusted.
- [ ] Every endpoint has a cross-group access test (403/404, nothing written).
- [ ] Malformed input, oversized bodies and failing bulk imports leave the database unchanged and return a clear 400.
- [ ] Thresholds tuned on the development split; results on the held-out test split saved with the commit id.

## Checklist

- [ ] Review and correction endpoints with tests.
- [ ] CSV import with `import_batch_id` and `source_ref`.
- [ ] Authentication and request size limits.
- [ ] Full labelled dataset (200–300 records), threshold sweep.
- [ ] Docs updated (API reference, security status, evaluation results).
- [ ] Release notes, tag `v0.3.0`, e-mail.
