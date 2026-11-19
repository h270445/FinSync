# 0011. LLM categorization layer: one provider behind an interface, confidence from five samples

- Status: Proposed (layer and measurement runner built 2026-11-19; provider, budget and threshold rule await the author's approval)
- Date: 2026-11-19

## Context

The hybrid categorizer's deterministic layer (group merchant rules, then the built-in Hungarian dictionary, [design](../../design/categorization.md#order-of-precedence)) answers `high` for clear merchants and keywords, and only `low` or nothing for mixed-assortment merchants, unfamiliar merchants and cryptic payment texts. The supervisor asked (2026-11-16) for the deterministic layer + a model/LLM layer + an explicit abstention threshold ("Bizonytalan") to be measured together: coverage-accuracy curve, latency and cost.

The [technology stack](../technology-stack.md) planned one provider's official SDK, called only from `finsync.categorization`, with the provider chosen in November. The [design](../../design/categorization.md#llm-rules) planned temperature 0 with structured output, and confidence from token log-probabilities, or from the share of the top answer in five samples where log-probabilities are not available. Current Anthropic models take no `temperature` (a non-default value is rejected) and expose no log-probabilities.

## Decision

1. **Provider and model (proposed):** Anthropic, `claude-haiku-5-5` (USD 0.10 / 0.50 per million input / output tokens on 2026-11-03), through the official `anthropic` Python SDK, effort `low`, the answer constrained by a JSON schema whose only field is `category` with the nine allowed categories plus `unknown`. The provider sits behind the `LlmClient` interface (`finsync/categorization/llm.py`), so another provider or model is one class.
2. **Only what is needed leaves the system:** one record's merchant, description and amount with currency. No member, group or account data. The measurement uses only the synthetic dataset.
3. **Untrusted output:** an answer that is not valid JSON naming an allowed category counts as `unknown`; a refusal counts as `unknown`.
4. **When it is asked:** only when the deterministic layer gives nothing or a `low` answer; a `high` answer is never sent.
5. **Confidence from five samples:** five answers per record; the confidence is the share of all five (`unknown` included) that name the most frequent category, so it is one of 0, 0.2, ..., 1.0.
6. **Abstention:** at or above the threshold the LLM category is settled (`llm`, `high`); below it the record is "Bizonytalan" and keeps a `low` suggestion (the dictionary's, else the LLM's top answer, else `uncategorized`).
7. **Threshold rule (proposed), fixed before the run:** on the dev split, the highest coverage at which at most 5 % of the settled answers are wrong; ties go to the higher threshold; if no threshold meets the target, the highest threshold. The test split is categorized once, after the choice ([dev-test-evaluation](../../../.claude/skills/dev-test-evaluation/SKILL.md)).
8. **Cache:** every answer is cached by model, prompt version, record text and sample number. In the measurement the cache file is committed under `docs/evaluation/results/llm-cache/`, so a re-run gives the same numbers without new calls; the runner calls the provider only with `--call-llm`.
9. **Not yet in the live path:** the layer is used by the measurement only. Wiring it into the core, asynchronously (a record is stored at once with the deterministic result and updated when the LLM answers) and off by default, comes with storing `category_source` and `category_confidence` (Nov 23–27).

## Consequences

- Five calls per record cost five times one call; at the proposed model the 78 records of the dataset that need the LLM are about 390 calls, estimated below USD 0.05 (`python -m finsync.evaluation.hybrid --estimate`).
- The confidence has only five levels, so the coverage-accuracy curve has five points; more samples would give a finer curve at a linear cost.
- Self-reported confidence is not used, and agreement with a dictionary `low` answer is not used as a bonus in the first measurement; both can be compared later on dev.
- The `anthropic` package is a new dependency, imported only when the provider is called, so the tests run without network or key.
- A provider change needs a new answer cache and a new measurement report; old reports stay valid for their model and prompt version.
