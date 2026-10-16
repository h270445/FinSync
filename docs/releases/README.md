# Releases

One file per tagged milestone, plus the fix log for the final package.

| File | Contents |
| --- | --- |
| `vX.Y.Z.md` (one per tag) | Release notes for a milestone |
| `fix-log.md` (from M4) | Changes made in response to M3 feedback |
| [status-emails/](status-emails/README.md) | Hungarian text of each progress e-mail to the supervisor |

No release has been tagged yet. The tag plan is in [planning/milestones/](../planning/milestones/README.md).

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
