from __future__ import annotations

from contextlib import contextmanager
import os
import tempfile
from typing import Iterator
import unittest

from finsync.core import FinSyncService
from finsync.matching import decide
from finsync.matching import decision as decision_rules
from finsync.matching.scoring import Features
from finsync.storage import FinSyncStorage


@contextmanager
def options(strict: bool = False, reopen: bool = False, auto_link: float = 0.85) -> Iterator[None]:
    """The options at the rules-2 threshold, where they were compared; rules-3 links at 0.95."""
    saved = decision_rules.STRICT_POOR_GATE, decision_rules.REOPEN_CONTESTED, decision_rules.AUTO_LINK_THRESHOLD
    decision_rules.STRICT_POOR_GATE, decision_rules.REOPEN_CONTESTED = strict, reopen
    decision_rules.AUTO_LINK_THRESHOLD = auto_link
    try:
        yield
    finally:
        decision_rules.STRICT_POOR_GATE, decision_rules.REOPEN_CONTESTED, decision_rules.AUTO_LINK_THRESHOLD = saved


class StrictGateDecisionTest(unittest.TestCase):
    def test_only_information_poor_pairs_need_the_higher_score(self) -> None:
        day_late = Features(amount=1.0, time=0.6667, merchant=1.0, delta="1d", score=0.9)
        no_merchant = Features(amount=1.0, time=1.0, merchant=0.5, delta="0d", score=0.85)
        minute_pair = Features(amount=1.0, time=0.5, merchant=1.0, delta="24.00h", score=0.85)
        same_day = Features(amount=1.0, time=1.0, merchant=1.0, delta="0d", score=1.0)
        with options():
            self.assertEqual(decide({1: day_late}).outcome, "auto_linked")
        with options(strict=True):
            self.assertEqual(decide({1: day_late}).outcome, "needs_review")
            self.assertEqual(decide({1: no_merchant}).outcome, "needs_review")
            self.assertEqual(decide({1: minute_pair}).outcome, "auto_linked")
            self.assertEqual(decide({1: same_day}).outcome, "auto_linked")

    def test_a_contested_event_can_only_lead_to_review(self) -> None:
        strong = Features(amount=1.0, time=1.0, merchant=1.0, delta="0h", score=1.0)
        decision = decide({}, contested={7: strong})
        self.assertEqual((decision.outcome, decision.event_id), ("needs_review", 7))


class ReverseOrderIkeaTest(unittest.TestCase):
    """The test-split case from the 2026-10-18 results, replayed from the last arrival to the first.

    Two 14 990 HUF IKEA purchases two days apart. The second one's notification and member B's
    date-only entry arrive first and link; member A's entry for the first purchase, typed the next
    day, then joins them, and the first purchase's own notification finds its channel taken.
    """

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        self.service = FinSyncService(self.storage)
        for user in ("user-a", "user-b"):
            self.storage.add_group_membership(user, "group-1")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _manual(self, user: str, day: str):
        row = {"amount": "-14990", "currency": "HUF", "description": "Household items", "merchant": "IKEA",
               "happened_at": day}
        return self.service.create_manual_transaction(user, "group-1", row)

    def _notification(self, when: str):
        return self.service.ingest_notification("user-a", "group-1", f"CARD PURCHASE -14990 HUF at IKEA Budaörs on {when}")

    def _replay(self):
        self._manual("user-b", "2026-09-06")
        self._notification("2026-09-06 09:37")
        late_entry = self._manual("user-a", "2026-09-05")
        first_notification = self._notification("2026-09-04 09:46")
        return late_entry, first_notification

    def _review_states(self) -> dict[int, str]:
        return {event.id: event.review_state for event in self.service.list_group_events("user-a", "group-1")}

    def test_without_either_option_the_late_entry_is_merged_silently(self) -> None:
        with options():
            late_entry, first_notification = self._replay()
        self.assertEqual(late_entry.match_outcome, "auto_linked")
        self.assertEqual(first_notification.match_outcome, "separate")
        self.assertEqual(set(self._review_states().values()), {"clear"})

    def test_strict_gate_sends_the_late_entry_to_review(self) -> None:
        with options(strict=True):
            late_entry, first_notification = self._replay()
        self.assertEqual(late_entry.match_outcome, "needs_review")
        self.assertNotEqual(first_notification.event_id, late_entry.event_id)
        self.assertEqual(len(self.service.list_group_events("user-a", "group-1")), 3)

    def test_reopening_flags_the_merged_event_and_moves_nothing(self) -> None:
        with options(reopen=True):
            late_entry, first_notification = self._replay()
        self.assertEqual(late_entry.match_outcome, "auto_linked")
        self.assertEqual(first_notification.match_outcome, "needs_review")
        states = self._review_states()
        self.assertEqual(states[late_entry.event_id], "needs_review")
        self.assertEqual(states[first_notification.event_id], "needs_review")
        merged = next(e for e in self.service.list_group_events("user-a", "group-1") if e.id == late_entry.event_id)
        self.assertEqual(len(merged.transactions), 3)
        [review] = self.service.list_open_reviews("user-a", "group-1")
        self.assertTrue(review.features["contested"])

        with options(reopen=True):
            self.service.reject_match("user-a", "group-1", review.decision_id)
        self.assertEqual(set(self._review_states().values()), {"clear"})

    def test_an_event_a_person_put_together_is_never_reopened(self) -> None:
        with options(strict=True, reopen=True):
            founder = self._manual("user-b", "2026-09-06")
            self._manual("user-a", "2026-09-05")
            [review] = self.service.list_open_reviews("user-a", "group-1")
            self.service.confirm_match("user-a", "group-1", review.decision_id)
            # Member B's channel is taken in that event, and the event has no automatic link to contest.
            later = self._manual("user-b", "2026-09-07")
        self.assertEqual(later.match_outcome, "separate")
        self.assertEqual(self._review_states()[founder.event_id], "clear")
        self.assertNotIn("contested", self.storage.list_decisions("group-1")[-1]["features"] or {})


if __name__ == "__main__":
    unittest.main()
