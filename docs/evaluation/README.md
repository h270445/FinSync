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
