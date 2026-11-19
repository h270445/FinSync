"""Transfers within the group: records whose counterparty is one of the group's own accounts.

A group lists its own accounts and counterparties on the W8 settings screen: account numbers or IBANs,
and the names the bank prints for the members ("KISS ANNA"). A record that names one of them is money
moved inside the group, so it gets the direction and category `transfer` and is left out of spending
and income totals ([categorization design](../../docs/design/categorization.md#money-transfers)).

- An entry with at least 8 digits is an **account**: it matches when its digits appear, in order and
  without gaps, among the digits of the record's merchant and description ("11773016-01234567" also
  matches "HU42 1177 3016 0123 4567 0000 0000").
- Any other entry is a **name**: it matches when all its words are words of the record's merchant or
  description, after the same normalisation as merchant rules (lowercase, no accents).
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from finsync.categorization.merchant_rules import ascii_lower

TRANSFER = "transfer"
ACCOUNT = "account"
NAME = "name"

_MIN_ACCOUNT_DIGITS = 8
_MAX_LABEL_LENGTH = 80
_NON_DIGIT = re.compile(r"\D+")
_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True)
class OwnAccount:
    id: int
    kind: str
    match_key: str


def own_account_key(label: str) -> tuple[str, str, str]:
    """(label, kind, key) for an entry a member typed; ValueError with the reason otherwise."""
    label = label.strip()
    if not label:
        raise ValueError("label is required: an account number or a name")
    if len(label) > _MAX_LABEL_LENGTH:
        raise ValueError(f"label is at most {_MAX_LABEL_LENGTH} characters")
    digits = _NON_DIGIT.sub("", label)
    if len(digits) >= _MIN_ACCOUNT_DIGITS:
        return label, ACCOUNT, digits
    words = _words(label)
    if not words:
        raise ValueError("label must contain a name or an account number of at least 8 digits")
    return label, NAME, " ".join(words)


def is_transfer(entries: Iterable[OwnAccount], merchant: str | None, description: str | None) -> bool:
    text = f"{merchant or ''} {description or ''}"
    digits = _NON_DIGIT.sub("", text)
    words = set(_words(text))
    for entry in entries:
        if entry.kind == ACCOUNT and entry.match_key in digits:
            return True
        if entry.kind == NAME and set(entry.match_key.split()) <= words:
            return True
    return False


def _words(text: str) -> list[str]:
    found: list[str] = []
    for word in _NON_ALPHANUMERIC.sub(" ", ascii_lower(text)).split():
        if not word.isdigit() and word not in found:
            found.append(word)
    return found
