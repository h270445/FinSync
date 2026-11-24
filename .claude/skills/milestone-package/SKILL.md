---
name: milestone-package
description: Use when closing a FinSync milestone (M2, M3, M4) before its e-mail, for example "put together the M2 package". Runs the full checks on both databases, ticks the acceptance criteria only with evidence, writes the English release notes docs/releases/vX.Y.Z.md and prepares the tag for the author.
---

# Milestone package

- Version: 1.0 (2026-11-24)
- Owner: Bence Varga
- Why it exists: every milestone ends the same way (M1 on 2026-11-02, M2 on 2026-11-27 and 2026-12-04, M3 on 2026-01-15, M4 on 2026-01-30): full tests, acceptance criteria ticked with evidence, release notes, tag, then the status e-mail. The [supervisor-status-email](../supervisor-status-email/SKILL.md) skill takes the release notes as its input, but nothing fixed how they are made; at M1 this was done from memory. This skill is that missing step, so a "done" in the e-mail always has a tested commit behind it.

## Input

- The milestone (M2, M3, M4), its file in `docs/planning/milestones/`, the version (`v0.3.0` for M2, then one minor version per milestone) and the commit the package describes (normally the head of the session's branch; after the merge, the merge commit on `main`).
- The previous release notes (`docs/releases/v0.2.0.md` is the model), the [roadmap](../../../docs/planning/roadmap.md), the open actions in [supervisor-feedback.md](../../../docs/planning/supervisor-feedback.md) and the results in `docs/evaluation/results/`.

## Output

1. The milestone file with every acceptance criterion and checklist line either ticked with its evidence (link, test name, result file, date) or left open with what is missing in brackets.
2. `docs/releases/vX.Y.Z.md` in English, in the order of v0.2.0: what works, how to verify (commands with the test counts they print), measurements (numbers copied from the result files, with links), known limitations, what changed in the plan, decisions recorded (ADRs). A row in `docs/releases/README.md`.
3. Updated API reference, security status and getting-started guide where the milestone changed them (the closing schedule names them).
4. A report in the reply: the gate results with counts, the criteria table (criterion, ticked or open, evidence), the commands the author runs to tag after the merge, and the handover to the supervisor-status-email skill.

## Prohibitions

- **Never set or push a tag.** The tag is set by the author on `main` after the merge; the skill only writes the command. Never push to `main` and never merge.
- Never call a criterion done without evidence that a reader can open: a test that runs, a result file, a screenshot kept outside the repository and described, or a merged pull request. A criterion met only in part stays unticked, with what is done in brackets (as the [session-wrap-up](../session-wrap-up/SKILL.md) rule says).
- Never copy a number into the release notes from memory or from an earlier e-mail: every count comes from a command run in this session, every measurement from its result file.
- Never describe the package from a dirty tree: `git status --short` is empty before the gates, so the counts belong to a commit.
- Never put a model identifier, an e-mail address, a token or real financial data in the release notes; the measured model is named only in the result files, as before.
- Never change the plan's dates or scope to make a criterion look met; a criterion that moves is a plan change with its own roadmap change-log row and the author's decision.

## Steps

1. **Clean tree and the commit.** `git status --short` empty; `git log -1 --format='%H %ad'` gives the commit the package describes.
2. **Gates, on both databases.** Copy each result line into the report; a gate that cannot run is reported as not run.

   ```bash
   python -m unittest discover -s tests                                  # SQLite, all OK
   python tests/run_on_postgres.py "$FINSYNC_TEST_DATABASE_URL"          # PostgreSQL, all OK (skips named)
   python .claude/skills/docs-and-comments/check_docs.py                 # OK
   python .claude/skills/session-wrap-up/check_time_log.py               # OK
   python -m finsync.api --openapi | diff - web/openapi.json             # empty
   cd web && npm run lint && npm test && npm run build                   # no errors
   ```

   Re-run each evaluation the release notes quote from its cache or dataset (for example `python -m finsync.evaluation` and `python -m finsync.evaluation.hybrid` without `--call-llm`) and check that the numbers equal the committed result file; a difference stops the package.
3. **Criteria.** Go through the milestone file line by line. For each: the evidence, or what is missing. Ask the author about a criterion whose evidence is their own step (a demo dry run, a real-phone test, reading a report) instead of assuming it.
4. **Release notes.** Write `docs/releases/vX.Y.Z.md` from the ticked criteria, the commits since the previous tag (`git log vPREV..HEAD --oneline`) and the result files; known limitations come from the open lines and the docs' "not built" notes, never left out to make the release look complete.
5. **Guides.** Update the API reference, the security status and the getting-started guide where the milestone changed them; run the docs checker again.
6. **Tag command.** In the report, the commands for the author after the merge:

   ```bash
   git checkout main && git pull
   git tag -a vX.Y.Z -m "MN: <milestone title>" <merge commit>
   git push origin vX.Y.Z
   ```

7. **Handover.** The release notes and the merge commit are the input of the supervisor-status-email skill; the e-mail is drafted after the author has merged, so it can name the tag and the commit.

## Self-check

- Every ticked line in the milestone file has a link or a test name.
- Every number in the release notes appears in a command output of this session or in a linked result file.
- The release notes list the known limitations and the open criteria.
- `git diff --stat` shows only the milestone file, the release notes and their README, the guides and the logs.

## Human checkpoints

1. **Before** ticking a criterion that rests on the author's own step: ask the author.
2. **Before** the release notes go into the pull request: the author reads the criteria table.
3. **After** the merge: the author sets and pushes the tag, then the status e-mail is drafted.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-24 | First version, from the M1 package (v0.2.0, 2026-11-02) and the Friday step of the [M2 closing schedule](../../../docs/planning/m2-closing-schedule.md), before the M2 package of 2026-11-27. |
