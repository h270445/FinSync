# `finsync/categorization/` — transaction categorization

Assigns a spending category to a transaction from its description and merchant text.

| File | Contents |
| --- | --- |
| `rules.py` | `categorize_transaction()`: keyword rules for `groceries`, `transport`, `entertainment`, `housing_utilities` (called `housing` before 2026-11-19), else `other`; keywords match whole words only ("bus" does not match "business") |
| `merchant_rules.py` | The group's merchant → category rules, the hybrid categorizer's first layer: `CATEGORIES` (the nine allowed categories), `merchant_key()`, `validate_rule()`, `find_rule()` (all words of the key in the merchant; most words wins) |
| `dictionary.py` | The built-in Hungarian merchant and keyword dictionary (`DICTIONARY_VERSION`, `MERCHANTS`, `KEYWORDS`, `find_merchant()`, `keyword_categories()`); mixed-assortment merchants (Tesco, dm, eMAG) are marked and give only a `low` answer |
| `hybrid.py` | `categorize_record()`: the hybrid categorizer's deterministic layer; returns a `CategoryDecision` (category, source, confidence) |
| `own_accounts.py` | Transfers within the group: `own_account_key()` (account by 8+ digits, otherwise name), `is_transfer()` |
| `__init__.py` | Public names: `CATEGORIES`, `DICTIONARY_VERSION`, `TRANSFER`, `CategoryDecision`, `MerchantRule`, `OwnAccount`, `categorize_record`, `categorize_transaction`, `find_rule`, `is_transfer`, `merchant_key`, `own_account_key`, `validate_rule` |

Order today (since 2026-11-19): a record naming one of the group's own accounts is a `transfer`; otherwise `categorize_record()` decides: the group's merchant rule, then a clear merchant of the dictionary, then Hungarian or English keywords, then a mixed-assortment merchant's usual category (`low`), otherwise `other` with source `none` (where the LLM layer will plug in, Nov 23–27). The core applies this when it stores a record (`_classify` in `finsync/core/service.py`), so every input path gets it. Today only the category is stored; source and confidence are returned for the LLM layer and the measurement. `categorize_transaction()` in `rules.py` is unchanged and stays the measured baseline.

The rule-based categorizer is the baseline for the planned comparison with an LLM-based categorizer ([evaluation plan](../../docs/evaluation/evaluation-plan.md)).

## Rules for this folder

- Every categorizer exposes the same signature, so the rule-based and LLM-based versions can be evaluated on the same labelled dataset.
- An LLM categorizer's output is untrusted input: it must be checked against the allowed category list before use.
