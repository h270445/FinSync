from __future__ import annotations

import unittest

from finsync.categorization import categorize_transaction


class CategorizationTest(unittest.TestCase):
    def test_matches_whole_keywords(self) -> None:
        self.assertEqual(categorize_transaction("Bus ticket"), "transport")
        self.assertEqual(categorize_transaction("Train to Vienna"), "transport")
        self.assertEqual(categorize_transaction("Monthly rent"), "housing")
        self.assertEqual(categorize_transaction("CARD PURCHASE at Tesco"), "groceries")

    def test_matches_keywords_next_to_punctuation(self) -> None:
        self.assertEqual(categorize_transaction("Uber*Trip"), "transport")
        self.assertEqual(categorize_transaction("rent-october"), "housing")

    def test_does_not_match_keywords_inside_other_words(self) -> None:
        self.assertEqual(categorize_transaction("Business lunch"), "other")
        self.assertEqual(categorize_transaction("Training course"), "other")
        self.assertEqual(categorize_transaction("Parent gift"), "other")


if __name__ == "__main__":
    unittest.main()
