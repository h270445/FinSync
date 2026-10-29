# Evaluation

How FinSync's critical behaviour is measured, and the measured results.

| File | Contents |
| --- | --- |
| [evaluation-plan.md](evaluation-plan.md) | Methods and metrics for matching, categorization, and security and privacy |
| [datasets.md](datasets.md) | The labelled synthetic datasets: how they are generated, columns, scenarios, limits |
| [results/](results/) | One report per measurement (`YYYY-MM-DD-<topic>.md`) with the commit id, the command that produced it and the numbers |

Results are never edited after the fact; a re-run gets a new file.

| Result | Summary |
| --- | --- |
| [2026-10-18-matching.md](results/2026-10-18-matching.md) | Dataset v1: auto-link threshold 0.85 confirmed on dev; on test the matcher removes 8 of 12 double counts with no false merge in arrival order, one false merge in reverse order |
| [2026-10-18-matching-rules-2.md](results/2026-10-18-matching-rules-2.md) | Same data, merchant score over the shorter name (`rules-2`): 0.85 kept; on test 11 of 12 double counts removed, the last one waits for review, no false merge in arrival order |
| [2026-10-29-matching-rules-3.md](results/2026-10-29-matching-rules-3.md) | Dataset v2 (v1 plus 8 neighbour-day look-alike cases): the two reverse-order fixes compared on dev, `rules-3` (both on) and threshold 0.95 chosen; on test no false merge in either order, every unlinked true pair waits for review |
| [2026-10-29-matching-rules-3-v1.md](results/2026-10-29-matching-rules-3-v1.md) | `rules-3` on dataset v1, for comparison with Oct 18: no false merge in either order on test, 4 double counts (all in review) instead of 1 |
