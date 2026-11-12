"""Checks docs/planning/time-log.md: weekly totals and the grand total match the session rows.

Run from the repository root: python .claude/skills/session-wrap-up/check_time_log.py
Prints the expected weekly table and exits with 1 if the file disagrees with it.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

LOG = Path("docs/planning/time-log.md")
SESSION_ROW = re.compile(r"^\| (\d{4}-\d{2}-\d{2}) \| [^|]* \| (\d+) \|")
WEEK_ROW = re.compile(r"^\| (\d{4}-\d{2}-\d{2}) – [^|]* \| (\d+) \| ([\d.]+) \|")
TOTAL_ROW = re.compile(r"^\| \*\*Total\*\* \| \*\*(\d+)\*\* \| \*\*([\d.]+)\*\* \|")


def hours(minutes: int) -> str:
    """One decimal, rounded half up as in the existing table (123 min is 2.1 h)."""
    return str((Decimal(minutes) / 60).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def main() -> int:
    sessions: dict[date, int] = defaultdict(int)
    weeks: dict[date, tuple[int, float]] = {}
    total: tuple[int, float] | None = None
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if match := WEEK_ROW.match(line):
            weeks[date.fromisoformat(match[1])] = (int(match[2]), float(match[3]))
        elif match := SESSION_ROW.match(line):
            day = date.fromisoformat(match[1])
            sessions[day - timedelta(days=day.weekday())] += int(match[2])
        elif match := TOTAL_ROW.match(line):
            total = (int(match[1]), float(match[2]))

    problems = []
    for monday in sorted(set(sessions) | set(weeks)):
        expected = sessions.get(monday, 0)
        listed = weeks.get(monday)
        if monday.weekday() != 0:
            problems.append(f"week row {monday} does not start on a Monday")
        if listed is None:
            problems.append(f"week of {monday}: missing, expected {expected} min")
        elif listed[0] != expected:
            problems.append(f"week of {monday}: listed {listed[0]} min, sessions add up to {expected}")
        elif abs(listed[1] - expected / 60) > 0.051:
            problems.append(f"week of {monday}: {listed[1]} h does not match {expected} min")
    expected_total = sum(sessions.values())
    if total is None:
        problems.append("no **Total** row")
    elif total[0] != expected_total or abs(total[1] - expected_total / 60) > 0.051:
        problems.append(f"total: listed {total[0]} min / {total[1]} h, sessions add up to {expected_total} min")

    print("Expected weekly totals:")
    for monday in sorted(sessions):
        print(f"| {monday} – {(monday + timedelta(days=6)):%m-%d} | {sessions[monday]} | {hours(sessions[monday])} |")
    print(f"| **Total** | **{expected_total}** | **{hours(expected_total)}** |")
    if problems:
        print("\nProblems:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print("\nOK: weekly totals and the total match the session rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
