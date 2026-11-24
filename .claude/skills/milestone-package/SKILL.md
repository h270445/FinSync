---
name: milestone-package
description: Use when a FinSync milestone package is put together (M2 preliminary package and close, M3, M4), before the status e-mail. Runs every gate on the commit to be submitted, walks the acceptance criteria with evidence, writes the release notes (docs/releases/vX.Y.Z.md) and the fix log, and prepares the tag for the author. Includes a release-notes checker.
---

# Milestone package

- Version: 1.0 (2026-11-24)
- Owner: Bence Varga
- Why it exists: each milestone ends with a package the supervisor reviews: a commit that passes every test, acceptance criteria ticked with evidence, release notes, a tag and an e-mail. Three of them fall within two months (M2 preliminary package on 2026-11-27 and close on 2026-12-04, M3 on 2027-01-15, M4 on 2027-01-30). Until now only a schedule line and the four steps in [milestones/README.md](../../../docs/planning/milestones/README.md) described it; the [supervisor-status-email](../supervisor-status-email/SKILL.md) skill takes the release notes as input, but nothing said how they are made or checked. Writing the notes from memory risks claims that the commit does not hold.

## Input

- The milestone (M2, M3, M4) and the stage: **package** (everything ready for review, no tag yet; M2's preliminary package of Nov 27) or **release** (the author merged, the tag is set; M2's close on Dec 4, M3, M4).
- The milestone file in `docs/planning/milestones/`, the previous tag (`git tag`), the open pull requests (`gh pr list`), the supervisor's open actions in `docs/planning/supervisor-feedback.md`, and for M4 the M3 feedback.

## Output

1. `docs/releases/vX.Y.Z.md` from the template in [releases/README.md](../../../docs/releases/README.md), a row in its index, and for M4 `docs/releases/fix-log.md`.
2. The milestone file with every acceptance criterion and checklist line either ticked with its evidence or annotated with what is open and where it moved; `Status:` updated.
3. A short report in the reply: the gate table (command, result line, commit), the criterion–evidence table, what is open, the tag command for the author, and what the status e-mail needs.

## Prohibitions

- **Never create, push, move or delete a tag** without the author's explicit go in the same session. The author tags the merged `main` commit; an existing tag is never moved (a fix gets the next patch version).
- Never claim in the notes what the commit does not hold: "works" only for merged, tested work with a test, a result file or a screen behind it. Planned work goes to "Known limitations" or the next milestone, never to "What works".
- Never tick a criterion that is partly met (the session-wrap-up rule); write what is done in brackets with the date.
- Never copy a number into the notes that was not produced by a command on this commit or read from a committed result file; never edit a committed result file or the notes of an earlier tag (a correction goes into the next notes or the fix log).
- Never hide a failed or skipped gate. A gate that cannot run here (PostgreSQL, Android, the browser) is reported as not run, with the last commit on which it passed.
- Synthetic data only in commands and examples; no e-mail address, token or account number; no model identifier except the measured product setting already named in a result file.
- Never send the e-mail; the [supervisor-status-email](../supervisor-status-email/SKILL.md) skill drafts it and the author sends it.

## Steps

### 1. Scope

1. Read the milestone file and list each acceptance criterion and checklist line with its current state.
2. Collect the changes since the previous tag: `git log <previous tag>..origin/main --merges --format='%s'` and the open pull requests that the package depends on. A package built on unmerged work names those pull requests; the author merges them first, in order.
3. List the supervisor's open actions that this milestone was asked to answer.

### 2. Gates on the commit to be submitted

Run on a clean tree (`git status --short` empty apart from untracked IDE folders) and write the commit id (`git rev-parse HEAD`) next to every result.

```bash
python -m unittest discover -s tests                        # count and OK
python tests/run_on_postgres.py <url>                       # when a PostgreSQL 16 is reachable; otherwise "not run"
cd web && npm ci && npm run lint && npm test && npm run build && cd ..
python .claude/skills/docs-and-comments/check_docs.py       # OK
python -m finsync.api --openapi | diff - web/openapi.json   # empty
python -m finsync.evaluation --out <tmp>/matching.md        # the same numbers as the result file the notes quote (non-LLM runners)
```

Every result file the notes quote is reproduced this way, or from its LLM answer cache with no new calls, and the diff is reported. The Android unit tests and the emulator run happen only on the author's computer ([android-emulator-e2e](../android-emulator-e2e/SKILL.md)); report the date and commit of the last run if this session cannot run them.

### 3. Fresh clone (M3 and M4; optional for M2)

