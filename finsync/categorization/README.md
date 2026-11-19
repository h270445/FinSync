# `finsync/categorization/` — transaction categorization

Assigns a spending category to a transaction from its description and merchant text.

| File | Contents |
| --- | --- |
| `rules.py` | `categorize_transaction()`: keyword rules for `groceries`, `transport`, `entertainment`, `housing`, else `other`; keywords match whole words only ("bus" does not match "business") |
| `merchant_rules.py` | The group's merchant → category rules, the hybrid categorizer's first layer: `CATEGORIES` (the nine allowed categories), `merchant_key()`, `validate_rule()`, `find_rule()` (all words of the key in the merchant; most words wins) |
| `__init__.py` | Public names: `CATEGORIES`, `MerchantRule`, `categorize_transaction`, `find_rule`, `merchant_key`, `validate_rule` |

Order today: the group's merchant rule, if one applies, otherwise the keyword rules. The core applies the rules when it stores a record (`_store_and_match`), so every input path gets them.

The rule-based categorizer is the baseline for the planned comparison with an LLM-based categorizer ([evaluation plan](../../docs/evaluation/evaluation-plan.md)).

## Rules for this folder

- Every categorizer exposes the same signature, so the rule-based and LLM-based versions can be evaluated on the same labelled dataset.
- An LLM categorizer's output is untrusted input: it must be checked against the allowed category list before use.
