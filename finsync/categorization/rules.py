from __future__ import annotations


def categorize_transaction(description: str) -> str:
    text = description.lower()
    if any(token in text for token in ("tesco", "aldi", "lidl", "grocery", "market")):
        return "groceries"
    if any(token in text for token in ("uber", "bolt", "taxi", "bus", "train", "fuel")):
        return "transport"
    if any(token in text for token in ("netflix", "spotify", "cinema", "subscription")):
        return "entertainment"
    if any(token in text for token in ("rent", "mortgage", "housing", "utility", "electricity", "water")):
        return "housing"
    return "other"
