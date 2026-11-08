# `finsync/evaluation/` — measuring matching and categorization

Tooling for the evaluation in [docs/evaluation/](../../docs/evaluation/README.md). It is not used by the API.

| File | Contents |
| --- | --- |
| `generate.py` | Scenario-based generator of the synthetic matching dataset (`python -m finsync.evaluation.generate`) |
| `generate_categories.py` | Generator of the synthetic, labelled categorization dataset (`python -m finsync.evaluation.generate_categories`) |
| `runner.py` | Replays a split through a fresh database, scores the events against the labels, and the store-every-row baseline |
| `__main__.py` | The report (`python -m finsync.evaluation [--out docs/evaluation/results/<date>-matching.md]`): threshold sweep on dev, test split at the chosen threshold in arrival and reverse order, false merges and missed duplicates listed |

## Rules for this folder

- Synthetic data only; the generator is deterministic for a seed, so a result can be reproduced from the commit id.
- The matcher never sees the labels (`true_event`, `scenario`, `kind`); only the runner reads them. The same holds for the categorizer and `true_category`, `usual_category`, `ambiguity`.
