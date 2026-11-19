"""Transfers within the group: own accounts and counterparties (W8) give the direction `transfer`."""

from __future__ import annotations

from decimal import Decimal
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from finsync.api import create_app
from finsync.categorization import OwnAccount, is_transfer, own_account_key
from finsync.core import ConflictError, FinSyncService, NotFoundError, TokenService
from finsync.core.service import AuthorizationError
from finsync.storage import FinSyncStorage

# The supported OTP format for an outgoing transfer (synthetic names, tests/test_android_ingest.py).
OUTGOING = "-12 000 Ft, Minta Anna Beata"
INCOMING = "+12 000 Ft, Minta Bela"


class OwnAccountKeyTest(unittest.TestCase):
    def test_account_numbers_match_on_their_digits_and_names_on_their_words(self) -> None:
        self.assertEqual(own_account_key(" 11773016-01234567 "), ("11773016-01234567", "account", "1177301601234567"))
        self.assertEqual(own_account_key("Minta Anna Beáta"), ("Minta Anna Beáta", "name", "minta anna beata"))
        account = OwnAccount(1, "account", "1177301601234567")
        name = OwnAccount(2, "name", "minta anna")
        self.assertTrue(is_transfer([account], None, "Átutalás HU42 1177 3016 0123 4567 0000 0000"))
        self.assertFalse(is_transfer([account], None, "Átutalás 1177 3016 9999"))
        self.assertTrue(is_transfer([name], "Minta Anna Beata", None))
        self.assertFalse(is_transfer([name], "Minta Bela", None))
        self.assertFalse(is_transfer([name], "Mintabolt Anna utca", None))  # whole words only

    def test_an_entry_needs_a_name_or_eight_digits(self) -> None:
        for label in ("", "1234 567", "x" * 81):
            with self.subTest(label=label), self.assertRaises(ValueError):
                own_account_key(label)


class TransferServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        self.service = FinSyncService(self.storage)
        for user, group in (("anna", "group-1"), ("balint", "group-1"), ("user-c", "group-2")):
            self.storage.add_group_membership(user, group)  # Anna is group 1's admin

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _record(self, result):
        return next(tx for tx in self.storage.list_transactions("group-1") if tx.id == result.transaction_id)

    def test_a_notification_to_an_own_account_is_a_transfer_left_out_of_the_overview(self) -> None:
        self.service.create_own_account("anna", "group-1", "Minta Anna Beata")
        sent = self.service.ingest_notification("balint", "group-1", OUTGOING, posted_at="2026-11-12T09:15:00+01:00")
        record = self._record(sent)
        self.assertEqual((record.direction, record.category, record.amount), ("transfer", "transfer", Decimal("-12000")))
        other = self.service.ingest_notification("balint", "group-1", INCOMING, posted_at="2026-11-12T10:00:00+01:00")
        self.assertEqual(self._record(other).direction, "income")  # not on the list

        overview = self.service.overview("anna", "group-1", "2026-11")
        self.assertEqual(overview.transfer_count, 1)
        self.assertEqual([(t.expense, t.income) for t in overview.totals], [(Decimal("0"), Decimal("12000"))])

    def test_a_transfer_is_never_linked_to_a_purchase_of_the_same_amount(self) -> None:
        self.service.create_own_account("anna", "group-1", "Minta Anna")
        self.service.create_manual_transaction("anna", "group-1", {
            "amount": "-12000", "currency": "HUF", "description": "Bolt", "merchant": "Bolt",
            "happened_at": "2026-11-12T09:10",
        })
        sent = self.service.ingest_notification("anna", "group-1", OUTGOING, posted_at="2026-11-12T09:15:00+01:00")
        self.assertEqual(sent.match_outcome, "separate")

    def test_only_admins_change_the_list_and_entries_are_unique(self) -> None:
        with self.assertRaisesRegex(AuthorizationError, "admin"):
            self.service.create_own_account("balint", "group-1", "Minta Anna")
        entry = self.service.create_own_account("anna", "group-1", "11773016-01234567")
        with self.assertRaises(ConflictError):
            self.service.create_own_account("anna", "group-1", "1177 3016 0123 4567")
        self.assertEqual([a.id for a in self.service.list_own_accounts("balint", "group-1")], [entry.id])
        with self.assertRaisesRegex(AuthorizationError, "admin"):
            self.service.delete_own_account("balint", "group-1", entry.id)
        with self.assertRaises(NotFoundError):
            self.service.delete_own_account("user-c", "group-2", entry.id)  # another group's entry
        self.assertEqual(self.service.delete_own_account("anna", "group-1", entry.id).label, "11773016-01234567")
        self.assertEqual(self.service.list_own_accounts("anna", "group-1"), [])

    def test_own_accounts_over_http(self) -> None:
        token, _ = TokenService(self.storage).create("anna", "group-1", "test")
        headers = {"Authorization": f"Bearer {token}"}
        with TestClient(create_app(self.storage)) as client:
            created = client.post("/v1/own-accounts", json={"label": "Minta Anna"}, headers=headers)
            self.assertEqual(created.status_code, 201)
            self.assertEqual((created.json()["kind"], created.json()["match_key"]), ("name", "minta anna"))
            self.assertEqual(client.post("/v1/own-accounts", json={"label": "MINTA ANNA"}, headers=headers).status_code, 409)
            self.assertEqual(client.post("/v1/own-accounts", json={"label": "12"}, headers=headers).status_code, 400)
            listed = client.get("/v1/own-accounts", headers=headers).json()["own_accounts"]
            self.assertEqual([a["label"] for a in listed], ["Minta Anna"])
            path = f"/v1/own-accounts/{listed[0]['id']}"
            self.assertEqual(client.delete(path, headers=headers).status_code, 200)
            self.assertEqual(client.delete(path, headers=headers).status_code, 404)


if __name__ == "__main__":
    unittest.main()
