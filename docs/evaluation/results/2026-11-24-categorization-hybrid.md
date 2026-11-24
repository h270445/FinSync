# Categorization evaluation: hybrid categorizer (dictionary + LLM + abstention)

- Code: commit `a590623`, dictionary `hu-1`, prompt `llm-1`
- Command: `python -m finsync.evaluation.hybrid`
- Dataset: `tests/data/categorization_eval.csv` (sha256 `35436663b6fa`), 200 items, dev 101, test 99
- LLM: `claude-haiku-5-5`, 5 samples per record, JSON schema output (Anthropic API: effort `low`, no temperature, current models do not take one; an OpenAI-compatible server: its default sampling); answers cached in `docs/evaluation/results/llm-cache/categorization-claude-haiku-5-5-llm-1.json`; 365 new calls in this run; report date 2026-11-24
- Group merchant rules: none (the dataset has no group), so the deterministic layer is the built-in dictionary.

## Decision rule (fixed before the run)

The LLM is asked only for records where the dictionary gives nothing or only a `low` answer. Its confidence is the share of the 5 samples that name the most frequent category. A record is *settled* when the dictionary answers `high` or the LLM share reaches the threshold; otherwise it is *Bizonytalan* (uncertain) and keeps a suggestion that a member confirms. Rule: the highest coverage at which at most 5% of the settled dev answers are wrong; ties go to the higher threshold; if no threshold meets the target, the highest threshold is used. The test split was categorized only after the threshold was chosen and did not influence it.

## 1. Coverage-accuracy curve (dev split)

| Threshold | Coverage (settled) | Accuracy of settled | Wrong and settled | Bizonytalan |
| --- | --- | --- | --- | --- |
| dictionary alone | 58.4% | 100.0% | 0 | 42 |
| 0.20 | 78.2% | 94.9% | 4 | 22 |
| 0.40 | 77.2% | 96.2% | 3 | 23 |
| 0.60 | 75.2% | 97.4% | 2 | 25 |
| 0.80 | 74.3% | 97.3% | 2 | 26 |
| 1.00 | 73.3% | 97.3% | 2 | 27 |

Chosen: **0.40**.

## 2. Dev and test at the chosen threshold, next to the baselines

| Method | Split | Items | Coverage (settled) | Accuracy of settled | Wrong and settled | Bizonytalan | Accuracy of shown category |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Rule-based baseline | dev | 101 | 100.0% | 13.9% | 87 | 0 | 13.9% |
| Rule-based baseline | test | 99 | 100.0% | 13.1% | 86 | 0 | 13.1% |
| Dictionary layer alone | dev | 101 | 58.4% | 100.0% | 0 | 42 | 76.2% |
| Dictionary layer alone | test | 99 | 63.6% | 100.0% | 0 | 36 | 76.8% |
| Hybrid @ 0.40 (chosen on dev) | dev | 101 | 77.2% | 96.2% | 3 | 23 | 78.2% |
| Hybrid @ 0.40 (chosen on dev) | test | 99 | 79.8% | 93.7% | 5 | 20 | 80.8% |

*Accuracy of shown category* counts every record with the category the app would show, settled or suggested (`uncategorized` counts as wrong). The rule-based baseline is the keyword categorizer of the [Nov 8 report](2026-11-08-categorization-rules.md).

## 3. Test split by scenario (chosen threshold)

| Scenario | Items | Coverage | Accuracy of settled | Wrong and settled | Bizonytalan |
| --- | --- | --- | --- | --- | --- |
| clear_merchant | 23 | 100.0% | 100.0% | 0 | 0 |
| mixed_merchant | 21 | 52.4% | 54.5% | 5 | 10 |
| mixed_with_detail | 13 | 100.0% | 100.0% | 0 | 0 |
| unfamiliar_merchant | 21 | 100.0% | 100.0% | 0 | 0 |
| hungarian_description | 11 | 100.0% | 100.0% | 0 | 0 |
| cryptic_text | 10 | 0.0% | n/a | 0 | 10 |

## 4. Overlap of the dictionary and the dataset

The dictionary was written from general knowledge, but it names the same large Hungarian chains as the synthetic dataset, so its numbers on records with a known merchant are optimistic. Records whose merchant (or description, without a merchant) is a dictionary merchant are reported apart:

| Group | Split | Items | Coverage | Accuracy of settled | Wrong and settled |
| --- | --- | --- | --- | --- | --- |
| merchant in dictionary | dev | 74 | 82.4% | 95.1% | 3 |
| merchant not in dictionary | dev | 27 | 63.0% | 100.0% | 0 |
| merchant in dictionary | test | 60 | 83.3% | 90.0% | 5 |
| merchant not in dictionary | test | 39 | 74.4% | 100.0% | 0 |

## 5. Latency and cost of the LLM layer

- Records sent to the LLM: 78 of 200 (42 dev, 36 test), 390 answers, 365 distinct calls (records with the same text share cached answers)
- Latency per call: median 0.98 s, worst 2.56 s
- Latency per record (5 calls one after another): median 5.11 s, worst 10.07 s; the calls are independent, so in parallel a record takes about one call's time
- Tokens: 317905 in, 4394 out
- Cost: $0.0340 in total, $0.0004 per record sent to the LLM, $0.0170 per 100 records of this mix (prices of 2026-11-03)

Latency and token counts are those of the first, uncached call of each answer.

## 6. Wrong and settled answers (test split, chosen threshold)

| Item | Scenario | Merchant | Description | True | Given | Source |
| --- | --- | --- | --- | --- | --- | --- |
| C0050 | mixed_merchant |  | VÁSÁRLÁS KÁRTYÁVAL TESCO ÁRUHÁZ 41021 | entertainment | groceries | llm |
| C0088 | mixed_merchant |  | TESCO Áruház 41021 | household | groceries | llm |
| C0096 | mixed_merchant |  | LIDL 0231 | clothing | groceries | llm |
| C0098 | mixed_merchant |  | SPAR Magyarország Kft. | other | groceries | llm |
| C0140 | mixed_merchant |  | VÁSÁRLÁS KÁRTYÁVAL AUCHAN SOROKSAR | entertainment | groceries | llm |
