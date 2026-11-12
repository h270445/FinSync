"""Times without an offset are Europe/Budapest wall-clock time (ADR 0008, point 3)."""

from __future__ import annotations

from datetime import datetime, timezone

from finsync.matching.normalize import LOCAL_TIME_ZONE


def local_to_utc(value: datetime) -> datetime:
    """A naive time read as Budapest wall-clock time, as UTC; an aware time is only converted.

    In the repeated autumn hour the first occurrence is taken (fold=0). A time in the skipped spring
    hour is read with the offset before the change, which moves it forward by the zone rules.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=LOCAL_TIME_ZONE, fold=0)
    return value.astimezone(timezone.utc)
