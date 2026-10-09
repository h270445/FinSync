"""Input parsing: turns source-specific input into structured transaction data."""

from finsync.ingestion.notifications import ParsedNotification, parse_notification

__all__ = ["ParsedNotification", "parse_notification"]
