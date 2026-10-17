# `finsync/evaluation/` — measuring matching

Tooling for the evaluation in [docs/evaluation/](../../docs/evaluation/README.md). It is not used by the API.

| File | Contents |
| --- | --- |
| `generate.py` | Scenario-based generator of the synthetic matching dataset (`python -m finsync.evaluation.generate`) |

Planned: the runner (`python -m finsync.evaluation`) that replays a split through the service and reports the metrics against the store-every-row baseline.

## Rules for this folder

- Synthetic data only; the generator is deterministic for a seed, so a result can be reproduced from the commit id.
- The matcher never sees the labels (`true_event`, `scenario`, `kind`); only the runner reads them.
