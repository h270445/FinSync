from __future__ import annotations

from pathlib import Path
import unittest

from finsync.categorization.rules import _CATEGORY_KEYWORDS
from finsync.evaluation.categories import RULES_TO_DATASET, evaluate, rules_categorizer, score
from finsync.evaluation.generate_categories import CATEGORIES, read_csv

DATASET = Path(__file__).parent / "data" / "categorization_eval.csv"


class CategorizationEvaluationTest(unittest.TestCase):
    def test_mapping_covers_every_rule_label_and_stays_in_the_list(self) -> None:
        rule_labels = {category for category, _ in _CATEGORY_KEYWORDS} | {"other"}
        self.assertEqual(set(RULES_TO_DATASET), rule_labels)
        self.assertLessEqual(set(RULES_TO_DATASET.values()), set(CATEGORIES))

    def test_scores_every_split_with_known_categories(self) -> None:
        items = read_csv(DATASET)
        for split in ("dev", "test"):
            result = score([item for item in items if item.split == split], rules_categorizer, split)
            self.assertGreater(result.items, 0)
            self.assertGreater(result.correct, 0)
            self.assertLess(result.correct, result.items)

    def test_rejects_a_category_outside_the_list(self) -> None:
        with self.assertRaises(ValueError):
            score(read_csv(DATASET)[:1], lambda item: "food", "bad")

    def test_report_lists_both_splits(self) -> None:
        report = evaluate(read_csv(DATASET), DATASET)
        self.assertIn("| all |", report)
        self.assertIn("| scenario: cryptic_text |", report)


if __name__ == "__main__":
    unittest.main()
