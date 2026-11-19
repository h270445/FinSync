"""The hybrid categorizer's deterministic layer: the Hungarian dictionary under the group's merchant rules."""

from __future__ import annotations

import os
import tempfile
import unittest

from finsync.categorization import CATEGORIES, CategoryDecision, MerchantRule, categorize_record
from finsync.categorization.dictionary import KEYWORDS, MERCHANTS, find_merchant, keyword_categories
from finsync.categorization.merchant_rules import merchant_key
from finsync.core import FinSyncService
from finsync.storage import FinSyncStorage


class DictionaryTest(unittest.TestCase):
    def test_every_entry_names_an_allowed_category_and_a_normalised_key(self) -> None:
        for entry in MERCHANTS:
            with self.subTest(key=entry.key):
                self.assertIn(entry.category, CATEGORIES)
                self.assertEqual(merchant_key(entry.key), entry.key)
        self.assertLessEqual(set(KEYWORDS), set(CATEGORIES))
        keys = [entry.key for entry in MERCHANTS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_merchants_match_on_whole_words_and_the_longest_key_wins(self) -> None:
        self.assertEqual(find_merchant("SPAR Magyarország Kft.").category, "groceries")
        self.assertEqual(find_merchant("MAV-START ZRT").key, "mav start")
        self.assertEqual(find_merchant("MOL Bubi 0042").key, "mol bubi")
        self.assertEqual(find_merchant("DM DROGERIE 0855").key, "dm")
        self.assertIsNone(find_merchant("Molnár Pékség"))  # "mol" only as a whole word
        self.assertIsNone(find_merchant("Sarki bolt"))  # "bolt" is a shop; Bolt rides are "BOLT.EU"
        self.assertEqual(find_merchant("BOLT.EU/O/2610").category, "transport")
        self.assertIsNone(find_merchant(None))

    def test_keywords_ignore_accents_and_take_hungarian_suffixes(self) -> None:
        self.assertEqual(keyword_categories("Vacsora az étteremben"), ["eating_out"])
        self.assertEqual(keyword_categories("GYÓGYSZERTÁR 12"), ["health"])
        self.assertEqual(keyword_categories("novemberi lakbér"), ["housing_utilities"])
        self.assertEqual(keyword_categories("lakberendezési áruház"), ["household"])  # not the rent
        self.assertEqual(keyword_categories("a vonatkozó számla"), [])  # "vonat" only as a word
        self.assertEqual(keyword_categories("Business lunch"), ["eating_out"])  # "bus" only as a word
        self.assertEqual(keyword_categories("zokni és mosószer"), ["clothing", "household"])


class CategorizeRecordTest(unittest.TestCase):
    def test_a_clear_merchant_is_high(self) -> None:
        self.assertEqual(
            categorize_record("MAV-START ZRT", "Kártyás vásárlás"), CategoryDecision("transport", "dictionary", "high")
        )

    def test_a_mixed_merchant_alone_is_its_usual_category_and_low(self) -> None:
        self.assertEqual(categorize_record("TESCO Áruház 41021", None), CategoryDecision("groceries", "dictionary", "low"))

    def test_keywords_beat_a_mixed_merchants_usual_category(self) -> None:
        self.assertEqual(categorize_record("Tesco", "zokni"), CategoryDecision("clothing", "keyword", "high"))
        self.assertEqual(categorize_record("Spar", "heti bevásárlás"), CategoryDecision("groceries", "keyword", "high"))
        # Two categories named: the mixed merchant's usual one is preferred, but stays low.
        self.assertEqual(
            categorize_record("dm", "mosószer és vitamin"), CategoryDecision("household", "keyword", "low")
        )

    def test_the_groups_rule_wins_over_the_dictionary(self) -> None:
        rules = [MerchantRule(1, "mol", "other")]
        self.assertEqual(categorize_record("MOL Töltőállomás", None, rules), CategoryDecision("other", "merchant_rule", "high"))

    def test_without_merchant_the_description_is_looked_up(self) -> None:
        self.assertEqual(categorize_record(None, "Netflix"), CategoryDecision("entertainment", "dictionary", "high"))

    def test_nothing_known_is_other_without_a_source(self) -> None:
        self.assertEqual(categorize_record("SUMUP *KJ BT", None), CategoryDecision("other", "none", "low"))


class ServiceUsesTheDictionaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        self.service = FinSyncService(self.storage)
        self.storage.add_group_membership("anna", "group-1")  # admin

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _record(self, result):
        return next(tx for tx in self.storage.list_transactions("group-1") if tx.id == result.transaction_id)

    def test_new_records_get_the_dictionary_category_unless_a_rule_applies(self) -> None:
        notification = self.service.ingest_notification(
            "anna", "group-1", "CARD PURCHASE -1890 HUF at SPAR 0123 Kft on 2026-11-05 16:42"
        )
        self.assertEqual(self._record(notification).category, "groceries")
        manual = self.service.create_manual_transaction("anna", "group-1", {
            "amount": "-3450", "currency": "HUF", "description": "BENU Gyógyszertár", "happened_at": "2026-11-06",
        })
        self.assertEqual(self._record(manual).category, "health")
        self.service.create_merchant_rule("anna", "group-1", "Benu", "household")
        later = self.service.create_manual_transaction("anna", "group-1", {
            "amount": "-1290", "currency": "HUF", "description": "BENU Gyógyszertár", "happened_at": "2026-11-07",
        })
        self.assertEqual(self._record(later).category, "household")

    def test_a_repeated_transfer_row_of_one_file_is_a_transfer_too(self) -> None:
        self.service.create_own_account("anna", "group-1", "Minta Anna")
        content = "date,amount,description\n2026-11-05,-5000,Minta Anna\n2026-11-05,-5000,Minta Anna\n"
        first, second = self.service.import_file("anna", "group-1", content).results
        self.assertEqual(second.match_outcome, "needs_review")
        for result in (first, second):
            record = self._record(result)
            self.assertEqual((record.direction, record.category), ("transfer", "transfer"))


if __name__ == "__main__":
    unittest.main()
