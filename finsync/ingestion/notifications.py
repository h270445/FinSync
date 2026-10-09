from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re


@dataclass(frozen=True)
class ParsedNotification:
    amount: Decimal
    currency: str
    merchant_or_counterparty: str
    happened_at: datetime
    description: str


_CARD_PATTERN = re.compile(
    r"^CARD PURCHASE\s+(?P<amount>[+-]?\d+[\d,.]*)\s+(?P<currency>[A-Z]{3})\s+at\s+(?P<merchant>.+?)\s+on\s+(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})$"
)
_TRANSFER_PATTERN = re.compile(
    r"^Incoming transfer\s+(?P<amount>[+-]?\d+[\d,.]*)\s+(?P<currency>[A-Z]{3})\s+from\s+(?P<party>.+?)\s+(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})$"
)


def _parse_amount(raw: str) -> Decimal:
    normalized = raw.replace(",", "")
    try:
        amount = Decimal(normalized)
    except InvalidOperation as error:
        raise ValueError("Invalid notification amount format") from error

    if amount == 0:
        raise ValueError("Amount cannot be zero")
    return amount


def _parse_timestamp(raw: str) -> datetime:
    return datetime.strptime(raw, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)


def parse_notification(message: str) -> ParsedNotification:
    for pattern, source in ((_CARD_PATTERN, "card_purchase"), (_TRANSFER_PATTERN, "incoming_transfer")):
        match = pattern.match(message.strip())
        if not match:
            continue

        amount = _parse_amount(match.group("amount"))
        currency = match.group("currency")
        party = match.group("merchant") if "merchant" in match.groupdict() else match.group("party")
        happened_at = _parse_timestamp(match.group("timestamp"))
        description = f"{source}:{party}"

        return ParsedNotification(
            amount=amount,
            currency=currency,
            merchant_or_counterparty=party,
            happened_at=happened_at,
            description=description,
        )

    raise ValueError("Unsupported notification format")
