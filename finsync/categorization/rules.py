from __future__ import annotations

import re

_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("groceries", ("tesco", "aldi", "lidl", "grocery", "market")),
    ("transport", ("uber", "bolt", "taxi", "bus", "train", "fuel")),
    ("entertainment", ("netflix", "spotify", "cinema", "subscription")),
    ("housing", ("rent", "mortgage", "housing", "utility", "electricity", "water")),
)

# Match keywords as whole words only, so "bus" does not match "business"
# and "rent" does not match "parent".
_CATEGORY_PATTERNS = tuple(
    (category, re.compile(r"\b(?:" + "|".join(map(re.escape, keywords)) + r")\b"))
    for category, keywords in _CATEGORY_KEYWORDS
)


def categorize_transaction(description: str) -> str:
    text = description.lower()
    for category, pattern in _CATEGORY_PATTERNS:
        if pattern.search(text):
            return category
    return "other"
