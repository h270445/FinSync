"""Group merchant → category rules: the first, deterministic layer of the hybrid categorizer.

A group's members name a merchant and its category on the W8 settings screen ("SPAR" → groceries).
A rule applies to a record when every word of its key is a word of the record's merchant, so the rule
"SPAR" also covers "SPAR 0123 BUDAPEST" and "Spar Magyarország Kft.". When several rules apply, the one
with the most words wins ("MOL Bubi" before "MOL"), then the oldest. Rules come before the keyword
rules ([categorization design](../../docs/design/categorization.md#order-of-precedence)).
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable
import unicodedata

from finsync.matching.normalize import merchant_tokens

# The allowed categories, the same nine as the labelled categorization dataset
# (finsync/evaluation/generate_categories.py; a test keeps the two lists equal).
CATEGORIES = (
    "groceries",
    "eating_out",
    "transport",
    "housing_utilities",
    "health",
    "clothing",
    "entertainment",
    "household",
    "other",
)

_MAX_LABEL_LENGTH = 80
# The same word split as merchant_tokens() in finsync/matching/normalize.py.
_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class MerchantRule:
    id: int
    merchant_key: str
    category: str


def merchant_key(merchant: str) -> str:
    """The normalised words of a merchant name in their typed order: "Spar 0123 Kft." -> "spar"."""
    kept = merchant_tokens(merchant)  # drops store numbers and legal suffixes
    words: list[str] = []
    for word in _NON_ALPHANUMERIC.sub(" ", ascii_lower(merchant)).split():
        if word in kept and word not in words:
            words.append(word)
    return " ".join(words)


def ascii_lower(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def validate_rule(merchant: str, category: str) -> tuple[str, str, str]:
    """(label, key, category) for a rule a member typed; ValueError with the reason otherwise."""
    label = merchant.strip()
    if not label:
        raise ValueError("merchant is required")
    if len(label) > _MAX_LABEL_LENGTH:
        raise ValueError(f"merchant is at most {_MAX_LABEL_LENGTH} characters")
    key = merchant_key(label)
    if not key:
        raise ValueError("merchant must contain a word other than numbers and company suffixes")
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of: {', '.join(CATEGORIES)}")
    return label, key, category


def find_rule(rules: Iterable[MerchantRule], merchant: str | None) -> MerchantRule | None:
    """The rule that applies to a merchant name, or None."""
    words = merchant_tokens(merchant)
    if not words:
        return None
    applicable = [rule for rule in rules if set(rule.merchant_key.split()) <= words]
    if not applicable:
        return None
    return min(applicable, key=lambda rule: (-len(rule.merchant_key.split()), rule.id))
