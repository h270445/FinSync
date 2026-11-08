from __future__ import annotations

import collections
from pathlib import Path
import unittest

from finsync.evaluation.generate_categories import CATEGORIES, SCENARIOS, generate, read_csv

DATASET = Path(__file__).parent / "data" / "categorization_eval.csv"


class CategorizationDatasetTest(unittest.TestCase):
    def test_committed_dataset_matches_the_generator(self) -> None:
        # Regenerate with: python -m finsync.evaluation.generate_categories
        self.assertEqual(read_csv(DATASET), generate(2026))

    def test_generation_is_reproducible_and_seed_dependent(self) -> None:
        self.assertEqual(generate(7), generate(7))
        self.assertNotEqual(generate(7), generate(8))

    def test_scenario_mix_and_labels(self) -> None:
        items = read_csv(DATASET)
        self.assertEqual(len({item.item_id for item in items}), len(items))
        counts = collections.Counter((item.scenario, item.ambiguity) for item in items)
        self.assertEqual(counts, {(scenario, ambiguity): count for scenario, ambiguity, count in SCENARIOS})
        self.assertEqual({item.true_category for item in items}, set(CATEGORIES))
        for item in items:
            self.assertIn(item.usual_category, (*CATEGORIES, ""), item.item_id)
            self.assertTrue(item.description, item.item_id)
            self.assertGreater(int(item.amount), 0, item.item_id)

    def test_both_splits_hold_clear_and_ambiguous_items(self) -> None:
        pairs = {(item.split, item.ambiguity) for item in read_csv(DATASET)}
        self.assertEqual(pairs, {(s, a) for s in ("dev", "test") for a in ("clear", "ambiguous")})


if __name__ == "__main__":
    unittest.main()
