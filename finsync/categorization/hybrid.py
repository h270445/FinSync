"""The hybrid categorizer's deterministic layer: group rules, then the built-in dictionary.

`categorize_record()` decides a record's category from its merchant and description, and says where the
answer came from and how sure it is, so the planned LLM layer (Nov 23–27) can be asked only when this
layer gives nothing or only a `low` answer ([design](../../docs/design/categorization.md#order-of-precedence)).

The first step that answers wins:

1. **Group merchant rule** (W8 settings, merchant_rules.py): `high`. The group's own choice always wins.
2. **Clear merchant** from the dictionary (dictionary.py): `high`.
3. **Keywords** in the merchant and description: `high` when they name one category, `low` when they
   name several (then the usual category of a mixed merchant is preferred if it is among them, otherwise
   the keyword that occurs first). So "Tesco" with "zokni" is clothing, not the usual groceries.
4. **Mixed-assortment merchant** from the dictionary: its usual category, `low`.
5. Nothing: `other` with source `none` and `low`, the place where the LLM layer will plug in.

Transfers to the group's own accounts are decided before this, in the core (own_accounts.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from finsync.categorization.dictionary import find_merchant, keyword_categories
from finsync.categorization.merchant_rules import MerchantRule, find_rule

HIGH = "high"
LOW = "low"

# Where a category came from, the `category_source` values of the design that this layer produces.
SOURCE_MERCHANT_RULE = "merchant_rule"
SOURCE_DICTIONARY = "dictionary"
SOURCE_KEYWORD = "keyword"
SOURCE_NONE = "none"

FALLBACK_CATEGORY = "other"


@dataclass(frozen=True)
class CategoryDecision:
    category: str
    source: str
    confidence: str


def categorize_record(
    merchant: str | None, description: str | None, rules: Iterable[MerchantRule] = ()
) -> CategoryDecision:
    """The deterministic category of a record. Merchant lookups use the merchant, or the description
    when there is no merchant; keywords are searched in both."""
    name = merchant or description
    rule = find_rule(rules, name)
    if rule is not None:
        return CategoryDecision(rule.category, SOURCE_MERCHANT_RULE, HIGH)

    entry = find_merchant(name)
    if entry is not None and not entry.mixed:
        return CategoryDecision(entry.category, SOURCE_DICTIONARY, HIGH)

    found = keyword_categories(f"{merchant or ''} {description or ''}")
    if len(found) == 1:
        return CategoryDecision(found[0], SOURCE_KEYWORD, HIGH)
    if found:
        usual = entry.category if entry is not None and entry.category in found else found[0]
        return CategoryDecision(usual, SOURCE_KEYWORD, LOW)

    if entry is not None:
        return CategoryDecision(entry.category, SOURCE_DICTIONARY, LOW)
    return CategoryDecision(FALLBACK_CATEGORY, SOURCE_NONE, LOW)
