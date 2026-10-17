from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
import re
import unicodedata
from zoneinfo import ZoneInfo

# Calendar days are compared in the household's time zone, so a purchase at 23:30 local time
# is not moved to the next day by the UTC conversion.
LOCAL_TIME_ZONE = ZoneInfo("Europe/Budapest")

_LEGAL_SUFFIXES = frozenset({"kft", "zrt", "nyrt", "bt", "kkt", "ltd", "gmbh", "inc"})
_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


def direction_of(amount: Decimal) -> str:
    return "expense" if amount < 0 else "income"


def whole_units(amount: Decimal) -> Decimal:
    """Absolute amount rounded to a whole currency unit (1234.56 -> 1235)."""
    return abs(amount).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def local_date(happened_at: datetime, precision: str) -> date:
    """The calendar day of a record. A day-precision record already stores its own date."""
    if precision == "day":
        return happened_at.date()
    return happened_at.astimezone(LOCAL_TIME_ZONE).date()


def merchant_tokens(text: str | None) -> frozenset[str]:
    """Lowercase, accent-free tokens without store numbers and legal suffixes."""
    if not text:
        return frozenset()
    decomposed = unicodedata.normalize("NFKD", text.lower())
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    tokens = _NON_ALPHANUMERIC.sub(" ", ascii_text).split()
    return frozenset(token for token in tokens if not token.isdigit() and token not in _LEGAL_SUFFIXES)
