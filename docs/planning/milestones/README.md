# Milestones

One target file per course deadline. The course deadline is the latest submission date; each file also gives an earlier internal target, and work on the next milestone starts as soon as the current one is complete. Each file states the expected result, acceptance criteria that can be checked from the repository, a checklist, and the version tag.

| Milestone | Deadline | Internal target | File | Tag |
| --- | --- | --- | --- | --- |
| M0 | 2026-10-09 | – | [Semester commitment](m0-2026-10-09-semester-commitment.md) | `v0.1.0` |
| M1 | 2026-11-06 | 2026-10-30 | [Working core](m1-2026-11-06-working-core.md) | `v0.2.0` |
| M2 | 2026-12-04 | 2026-11-27 | [Integrated prototype](m2-2026-12-04-integrated-prototype.md) | `v0.3.0` |
| M3 | 2027-01-15 | 2027-01-08 | [Preliminary final package](m3-2027-01-15-preliminary-package.md) | `v0.9.0` |
| M4 | 2027-01-30 | as feedback arrives | [Corrected final package](m4-2027-01-30-final-package.md) | `v1.0.0` |

## Delivering a milestone

1. Tick the checklist in the milestone file; move unfinished items to the next milestone and note it in the roadmap change log.
2. Write the release notes in [releases/](../../releases/README.md).
3. Create an annotated tag on the `main` commit that is being submitted, and push it:

   ```bash
   git tag -a v0.2.0 -m "M1: working core"
   git push origin v0.2.0
   ```

4. Send the milestone e-mail with the tag name and the full commit id (`git rev-parse v0.2.0^{commit}`).

Tags follow [Semantic Versioning](https://semver.org/): `0.x` while the prototype is in development, `1.0.0` for the final package of this semester.
