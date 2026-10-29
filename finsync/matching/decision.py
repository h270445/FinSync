from __future__ import annotations

from dataclasses import dataclass

from finsync.matching.scoring import Features

MATCHER_VERSION = "rules-3"
AUTO_LINK_THRESHOLD = 0.95
REVIEW_THRESHOLD = 0.60
RUNNER_UP_MARGIN = 0.10

# Two fixes for the reverse-order case (supervisor feedback of 2026-10-29), both on since rules-3
# (author's decision, 2026-10-29). The evaluation runner switches them off to compare.
# A: an information-poor pair (see `information_poor`) needs this score to link automatically.
STRICT_POOR_GATE = True
POOR_PAIR_AUTO_LINK = 0.95
# B: a later record that would fit an automatically linked, unconfirmed event as well as its weakest
# automatic link does reopens that event for review instead of being kept apart silently.
REOPEN_CONTESTED = True


@dataclass(frozen=True)
class Decision:
    outcome: str
    event_id: int | None
    features: Features | None
    runner_up: float | None = None


def information_poor(features: Features) -> bool:
    """A date-only side, or a merchant score of 0.5 (unknown on one side, or only half shared)."""
    return features.delta.endswith("d") or features.merchant == 0.5


def decide(best_by_event: dict[int, Features], contested: dict[int, Features] | None = None) -> Decision:
    """Pick auto_linked, needs_review or separate from the best pair score of each candidate event.

    `contested` holds events the record cannot join (its channel is taken) but that it fits as well as
    their weakest automatic link; they compete like candidates but can only lead to review.
    """
    contested = contested or {}
    candidates = {**best_by_event, **contested}
    if not candidates:
        return Decision("separate", None, None)
    ranked = sorted(candidates.items(), key=lambda item: (-item[1].score, item[0]))
    event_id, best = ranked[0]
    runner_up = ranked[1][1].score if len(ranked) > 1 else None
    if best.score < REVIEW_THRESHOLD:
        return Decision("separate", event_id, best, runner_up)
    if event_id in contested:
        return Decision("needs_review", event_id, best, runner_up)
    # Rounded so that 0.95 against 0.85 counts as exactly the margin, not 0.0999…
    close = runner_up is not None and round(best.score - runner_up, 4) < RUNNER_UP_MARGIN
    strict = STRICT_POOR_GATE and information_poor(best)
    threshold = max(AUTO_LINK_THRESHOLD, POOR_PAIR_AUTO_LINK) if strict else AUTO_LINK_THRESHOLD
    if best.score >= threshold and not close:
        return Decision("auto_linked", event_id, best, runner_up)
    return Decision("needs_review", event_id, best, runner_up)
