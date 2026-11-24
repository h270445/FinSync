"""W2 overview: month totals over deduplicated events (finsync/core/overview.py, GET /v1/overview)."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from finsync.api import create_app
from finsync.core import AuthorizationError, FinSyncService, TokenService
from finsync.core.overview import build_overview
from finsync.storage import FinSyncStorage

NOTIFICATION = "CARD PURCHASE -4500 HUF at Tesco on 2026-09-05 16:42"


class OverviewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        self.service = FinSyncService(self.storage)
        for user, group in (("anna", "group-1"), ("balint", "group-1"), ("user-c", "group-2")):
            self.storage.add_group_membership(user, group)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _manual(self, user: str = "anna", **overrides: object):
        row = {
            "amount": "-4500",
            "currency": "HUF",
            "description": "Weekly shop",
            "merchant": "Tesco",
            "happened_at": "2026-09-05T16:50:00+00:00",
        }
        row.update(overrides)
        return self.service.create_manual_transaction(user, "group-1", row)

    def _bucket(self, buckets, key: str, currency: str = "HUF"):
        return next(b for b in buckets if b.key == key and b.currency == currency)

    def test_a_purchase_reported_by_two_sources_is_counted_once(self) -> None:
        self.service.ingest_notification("anna", "group-1", NOTIFICATION)
        linked = self._manual(user="balint")
        self.assertEqual(linked.match_outcome, "auto_linked")
        overview = self.service.overview("anna", "group-1", "2026-09")
        [total] = overview.totals
        self.assertEqual((total.expense, total.event_count), (Decimal("4500"), 1))
        # The notification is the primary record, so the purchase is Anna's.
        self.assertEqual([m.key for m in overview.members], ["anna"])
        self.assertEqual(self._bucket(overview.categories, "groceries").expense, Decimal("4500"))

    def test_expense_income_categories_and_members_are_summed_separately(self) -> None:
        self._manual(amount="-4500", merchant="Tesco", description="Tesco shop")
        self._manual(user="balint", amount="-890", merchant="BKK", description="bus ticket",
                     happened_at="2026-09-10T08:00:00+00:00")
        self._manual(amount="350000", merchant="Employer", description="salary", direction="income",
                     happened_at="2026-09-10T09:00:00+00:00")
        overview = self.service.overview("anna", "group-1", "2026-09")
        [total] = overview.totals
        self.assertEqual((total.expense, total.income, total.event_count), (Decimal("5390"), Decimal("350000"), 3))
        self.assertEqual(self._bucket(overview.categories, "transport").expense, Decimal("890"))
        anna = self._bucket(overview.members, "anna")
        self.assertEqual((anna.expense, anna.income), (Decimal("4500"), Decimal("350000")))
        self.assertEqual(self._bucket(overview.members, "balint").expense, Decimal("890"))
        # Categories are ordered by spending, largest first.
        self.assertEqual(overview.categories[0].key, "groceries")

    def test_months_follow_the_budapest_calendar_day(self) -> None:
        # 23:30 UTC on Sep 30 is already Oct 1 in Budapest; a date-only entry keeps its own date.
        self._manual(happened_at="2026-09-30T23:30:00+00:00")
        self._manual(happened_at="2026-09-30", merchant="Lidl", description="Lidl shop", amount="-1200")
        self.assertEqual(self.service.overview("anna", "group-1", "2026-10").totals[0].expense, Decimal("4500"))
        self.assertEqual(self.service.overview("anna", "group-1", "2026-09").totals[0].expense, Decimal("1200"))
        self.assertEqual(self.service.overview("anna", "group-1", "2026-10").months, ["2026-10", "2026-09"])

    def test_currencies_are_never_added_together(self) -> None:
        self._manual()
        self._manual(amount="-20", currency="EUR", merchant="Shop", description="souvenir")
        overview = self.service.overview("anna", "group-1", "2026-09")
        self.assertEqual([(t.currency, t.expense) for t in overview.totals],
                         [("EUR", Decimal("20")), ("HUF", Decimal("4500"))])

    def test_events_waiting_for_review_are_counted_in_and_flagged(self) -> None:
        self.service.ingest_notification("anna", "group-1", NOTIFICATION)
        manual = self._manual(happened_at="2026-09-05", merchant=None, description="Weekly shop")
        self.assertEqual(manual.match_outcome, "needs_review")
        [total] = self.service.overview("anna", "group-1", "2026-09").totals
        # Until someone decides, the two records are two events. The later one is flagged: its amount is
        # what the total may overstate if it turns out to be the same purchase.
        self.assertEqual((total.expense, total.event_count), (Decimal("9000"), 2))
        self.assertEqual((total.review_count, total.review_amount), (1, Decimal("4500")))
        [review] = self.service.list_open_reviews("anna", "group-1")
        self.service.confirm_match("anna", "group-1", review.decision_id)
        [total] = self.service.overview("anna", "group-1", "2026-09").totals
        self.assertEqual((total.expense, total.event_count, total.review_count), (Decimal("4500"), 1, 0))

    def test_transfers_are_left_out_and_only_counted(self) -> None:
        self._manual()
        self._manual(amount="-20000", merchant="Balint", description="to Balint", happened_at="2026-09-06T10:00:00+00:00")
        events = self.storage.list_events("group-1")
        # No input produces the transfer direction yet; the rule is checked on the event list itself.
        transfer = next(e for e in events if e.amount == Decimal("-20000"))
        events = [replace(e, direction="transfer") if e is transfer else e for e in events]
        overview = build_overview(events, "2026-09")
        self.assertEqual(overview.totals[0].expense, Decimal("4500"))
        self.assertEqual(overview.transfer_count, 1)
        self.assertNotIn("transfer", {b.key for b in overview.categories})

    def test_an_empty_month_has_no_rows(self) -> None:
        self._manual()
        overview = self.service.overview("anna", "group-1", "2026-12")
        self.assertEqual((overview.totals, overview.categories, overview.members), ([], [], []))
        self.assertEqual(overview.months, ["2026-09"])

    def test_month_must_be_year_dash_month(self) -> None:
        for value in ("2026-13", "2026-9", "09-2026", "2026-09-01"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "YYYY-MM"):
                self.service.overview("anna", "group-1", value)

    def test_other_groups_member_is_refused(self) -> None:
        with self.assertRaises(AuthorizationError):
            self.service.overview("user-c", "group-1", "2026-09")

    def test_overview_over_http(self) -> None:
        self.service.ingest_notification("anna", "group-1", NOTIFICATION)
        token, _ = TokenService(self.storage).create("anna", "group-1", "test")
        with TestClient(create_app(self.storage)) as client:
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/v1/overview", params={"month": "2026-09"}, headers=headers)
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["totals"], [{
                "key": "all", "currency": "HUF", "expense": "4500", "income": "0", "event_count": 1,
                "review_count": 0, "review_amount": "0",
                # Tesco sells many kinds of goods: its usual category is only a suggestion.
                "uncertain_count": 1, "uncertain_amount": "4500", "mixed_count": 0, "mixed_amount": "0",
            }])
            self.assertEqual(body["months"], ["2026-09"])
            bad = client.get("/v1/overview", params={"month": "september"}, headers=headers)
            self.assertEqual((bad.status_code, list(bad.json())), (400, ["error"]))


if __name__ == "__main__":
    unittest.main()
