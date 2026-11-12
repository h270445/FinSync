"""Android ingest: the OTP Bank format, posted_at and source_ref (ADR 0008, M2 Android app).

Every notification text here is made up; it follows the masked shapes recorded in
docs/design/android-notification-spike.md (2026-10-27 and 2026-10-28).
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from finsync.api import create_app
from finsync.core import FinSyncService, TokenService
from finsync.ingestion import parse_notification
from finsync.storage import FinSyncStorage

# Shape: "-9 999 Aa aaaaaaaa aaaaaaaaa aaaaaaaaaa a AAAAAAAAAA AAAAAA 99. aaaaaaaaaaaa."
PURCHASE = "-4 990 Ft értékben vásárolt a PELDABOLT KFT 12. üzletében."
PURCHASE_TITLE = "Kártyás vásárlás!"
# Shape: "-9 999 Aa, Aaaaa Aaaaaa Aaaaaa"
TRANSFER = "-12 000 Ft, Minta Anna Beata"
POSTED_AT = "2026-11-12T09:15:00.123+00:00"


class OtpFormatTest(unittest.TestCase):
    def test_card_purchase(self) -> None:
        parsed = parse_notification(PURCHASE)
        self.assertEqual((str(parsed.amount), parsed.currency), ("-4990", "HUF"))
        self.assertEqual(parsed.merchant_or_counterparty, "PELDABOLT KFT")
        self.assertEqual(parsed.description, "card_purchase:PELDABOLT KFT")
        self.assertIsNone(parsed.happened_at)

    def test_transfers_both_ways(self) -> None:
        outgoing = parse_notification(TRANSFER)
        self.assertEqual((str(outgoing.amount), outgoing.merchant_or_counterparty), ("-12000", "Minta Anna Beata"))
        self.assertEqual(outgoing.description, "outgoing_transfer:Minta Anna Beata")
        incoming = parse_notification("+1 500 Ft, Minta Bela")
        self.assertEqual(incoming.description, "incoming_transfer:Minta Bela")

    def test_amount_forms(self) -> None:
        cases = {
            "-990 Ft vásárlás a SPAR-123 boltban.": ("-990", "HUF", "SPAR-123"),
            "-1 234 567 Ft vásárlás a NAGY ÁRUHÁZ boltban.": ("-1234567", "HUF", "NAGY ÁRUHÁZ"),
            "-12,50 EUR vásárlás a CAFE PELDA üzletben.": ("-12.50", "EUR", "CAFE PELDA"),
            "-4 990 Ft vásárlás a PELDABOLT üzletben.": ("-4990", "HUF", "PELDABOLT"),
        }
        for text, (amount, currency, merchant) in cases.items():
            with self.subTest(text=text):
                parsed = parse_notification(text)
                self.assertEqual((str(parsed.amount), parsed.currency, parsed.merchant_or_counterparty), (amount, currency, merchant))

    def test_texts_that_are_not_transactions_are_refused(self) -> None:
        for text in (
            "Nyerj 10 EUR jóváírást, ha meghívod a barátodat!",  # marketing with an amount
            "-4 990 Ft értékben vásároltál, köszönjük.",  # amount first but no merchant
            "-4 990 Ft,",  # transfer without a counterparty
            "4 990 Ft, Minta Anna",  # no sign
            "-4990Ft, Minta Anna",  # no space before the currency
            "Új üzenete érkezett.",
            "",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_notification(text)


class AndroidIngestServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        self.service = FinSyncService(self.storage)
        self.storage.add_group_membership("anna", "lakas")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _stored(self, transaction_id: int):
        return next(tx for tx in self.storage.list_transactions("lakas") if tx.id == transaction_id)

    def _ingest(self, text: str = PURCHASE, **fields):
        fields = {"title": PURCHASE_TITLE, "posted_at": POSTED_AT, "source_ref": "000000101", **fields}
        return self.service.ingest_notification("anna", "lakas", text, **fields)

    def test_the_post_time_and_reference_are_stored(self) -> None:
        result = self._ingest()
        stored = self._stored(result.transaction_id)
        self.assertEqual(stored.happened_at, datetime(2026, 11, 12, 9, 15, 0, 123000, tzinfo=timezone.utc))
        self.assertEqual(stored.happened_at_precision, "minute")
        self.assertEqual(stored.source_ref, "000000101")
        self.assertEqual((stored.source, stored.merchant, str(stored.amount)), ("android_notification", "PELDABOLT KFT", "-4990"))

    def test_an_offset_is_converted_to_utc(self) -> None:
        result = self._ingest(posted_at="2026-11-12T23:30:00+01:00")
        stored = self._stored(result.transaction_id)
        self.assertEqual(stored.happened_at, datetime(2026, 11, 12, 22, 30, tzinfo=timezone.utc))

    def test_a_retry_is_a_re_delivery(self) -> None:
        first = self._ingest()
        again = self._ingest()
        self.assertEqual(again.match_outcome, "exact_duplicate")
        self.assertEqual(again.event_id, first.event_id)
        # The same post time written differently is still the same notification.
        third = self._ingest(posted_at="2026-11-12T10:15:00.123+01:00")
        self.assertEqual(third.match_outcome, "exact_duplicate")
        self.assertEqual(len(self.service.list_group_events("anna", "lakas")), 1)

    def test_two_identical_purchases_stay_two_events(self) -> None:
        first = self._ingest(source_ref="000000101")
        second = self._ingest(source_ref="000000102", posted_at="2026-11-12T09:16:00+00:00")
        self.assertNotEqual(second.match_outcome, "exact_duplicate")
        self.assertNotEqual(second.event_id, first.event_id)

    def test_the_notification_matches_a_date_only_manual_entry_of_the_same_budapest_day(self) -> None:
        manual = self.service.create_manual_transaction(
            "anna", "lakas", {"amount": "-4990", "currency": "HUF", "description": "Bolt", "merchant": "Peldabolt", "happened_at": "2026-11-12"}
        )
        # 23:30 in Budapest is 22:30 UTC on the same day.
        result = self._ingest(posted_at="2026-11-12T22:30:00+00:00")
        self.assertIn(result.match_outcome, ("auto_linked", "needs_review"))
        if result.match_outcome == "auto_linked":
            self.assertEqual(result.event_id, manual.event_id)
        else:
            reviews = self.service.list_open_reviews("anna", "lakas")
            self.assertEqual([item.candidate_event.id for item in reviews], [manual.event_id])

    def test_refused_input_stores_nothing(self) -> None:
        cases = {
            "no time anywhere": (PURCHASE, {"posted_at": None}),
            "no offset": (PURCHASE, {"posted_at": "2026-11-12T09:15:00"}),
            "not a time": (PURCHASE, {"posted_at": "tegnap"}),
            "marketing": ("Nyerj 10 EUR jóváírást!", {}),
        }
        for name, (text, fields) in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                self._ingest(text, **fields)
        self.assertEqual(self.storage.list_transactions("lakas"), [])

    def test_the_synthetic_format_still_works_without_the_new_fields(self) -> None:
        result = self.service.ingest_notification("anna", "lakas", "CARD PURCHASE -4500 HUF at Tesco on 2026-09-05 16:42")
        self.assertEqual(result.match_outcome, "separate")


class AndroidIngestApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        self.storage.add_group_membership("anna", "lakas")
        token, _ = TokenService(self.storage).create("anna", "lakas", "Anna telefon")
        self.headers = {"Authorization": f"Bearer {token}"}
        self.client = TestClient(create_app(self.storage))

    def tearDown(self) -> None:
        self.client.close()
        self.tempdir.cleanup()

    def test_the_phone_sends_text_title_time_and_reference(self) -> None:
        body = {"message": TRANSFER, "title": "Utalás indítva", "posted_at": POSTED_AT, "source_ref": "000000201"}
        first = self.client.post("/v1/notifications/ingest", json=body, headers=self.headers)
        self.assertEqual(first.status_code, 201, first.text)
        retry = self.client.post("/v1/notifications/ingest", json=body, headers=self.headers)
        self.assertEqual(retry.json()["match_outcome"], "exact_duplicate")
        self.assertEqual(retry.json()["event_id"], first.json()["event_id"])

    def test_a_non_transaction_is_a_400_so_the_phone_does_not_retry(self) -> None:
        body = {"message": "Nyerj 10 EUR jóváírást!", "posted_at": POSTED_AT}
        response = self.client.post("/v1/notifications/ingest", json=body, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.storage.list_transactions("lakas"), [])


if __name__ == "__main__":
    unittest.main()
