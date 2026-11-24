"""When the LLM layer is asked about an uncertain event in the live flow, and what it may cost.

The author's settings of 2026-11-19, confirmed on 2026-11-24 ([design](../../docs/design/categorization.md#when-the-llm-is-called-proposed-by-the-author-2026-11-19)):

- **Never by default.** A group's admin chooses `after_arrival` (X hours after the record arrived, 24 by
  default), `daily` (at a set Budapest time) or `weekly` (on a set weekday and time). Until then nothing
  is sent to a model.
- **Manual first.** The due time gives the members the chance to decide first; a member's decision is
  never overwritten and a due event decided in the meantime is skipped.
- **"Ask for a suggestion now"** works in every mode, for one event a member chooses.
- **Cost guard.** A monthly budget per group (USD); when the month's logged calls reach it, runs stop and
  the API says so. Identical texts are answered from the cache, so they cost nothing again.

The confidence threshold is the one chosen on the development split in the measurement of 2026-11-24
([report](../../docs/evaluation/results/2026-11-24-categorization-hybrid.md)): at or above it the model's
answer is settled (`llm`, `high`), below it the event stays a suggestion.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
import re
from zoneinfo import ZoneInfo

from finsync.storage import LLM_MODES, LlmSettingsRecord

BUDAPEST = ZoneInfo("Europe/Budapest")
# Chosen on dev in the measurement of 2026-11-24 (79.8 % coverage, 93.7 % accuracy of settled answers on test).
LLM_THRESHOLD = 0.40
# The in-process runner looks for due events this often (no external scheduler needed).
RUN_INTERVAL_SECONDS = 300
MAX_HOURS_AFTER = 24 * 14
MAX_MONTHLY_BUDGET_USD = Decimal("100")
_RUN_TIME = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def validate_settings(
    group_id: str, mode: str, hours_after: int, run_time: str, weekday: int, monthly_budget_usd: str
) -> LlmSettingsRecord:
    """The settings an admin sent, checked; ValueError with the reason otherwise."""
    if mode not in LLM_MODES:
        raise ValueError(f"mode must be one of: {', '.join(LLM_MODES)}")
    if not isinstance(hours_after, int) or not 1 <= hours_after <= MAX_HOURS_AFTER:
        raise ValueError(f"hours_after must be a whole number from 1 to {MAX_HOURS_AFTER}")
    if not _RUN_TIME.match(run_time or ""):
        raise ValueError("run_time must be HH:MM, for example 20:00")
    if not isinstance(weekday, int) or not 0 <= weekday <= 6:
        raise ValueError("weekday must be 0 (Monday) to 6 (Sunday)")
    try:
        budget = Decimal(str(monthly_budget_usd))
    except (InvalidOperation, ValueError) as error:
        raise ValueError("monthly_budget_usd must be a number") from error
    if not budget.is_finite() or budget < 0 or budget > MAX_MONTHLY_BUDGET_USD:
        raise ValueError(f"monthly_budget_usd must be from 0 to {MAX_MONTHLY_BUDGET_USD}")
    return LlmSettingsRecord(group_id, mode, hours_after, run_time, weekday, budget.quantize(Decimal("0.01")))


def next_due(settings: LlmSettingsRecord, arrived: datetime) -> datetime | None:
    """When the scheduled run may ask about an event whose first record arrived at `arrived` (UTC); None
    for `never`. Daily and weekly times are Budapest wall-clock times (ADR 0008)."""
    if settings.mode == "never":
        return None
    if settings.mode == "after_arrival":
        return (arrived + timedelta(hours=settings.hours_after)).astimezone(timezone.utc)
    hour, minute = (int(part) for part in settings.run_time.split(":"))
    local = arrived.astimezone(BUDAPEST)
    day = local.date()
    for offset in range(0, 8):
        candidate_day = day + timedelta(days=offset)
        if settings.mode == "weekly" and candidate_day.weekday() != settings.weekday:
            continue
        candidate = datetime.combine(candidate_day, time(hour, minute), BUDAPEST)
        if candidate > local:
            return candidate.astimezone(timezone.utc)
    raise AssertionError("a daily or weekly time always comes within eight days")


def month_start(now: datetime) -> datetime:
    """The start of the Budapest calendar month of `now`, in UTC: the budget's period."""
    local = now.astimezone(BUDAPEST)
    return datetime(local.year, local.month, 1, tzinfo=BUDAPEST).astimezone(timezone.utc)
