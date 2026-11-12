"""Masks an exported capture file of the Android app so its format can be shared without its content.

Run on the author's own machine, never on a shared or cloud machine:

    python .claude/skills/bank-notification-privacy/mask_captures.py captures.jsonl > masked.md

Every letter becomes `a` or `A` (by case, accented Hungarian letters included), every digit `9`;
spaces and punctuation stay, so amounts, separators and sentence shapes remain visible. Keys,
group keys and sort keys are masked too (Revolut puts the whole text into the tag and key).
Absolute times are dropped: only the difference between `when_ms` and `post_time_ms` is shown.
Only the masked table is printed; the script refuses to print a value that still holds a letter
other than a/A or a digit other than 9.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

TEXT_FIELDS = ("title", "text", "big_text", "sub_text", "ticker", "tag", "key", "group_key", "group", "sort_key")
PLAIN_FIELDS = ("type", "kind", "package", "channel", "category", "group_summary", "ongoing", "simulated", "device_zone")


def mask(value: str) -> str:
    out = []
    for char in value:
        if char.isdigit():
            out.append("9")
        elif char.isalpha():
            out.append("A" if char.isupper() else "a")
        else:
            out.append(char)
    return "".join(out)


def _safe(value: str) -> str:
    leaked = {char for char in value if (char.isalpha() and char not in "aA") or (char.isdigit() and char != "9")}
    if leaked:
        raise SystemExit(f"refusing to print: masking left {len(leaked)} unmasked character kinds")
    return value.replace("|", "\\|").replace("\n", " ⏎ ")


def describe(record: dict) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for field in PLAIN_FIELDS:
        if field in record and record[field] is not None:
            # App and channel identifiers, flags and the zone are metadata, not notification content.
            rows.append((field, str(record[field])))
    for field in TEXT_FIELDS:
        value = record.get(field)
        if isinstance(value, str):
            if field == "big_text" and value == record.get("text"):
                rows.append((field, "= text"))
            else:
                rows.append((field, _safe(mask(value))))
    for field, value in sorted((record.get("extras") or {}).items()):
        if isinstance(value, str):
            rows.append((f"extras.{mask(field) if not field.startswith('android.') else field}", _safe(mask(value))))
    for index, value in enumerate(record.get("masked_texts") or []):
        rows.append((f"masked_texts[{index}]", _safe(mask(str(value)))))
    if isinstance(record.get("post_time_ms"), int) and isinstance(record.get("when_ms"), int):
        rows.append(("when − post", f"{record['when_ms'] - record['post_time_ms']} ms"))
    return rows


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    lines = Path(argv[1]).read_text(encoding="utf-8").splitlines()
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("type") in ("listener_connected", "listener_disconnected", "removed"):
            print(f"Record {number}: {record['type']}" + (f" ({record.get('reason_name')})" if "reason_name" in record else ""))
            print()
            continue
        print(f"Record {number}")
        print()
        print("| Field | Masked value |")
        print("| --- | --- |")
        for field, value in describe(record):
            print(f"| `{field}` | `{value}` |")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
