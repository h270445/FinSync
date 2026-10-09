from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
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


    def _row(self, **overrides: object) -> dict:
        row = {
            "amount": "-1000",
            "currency": "HUF",
            "description": "Taxi",
            "happened_at": "2026-09-06T10:00:00+00:00",
        }
        row.update(overrides)
        return row

    def test_bulk_creation_is_atomic_when_a_row_is_invalid(self) -> None:
        with self.assertRaisesRegex(ValueError, "Row 1: Amount cannot be zero"):
            self.service.bulk_create_manual_transactions(
                "user-1", "group-1", [self._row(), self._row(amount="0")]
            )
        self.assertEqual(self.service.list_group_transactions("user-1", "group-1"), [])

    def test_bulk_storage_failure_rolls_back_earlier_rows(self) -> None:
        def records():
            yield {
                "user_id": "user-1",
                "group_id": "group-1",
                "amount": Decimal("-1"),
                "currency": "HUF",
                "description": "Taxi",
                "merchant": None,
                "category": "transport",
                "source": "manual",
                "happened_at": datetime(2026, 9, 6, tzinfo=timezone.utc),
            }
            raise RuntimeError("storage failed mid-batch")

        with self.assertRaises(RuntimeError):
            self.storage.insert_transactions(records())
        self.assertEqual(self.storage.list_transactions("group-1"), [])

    def test_non_finite_amounts_are_rejected(self) -> None:
        for amount in ("NaN", "nan", "sNaN", "Infinity", "-Infinity", float("nan")):
            with self.subTest(amount=amount):
                with self.assertRaisesRegex(ValueError, "Invalid amount"):
                    self.service.create_manual_transaction("user-1", "group-1", self._row(amount=amount))
        self.assertEqual(self.service.list_group_transactions("user-1", "group-1"), [])

    def test_non_object_bulk_row_is_a_validation_error(self) -> None:
        for bad_row in ("oops", 42, None, ["-1000", "HUF"]):
            with self.subTest(row=bad_row):
                with self.assertRaisesRegex(ValueError, "Row 1: Transaction must be a JSON object"):
                    self.service.bulk_create_manual_transactions(
                        "user-1", "group-1", [self._row(), bad_row]
                    )
        self.assertEqual(self.service.list_group_transactions("user-1", "group-1"), [])

    def test_non_object_bulk_row_returns_400_from_api(self) -> None:
        from http.server import ThreadingHTTPServer
        import http.client
        import json
        import threading

        # finsync.api opens a default database at import time; keep it inside the tempdir.
        previous_cwd = os.getcwd()
        os.chdir(self.tempdir.name)
        try:
            from finsync.api import FinSyncRequestHandler
        finally:
            os.chdir(previous_cwd)

        handler = type("Handler", (FinSyncRequestHandler,), {"service": self.service})
        handler.log_message = lambda *args: None
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", server.server_address[1])
            connection.request(
                "POST",
                "/v1/transactions/bulk",
                body=json.dumps({"rows": [self._row(), "oops"]}),
                headers={"X-User-Id": "user-1", "X-Group-Id": "group-1", "Content-Type": "application/json"},
            )
            response = connection.getresponse()
            body = json.loads(response.read())
            connection.close()
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(response.status, 400)
        self.assertIn("Transaction must be a JSON object", body["error"])
        self.assertEqual(self.service.list_group_transactions("user-1", "group-1"), [])


if __name__ == "__main__":
    unittest.main()
