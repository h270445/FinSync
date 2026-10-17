"""Transaction matching and duplicate detection: pure rules, no database access.

See docs/design/transaction-matching.md for the design.
"""

from finsync.matching.decision import MATCHER_VERSION, Decision, decide
from finsync.matching.fingerprint import canonical_row, fingerprint
from finsync.matching.normalize import direction_of, local_date, merchant_tokens
from finsync.matching.scoring import Features, MatchRecord, score

__all__ = [
    "MATCHER_VERSION",
    "Decision",
    "Features",
    "MatchRecord",
    "canonical_row",
    "decide",
    "direction_of",
    "fingerprint",
    "local_date",
    "merchant_tokens",
    "score",
]
