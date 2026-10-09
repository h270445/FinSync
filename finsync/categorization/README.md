# `finsync/categorization/` — transaction categorization

Assigns a spending category to a transaction from its description and merchant text.

| File | Contents |
| --- | --- |
| `rules.py` | `categorize_transaction()`: keyword rules for `groceries`, `transport`, `entertainment`, `housing`, else `other` |
| `__init__.py` | Public name: `categorize_transaction` |

The rule-based categorizer is the baseline for the planned comparison with an LLM-based categorizer ([evaluation plan](../../docs/evaluation/evaluation-plan.md)).

## Rules for this folder

- Every categorizer exposes the same signature, so the rule-based and LLM-based versions can be evaluated on the same labelled dataset.
- An LLM categorizer's output is untrusted input: it must be checked against the allowed category list before use.
