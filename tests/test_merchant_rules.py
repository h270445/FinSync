"""W8 group merchant → category rules: the hybrid categorizer's first layer and /v1/merchant-rules."""

from __future__ import annotations

import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from finsync.api import create_app
from finsync.categorization import CATEGORIES, MerchantRule, find_rule, merchant_key, validate_rule
from finsync.core import ConflictError, FinSyncService, NotFoundError, TokenService
from finsync.core.service import AuthorizationError
from finsync.evaluation.generate_categories import CATEGORIES as DATASET_CATEGORIES
from finsync.storage import FinSyncStorage

NOTIFICATION = "CARD PURCHASE -4500 HUF at Kisbolt 12 Kft on 2026-09-05 16:42"


class MerchantKeyTest(unittest.TestCase):
    def test_the_key_keeps_the_words_without_numbers_suffixes_and_accents(self) -> None:
        self.assertEqual(merchant_key("Spar 0123 Kft."), "spar")
        self.assertEqual(merchant_key("MÁV-START Zrt."), "mav start")
        self.assertEqual(merchant_key("  Dm  dm "), "dm")

    def test_a_rule_applies_when_all_its_words_are_in_the_merchant(self) -> None:
        rules = [MerchantRule(1, "mol", "transport"), MerchantRule(2, "mol bubi", "entertainment")]
        self.assertEqual(find_rule(rules, "MOL Bubi 0042").id, 2)  # the more specific rule wins
        self.assertEqual(find_rule(rules, "MOL Töltőállomás 117").id, 1)
        self.assertIsNone(find_rule(rules, "Molnár Pékség"))  # whole words only
        self.assertIsNone(find_rule(rules, None))

    def test_rules_name_one_of_the_datasets_categories(self) -> None:
        self.assertEqual(CATEGORIES, DATASET_CATEGORIES)
        self.assertEqual(validate_rule(" SPAR ", "groceries"), ("SPAR", "spar", "groceries"))
        for merchant, category, reason in (
            ("SPAR", "food", "category"),
            ("", "groceries", "merchant"),
            ("123 Kft", "groceries", "word"),
            ("x" * 81, "groceries", "80"),
        ):
            with self.subTest(merchant=merchant, category=category), self.assertRaisesRegex(ValueError, reason):
                validate_rule(merchant, category)


class MerchantRulesServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        self.service = FinSyncService(self.storage)
        for user, group in (("anna", "group-1"), ("balint", "group-1"), ("user-c", "group-2")):
            self.storage.add_group_membership(user, group)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _category_of(self, result) -> str:
        return next(tx.category for tx in self.storage.list_transactions("group-1") if tx.id == result.transaction_id)

    def test_a_rule_categorizes_new_notifications_and_manual_entries(self) -> None:
        self.service.create_merchant_rule("anna", "group-1", "Kisbolt", "household")
        notification = self.service.ingest_notification("anna", "group-1", NOTIFICATION)
        self.assertEqual(self._category_of(notification), "household")
        manual = self.service.create_manual_transaction("balint", "group-1", {
            "amount": "-990", "currency": "HUF", "description": "Kisbolt Budapest", "happened_at": "2026-09-20",
        })
        # Without a merchant, the description is looked up.
        self.assertEqual(self._category_of(manual), "household")

    def test_a_rule_wins_over_the_keyword_rules(self) -> None:
        # The keyword rules call any "market" groceries; the group knows this one sells household goods.
        result = self.service.create_manual_transaction("anna", "group-1", {
            "amount": "-2000", "currency": "HUF", "description": "Home Market", "merchant": "Home Market",
            "happened_at": "2026-09-01",
        })
        self.assertEqual(self._category_of(result), "groceries")
        self.service.create_merchant_rule("anna", "group-1", "Home Market", "household")
        later = self.service.create_manual_transaction("anna", "group-1", {
            "amount": "-3000", "currency": "HUF", "description": "Home Market", "merchant": "Home Market",
            "happened_at": "2026-09-08",
        })
        self.assertEqual(self._category_of(later), "household")
        # The existing record is not changed (rules apply to records stored after them).
        self.assertEqual(self._category_of(result), "groceries")

    def test_rules_are_per_group(self) -> None:
        self.service.create_merchant_rule("user-c", "group-2", "Kisbolt", "health")
        notification = self.service.ingest_notification("anna", "group-1", NOTIFICATION)
        self.assertEqual(self._category_of(notification), "other")
        with self.assertRaises(NotFoundError):
            rule_id = self.service.list_merchant_rules("user-c", "group-2")[0].id
            self.service.update_merchant_rule("anna", "group-1", rule_id, "Kisbolt", "household")
        with self.assertRaises(AuthorizationError):
            self.service.list_merchant_rules("user-c", "group-1")

    def test_any_member_edits_and_deletes_and_keys_stay_unique(self) -> None:
        rule = self.service.create_merchant_rule("anna", "group-1", "SPAR", "groceries")
        with self.assertRaises(ConflictError):
            self.service.create_merchant_rule("balint", "group-1", "Spar 0123 Kft.", "household")
        other = self.service.create_merchant_rule("balint", "group-1", "DM", "household")
        with self.assertRaises(ConflictError):
            self.service.update_merchant_rule("balint", "group-1", other.id, "spar", "household")
        updated = self.service.update_merchant_rule("balint", "group-1", rule.id, "Spar Market", "household")
        self.assertEqual((updated.merchant_key, updated.category, updated.created_by), ("spar market", "household", "anna"))
        deleted = self.service.delete_merchant_rule("balint", "group-1", rule.id)
        self.assertEqual(deleted.id, rule.id)
        self.assertEqual([r.merchant_key for r in self.service.list_merchant_rules("anna", "group-1")], ["dm"])
        with self.assertRaises(NotFoundError):
            self.service.delete_merchant_rule("anna", "group-1", rule.id)

    def test_merchant_rules_over_http(self) -> None:
        token, _ = TokenService(self.storage).create("anna", "group-1", "test")
        headers = {"Authorization": f"Bearer {token}"}
        with TestClient(create_app(self.storage)) as client:
            created = client.post("/v1/merchant-rules", json={"merchant": "Kisbolt", "category": "household"}, headers=headers)
            self.assertEqual(created.status_code, 201)
            rule = created.json()
            self.assertEqual((rule["merchant"], rule["merchant_key"], rule["created_by"]), ("Kisbolt", "kisbolt", "anna"))

            listed = client.get("/v1/merchant-rules", headers=headers).json()
            self.assertEqual([r["id"] for r in listed["rules"]], [rule["id"]])
            self.assertEqual(listed["categories"], list(CATEGORIES))

            duplicate = client.post("/v1/merchant-rules", json={"merchant": "KISBOLT", "category": "health"}, headers=headers)
            self.assertEqual(duplicate.status_code, 409)
            invalid = client.post("/v1/merchant-rules", json={"merchant": "Bolt", "category": "food"}, headers=headers)
            self.assertEqual((invalid.status_code, list(invalid.json())), (400, ["error"]))

            path = f"/v1/merchant-rules/{rule['id']}"
            updated = client.put(path, json={"merchant": "Kisbolt", "category": "groceries"}, headers=headers)
            self.assertEqual(updated.json()["category"], "groceries")
            self.assertEqual(client.delete(path, headers=headers).status_code, 200)
            self.assertEqual(client.delete(path, headers=headers).status_code, 404)
            self.assertEqual(client.get("/v1/merchant-rules", headers=headers).json()["rules"], [])


if __name__ == "__main__":
    unittest.main()
