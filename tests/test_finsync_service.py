from __future__ import annotations

from datetime import datetime, timezone
import os
import tempfile
import unittest

from finsync.parser import parse_notification
from finsync.service import AuthorizationError, FinSyncService
from finsync.storage import FinSyncStorage


class FinSyncServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.db")
        self.storage = FinSyncStorage(self.db_path)
        self.service = FinSyncService(self.storage)
        self.storage.add_group_membership("user-1", "group-1")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_parse_supported_card_notification(self) -> None:
        parsed = parse_notification("CARD PURCHASE -1234.56 HUF at Tesco on 2026-09-01 13:45")
        self.assertEqual(str(parsed.amount), "-1234.56")
        self.assertEqual(parsed.currency, "HUF")
        self.assertEqual(parsed.merchant_or_counterparty, "Tesco")

    def test_notification_ingest_persists_and_categorizes(self) -> None:
        transaction_id = self.service.ingest_notification(
            "user-1",
            "group-1",
            "CARD PURCHASE -1234.56 HUF at Tesco on 2026-09-01 13:45",
        )
        self.assertGreater(transaction_id, 0)

        transactions = self.service.list_group_transactions("user-1", "group-1")
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].category, "groceries")
        self.assertEqual(transactions[0].source, "android_notification")

    def test_manual_transaction_creation(self) -> None:
        transaction_id = self.service.create_manual_transaction(
            "user-1",
            "group-1",
            {
                "amount": "-4990",
                "currency": "huf",
                "description": "Monthly bus pass",
                "merchant": "BKK",
                "happened_at": datetime(2026, 9, 5, 7, 0, tzinfo=timezone.utc).isoformat(),
            },
        )
        self.assertGreater(transaction_id, 0)

        transactions = self.service.list_group_transactions("user-1", "group-1")
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0].currency, "HUF")
        self.assertEqual(transactions[0].category, "transport")

    def test_unauthorized_user_is_rejected(self) -> None:
        with self.assertRaises(AuthorizationError):
            self.service.list_group_transactions("user-2", "group-1")

    def test_bulk_creation(self) -> None:
        ids = self.service.bulk_create_manual_transactions(
            "user-1",
            "group-1",
            [
                {
                    "amount": "-1000",
                    "currency": "HUF",
                    "description": "Taxi",
                    "happened_at": "2026-09-06T10:00:00+00:00",
                },
                {
                    "amount": "-3000",
                    "currency": "HUF",
                    "description": "Rent share",
                    "happened_at": "2026-09-06T11:00:00+00:00",
                },
            ],
        )
        self.assertEqual(len(ids), 2)


if __name__ == "__main__":
    unittest.main()
