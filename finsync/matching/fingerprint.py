from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_row(fields: dict[str, Any]) -> str:
    """Stable JSON text of a manual row, independent of key order."""
    return json.dumps(fields, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def fingerprint(group_id: str, channel: str, raw_payload: str) -> str:
    """SHA-256 of what one channel sent; the same payload from the same channel gives the same value."""
    digest = hashlib.sha256()
    for part in (group_id, channel, raw_payload):
        digest.update(part.encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()
