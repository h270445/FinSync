# Releases

One file per tagged milestone, plus the fix log for the final package.

| File | Contents |
| --- | --- |
| `vX.Y.Z.md` (one per tag) | Release notes for a milestone |
| `fix-log.md` (from M4) | Changes made in response to M3 feedback |
| [status-emails/](status-emails/README.md) | Hungarian text of each progress e-mail to the supervisor |

The tag plan is in [planning/milestones/](../planning/milestones/README.md).

## Index

| Tag | Milestone | Date | Notes |
| --- | --- | --- | --- |
| `0.1.0` | M0 — Semester commitment | 2026-10-09 | No release notes file; the M0 scope is in the [milestone](../planning/milestones/m0-2026-10-09-semester-commitment.md) and the [e-mail](status-emails/2026-10-09-m0.md). The tag was created without the `v` prefix. |
| `v0.2.0` | M1 — Working core | 2026-11-02 | [v0.2.0.md](v0.2.0.md) |

## Release notes template

```markdown
# vX.Y.Z — Mn: <milestone name>

- Date: YYYY-MM-DD
- Commit: <full commit id>

## What works
- ...

## How to verify
- Commands and expected output.

## Measurements
- Link to docs/evaluation/results/...

## Known limitations
- ...

## Changes since the previous milestone
- Pull requests merged.
```

## Fix log template

```markdown
| # | Feedback | Change | Commit / PR |
| --- | --- | --- | --- |
```
