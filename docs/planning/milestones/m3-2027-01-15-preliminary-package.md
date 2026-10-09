# M3 — Preliminary final package

- Deadline: 2027-01-15 23:59
- Tag: `v0.9.0`
- Status: planned
- Internal target: 2027-01-08
- Feature freeze: 2026-12-18

## Expected result (course)

Runnable system, test and measurement results, a short professional report, known limitations, and the planned continuation for Szakdolgozat II.

## Acceptance criteria

- [ ] A person new to the project can install, run, test and evaluate the system using only [getting-started.md](../../guides/getting-started.md) (tried on a clean machine).
- [ ] All tests pass on the tagged commit.
- [ ] Final matching, categorization and security results with the commit id and command are in `docs/evaluation/results/`.
- [ ] Documentation describes the actual implementation (every design marked Accepted or updated to match).
- [ ] Known limitations are listed.
- [ ] The Szakdolgozat II. plan (refinement and thesis writing) is written.
- [ ] [AI usage](../../ai-usage.md) is complete: significant uses and how their output was checked.

## Checklist

- [ ] Full matching dataset, thresholds tuned on the development split, results on the test split.
- [ ] LLM vs rule categorization measured on the same dataset (accuracy, error patterns, latency, cost).
- [ ] Security and privacy evaluation results.
- [ ] Edge-case tests (late manual entries, rounded amounts, time zones).
- [ ] Clean-machine setup test.
- [ ] Short professional report (`docs/report.md` or PDF linked from `docs/README.md`).
- [ ] Release notes, tag `v0.9.0`, e-mail.