Clone the commit into an empty temporary folder and follow [getting-started.md](../../../docs/guides/getting-started.md) word for word: virtual environment, install, tests, API, web app. Every step that needed something the guide does not say is a fix to the guide in this session. M3's first criterion asks for this on a clean machine; a fresh clone in this environment is the evidence until the author tries it on another computer.

### 4. Acceptance criteria with evidence

For each criterion: the evidence (test name, result file, doc section, PR) or what is missing. A missing item is either finished in this session (if small and in scope) or moved: the author decides (checkpoint 1), the roadmap gets a change-log row, the next milestone file gets the item. Also check that the docs the milestone names describe the code: the endpoint table of `docs/guides/api.md` against the paths in `web/openapi.json`, the status list of `docs/overview.md`, `docs/architecture/security-and-privacy.md`, `docs/guides/getting-started.md`, every ADR's status, and the [thesis map](../../../docs/thesis-map.md).

### 5. Release notes

Write `docs/releases/vX.Y.Z.md` from the template:

- **Title and header:** `# vX.Y.Z — Mn: <milestone name>`, `- Date:` (the day the package goes out), `- Commit:` "the `main` commit tagged `vX.Y.Z` (the merge of #N); the full id is in the e-mail and on the tag". The full id cannot be written into the file it identifies; [v0.2.0.md](../../../docs/releases/v0.2.0.md) set the pattern. In the package stage write "the `main` commit after #N is merged; the tag is set at the close".
- **What works:** one bullet per capability, each with the endpoint, screen or command and a link to its test or doc. Lead with what the milestone's expected result asks for.
- **How to verify:** the commands of step 2 with the counts just measured, the demo ([demo guide](../../../docs/guides/demo.md)) and where the sign-in comes from (the demo seed prints it; no password in the notes).
- **Measurements:** link every result file and copy its headline table with the baseline row, unchanged.
- **Known limitations:** honest and specific: open criteria, gates not run, ADR consequences not yet done, known bugs with their files. A reviewer should not find a limitation the notes do not name.
- **Changes since the previous milestone:** the merged pull requests from step 1, `#N Title`, oldest first.

Add the index row in `docs/releases/README.md`. For M4, write `docs/releases/fix-log.md` from its template: one row per point of the M3 feedback, with the change and the commit or PR; a point not acted on says why.

Run the checker; it must print `OK` (in the release stage with `--release`):

```bash
python .claude/skills/milestone-package/check_release.py vX.Y.Z            # package stage
python .claude/skills/milestone-package/check_release.py vX.Y.Z --release  # after the author set the tag
```

### 6. Tag (release stage, the author)

After the author merged the session's pull request, give the commands, run on `main` at the merge commit:

```bash
git switch main && git pull
git tag -a vX.Y.Z -m "Mn: <milestone name>"
git push origin vX.Y.Z
git rev-parse vX.Y.Z^{commit}     # the full id for the e-mail
```

Then confirm `git rev-parse vX.Y.Z^{commit}` equals the merge commit, re-run the Python tests on the tag (`git worktree add <tmp> vX.Y.Z`), and set the milestone file's `Status:` to done in the next session's pull request.

### 7. Hand over to the e-mail

Start the [supervisor-status-email](../supervisor-status-email/SKILL.md) skill with the notes, the tag (or, in the package stage, the merge commit), the gate table and the criterion–evidence table. The e-mail's claims are the notes' claims.

## Self-check

- Every bullet in "What works" has a link, and every number in the notes appears in a gate output or a committed result file.
- `check_release.py` prints `OK`; `check_docs.py` prints `OK`.
- The milestone file has no unexplained open box: each is ticked, annotated, or moved with a roadmap change-log row.
- The leak search of the [session-wrap-up](../session-wrap-up/SKILL.md) skill finds nothing new in the notes.

## Human checkpoints

1. **Before** moving a criterion to a later milestone or dropping it: the author decides; the reason goes into the roadmap change log.
2. **Before** the tag: the author reads the notes and merges; only the author tags (or gives an explicit go).
3. **After** the supervisor's reply to the package: its points go through the [supervisor-feedback-intake](../supervisor-feedback-intake/SKILL.md) skill; for M3 they become the M4 fix log.

## Change log

| Version | Date | Change |
| --- | --- | --- |
| 1.0 | 2026-11-24 | First version, before the M2 preliminary package of 2026-11-27, from the M1 release (v0.2.0), the delivery steps in the milestones README and the M2 closing schedule. |
