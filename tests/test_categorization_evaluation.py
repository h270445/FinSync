from __future__ import annotations

from pathlib import Path
import unittest

from finsync.categorization.rules import _CATEGORY_KEYWORDS
from finsync.evaluation.categories import (
    RULES_TO_DATASET,
    evaluate,
    merchant_only_ceiling,
    rules_categorizer,
    score,
)
from finsync.evaluation.generate_categories import CATEGORIES, Item, read_csv

DATASET = Path(__file__).parent / "data" / "categorization_eval.csv"


def _item(description: str, merchant: str, true_category: str) -> Item:
    return Item(
        item_id="t", scenario="mixed_merchant", ambiguity="clear", split="dev", source="manual",
        description=description, merchant=merchant, amount="1000", currency="HUF",
        true_category=true_category, usual_category=true_category,
    )


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

    def test_rent_is_scored_as_housing_utilities(self) -> None:
        rent = _item("Monthly rent", "Lakas Kft", true_category="housing_utilities")
        self.assertEqual(rules_categorizer(rent), "housing_utilities")
        self.assertEqual(score([rent], rules_categorizer, "rent").correct, 1)

    def test_ceiling_takes_each_merchants_most_frequent_label(self) -> None:
        items = [
            _item("a", "Amazon", true_category="entertainment"),
            _item("b", "Amazon", true_category="entertainment"),
            _item("c", "Amazon", true_category="household"),
            _item("d", "Tesco", true_category="groceries"),
        ]
        self.assertEqual(merchant_only_ceiling(items).correct, 3)

    def test_rejects_a_category_outside_the_list(self) -> None:
        with self.assertRaises(ValueError):
            score(read_csv(DATASET)[:1], lambda item: "food", "bad")

    def test_report_lists_both_splits(self) -> None:
        report = evaluate(read_csv(DATASET), DATASET)
        self.assertIn("| all |", report)
        self.assertIn("| scenario: cryptic_text |", report)


if __name__ == "__main__":
    unittest.main()
