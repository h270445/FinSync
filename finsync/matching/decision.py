from __future__ import annotations

from dataclasses import dataclass

from finsync.matching.scoring import Features

MATCHER_VERSION = "rules-2"
AUTO_LINK_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.60
RUNNER_UP_MARGIN = 0.10


@dataclass(frozen=True)
class Decision:
    outcome: str
    event_id: int | None
    features: Features | None
    runner_up: float | None = None


def decide(best_by_event: dict[int, Features]) -> Decision:
    """Pick auto_linked, needs_review or separate from the best pair score of each candidate event."""
    if not best_by_event:
        return Decision("separate", None, None)
    ranked = sorted(best_by_event.items(), key=lambda item: (-item[1].score, item[0]))
    event_id, best = ranked[0]
    runner_up = ranked[1][1].score if len(ranked) > 1 else None
    if best.score < REVIEW_THRESHOLD:
        return Decision("separate", event_id, best, runner_up)
    # Rounded so that 0.95 against 0.85 counts as exactly the margin, not 0.0999…
    contested = runner_up is not None and round(best.score - runner_up, 4) < RUNNER_UP_MARGIN
    if best.score >= AUTO_LINK_THRESHOLD and not contested:
        return Decision("auto_linked", event_id, best, runner_up)
    return Decision("needs_review", event_id, best, runner_up)
