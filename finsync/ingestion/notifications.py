from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re

from finsync.ingestion.local_time import local_to_utc


@dataclass(frozen=True)
class ParsedNotification:
    amount: Decimal
    currency: str
    merchant_or_counterparty: str
    # None when the text prints no time (OTP Bank); the time then comes from the phone's posted_at.
    happened_at: datetime | None
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
    # The text prints local time without an offset (ADR 0008).
    return local_to_utc(datetime.strptime(raw, "%Y-%m-%d %H:%M"))


# OTP Bank (Android app, 2026-10-27/28 spike): the text starts with the signed amount, a space as
# thousands separator and the currency ("Ft"); a transfer then has a comma and the counterparty, a
# card purchase a sentence with the merchant in capitals. No time is printed. The pattern is written
# from the masked shapes in docs/design/android-notification-spike.md; examples in tests are made up.
_OTP_AMOUNT = re.compile(
    r"^(?P<amount>[+-]\d{1,3}(?:[ \u00a0\u202f]\d{3})*(?:,\d{1,2})?)[ \u00a0](?P<currency>Ft|[A-Z]{3})(?P<rest>(?:,| ).*)$"
)
_CAPITALS = "A-ZÁÉÍÓÖŐÚÜŰ"
# A run of words written in capitals (digits, &, ., -, ' allowed), each with at least one capital letter.
_MERCHANT = re.compile(rf"(?<![^\s])([{_CAPITALS}0-9&.'-]*[{_CAPITALS}][{_CAPITALS}0-9&.'-]*(?: [{_CAPITALS}0-9&.'-]*[{_CAPITALS}][{_CAPITALS}0-9&.'-]*)*)(?![^\s.,!?])")


def _parse_otp(text: str) -> ParsedNotification | None:
    match = _OTP_AMOUNT.match(text.strip())
    if not match:
        return None
    amount = _parse_amount(match.group("amount").replace(" ", "").replace("\u00a0", "").replace("\u202f", "").replace(",", "."))
    currency = "HUF" if match.group("currency") == "Ft" else match.group("currency")
    rest = match.group("rest")
    if rest.startswith(","):
        party = rest[1:].strip().rstrip(".").strip()
        if not party:
            return None
        kind = "outgoing_transfer" if amount < 0 else "incoming_transfer"
    else:
        runs = [run.strip(".-'& ") for run in _MERCHANT.findall(rest)]
        runs = [run for run in runs if len(run) >= 2]
        if not runs:
            return None
        party = max(runs, key=len)
        kind = "card_purchase" if amount < 0 else "card_refund"
    return ParsedNotification(
        amount=amount, currency=currency, merchant_or_counterparty=party, happened_at=None, description=f"{kind}:{party}"
    )


def parse_notification(message: str) -> ParsedNotification:
    otp = _parse_otp(message)
    if otp is not None:
        return otp
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
