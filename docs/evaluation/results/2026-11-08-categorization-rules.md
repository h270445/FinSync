# Categorization evaluation: rule-based baseline

- Code: commit `v0.2.0-24-g37c4b8d`
- Command: `python -m finsync.evaluation.categories --dataset tests/data/categorization_eval.csv`
- Dataset: `tests/data/categorization_eval.csv` (sha256 `a514e33d4f79`), 200 items, dev 101, test 99
- Label mapping: the rules' `housing` is scored as `housing_utilities`; the other four labels are the same in both lists. The rules never return `eating_out`, `health`, `clothing` or `household`.

The rules never abstain, so the abstention rate is 0 % and every miss is a confident wrong answer.

## Accuracy

| Group | Dev items | Dev accuracy | Test items | Test accuracy |
| --- | --- | --- | --- | --- |
| all | 101 | 13.9% | 99 | 13.1% |
| clear | 62 | 11.3% | 68 | 13.2% |
| ambiguous | 39 | 17.9% | 31 | 12.9% |
| scenario: clear_merchant | 27 | 11.1% | 23 | 21.7% |
| scenario: mixed_merchant | 29 | 13.8% | 21 | 14.3% |
| scenario: mixed_with_detail | 17 | 17.6% | 13 | 15.4% |
| scenario: unfamiliar_merchant | 9 | 11.1% | 21 | 9.5% |
| scenario: hungarian_description | 9 | 0.0% | 11 | 0.0% |
| scenario: cryptic_text | 10 | 30.0% | 10 | 10.0% |

## Ceiling on mixed-assortment merchants

Without detail, the best a merchant-only categorizer can do is the merchant's usual category. Scored against the labels, that reaches 48.3% on dev and 47.6% on test (`mixed_merchant` items only). The shares behind these labels are the author's assumptions (see [datasets.md](../datasets.md)).
