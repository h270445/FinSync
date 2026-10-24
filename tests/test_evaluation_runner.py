from __future__ import annotations

from pathlib import Path
import unittest

from finsync.evaluation.__main__ import evaluate
from finsync.evaluation.generate import Row, read_csv
from finsync.evaluation.runner import choose_threshold, run_baseline, run_matcher, score_events, thresholds
from finsync.matching import decision as decision_rules

DATASET = Path(__file__).parent / "data" / "matching_eval.csv"


def _row(record_id: str, true_event: str, scenario: str = "single_manual") -> Row:
    return Row(record_id=record_id, case="C1", true_event=true_event, scenario=scenario, kind="none",
               split="dev", member="member-a", source="manual", arrives_at=f"2026-09-01T00:00:{record_id[-2:]}")


class MetricsTest(unittest.TestCase):
    def setUp(self) -> None:
        # E1 has three records, E2 one.
        self.rows = [_row("R01", "E1"), _row("R02", "E1"), _row("R03", "E1"), _row("R04", "E2")]

    def test_baseline_merges_nothing_and_misses_every_duplicate(self) -> None:
        result = run_baseline(self.rows)
        self.assertEqual(result.predicted_events, 4)
        self.assertIsNone(result.precision)
        self.assertEqual(result.recall, 0.0)
        self.assertEqual(result.missed_rate, 1.0)
        self.assertEqual(result.false_merges, ())
        self.assertEqual(result.double_counted, 2)

    def test_false_merge_is_reported_with_its_records(self) -> None:
        events = {"R01": 1, "R02": 1, "R03": 2, "R04": 2}
        result = score_events(self.rows, events, set(), {}, "m", "dev", "arrival")
        self.assertEqual(result.true_pairs, 3)
        self.assertEqual(result.merged_pairs, 2)
        self.assertEqual(result.correct_pairs, 1)
        self.assertEqual([merge.record_ids for merge in result.false_merges], [("R03", "R04")])
        self.assertEqual(result.false_merge_rate, 0.5)
        # E1 is spread over two events, and E2 is hidden inside one of them.
        self.assertEqual(result.double_counted, 1)

    def test_a_pair_flagged_for_review_against_the_right_event_is_not_missed(self) -> None:
        events = {"R01": 1, "R02": 1, "R03": 3, "R04": 4}
        outcomes = {"R03": "needs_review"}
        unflagged = score_events(self.rows, events, set(), outcomes, "m", "dev", "arrival")
        flagged = score_events(self.rows, events, {("R03", 1)}, outcomes, "m", "dev", "arrival")
        wrong_event = score_events(self.rows, events, {("R03", 4)}, outcomes, "m", "dev", "arrival")
        self.assertEqual(len(unflagged.missed), 2)
        self.assertEqual(len(flagged.missed), 0)
        self.assertEqual(len(wrong_event.missed), 2)
        self.assertEqual(flagged.review_rate, 0.25)

    def test_threshold_choice_avoids_false_merges_then_prefers_recall(self) -> None:
        clean = score_events(self.rows, {"R01": 1, "R02": 1, "R03": 2, "R04": 3}, set(), {}, "m@0.85", "dev", "x")
        stricter = score_events(self.rows, {"R01": 1, "R02": 2, "R03": 3, "R04": 4}, set(), {}, "m@0.90", "dev", "x")
        merged = score_events(self.rows, {"R01": 1, "R02": 1, "R03": 1, "R04": 1}, set(), {}, "m@0.70", "dev", "x")
        same = score_events(self.rows, {"R01": 1, "R02": 1, "R03": 2, "R04": 3}, set(), {}, "m@0.95", "dev", "x")
        self.assertIs(choose_threshold([merged, clean, stricter]), clean)
        self.assertIs(choose_threshold([clean, same]), same)

    def test_thresholds_are_restored(self) -> None:
        before = decision_rules.AUTO_LINK_THRESHOLD
        with thresholds(auto_link=0.5):
            self.assertEqual(decision_rules.AUTO_LINK_THRESHOLD, 0.5)
        self.assertEqual(decision_rules.AUTO_LINK_THRESHOLD, before)


class DatasetRunTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rows = read_csv(DATASET)
        cls.dev = [row for row in cls.rows if row.split == "dev"]

    def test_current_threshold_has_no_false_merge_on_dev(self) -> None:
        result = run_matcher(self.dev, "dev")
        self.assertEqual(result.false_merges, ())
        self.assertEqual(result.records, len(self.dev))

    def test_late_decathlon_entry_goes_to_review_instead_of_the_other_purchase(self) -> None:
        # R0096 is logged five days after its notification and has the same amount as a later Decathlon purchase.
        self.assertEqual(run_matcher(self.dev, "dev").outcomes["R0096"], "needs_review")
        lowered = run_matcher(self.dev, "dev", auto_link=0.80)
        self.assertIn(("R0083", "R0088", "R0096"), [merge.record_ids for merge in lowered.false_merges])

    def test_report_is_deterministic(self) -> None:
        self.assertEqual(evaluate(self.rows, DATASET), evaluate(self.rows, DATASET))


if __name__ == "__main__":
    unittest.main()
