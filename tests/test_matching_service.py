from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from finsync.core import FinSyncService
from finsync.storage import FinSyncStorage

NOTIFICATION = "CARD PURCHASE -4500 HUF at Tesco on 2026-09-05 16:42"


class MatchingServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.db")
        self.storage = FinSyncStorage(self.db_path)
        self.service = FinSyncService(self.storage)
        for user in ("user-1", "user-2"):
            self.storage.add_group_membership(user, "group-1")
        self.storage.add_group_membership("user-1", "group-2")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _manual(self, user: str = "user-1", group: str = "group-1", **overrides: object):
        row = {
            "amount": "-4500",
            "currency": "HUF",
            "description": "Weekly shop",
            "merchant": "Tesco",
            "happened_at": "2026-09-05T16:50:00+00:00",
        }
        row.update(overrides)
        return self.service.create_manual_transaction(user, group, row)

    def _events(self, group: str = "group-1"):
        return self.service.list_group_events("user-1", group)

    # The four hand-decided examples (supervisor feedback, 2026-10-16).

    def test_repeated_notification_is_an_exact_duplicate(self) -> None:
        first = self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        second = self.service.ingest_notification("user-1", "group-1", NOTIFICATION)

        self.assertEqual(first.match_outcome, "separate")
        self.assertEqual(second.match_outcome, "exact_duplicate")
        self.assertEqual(second.event_id, first.event_id)
        events = self._events()
        self.assertEqual(len(events), 1)
        self.assertEqual(len(events[0].transactions), 2)
        duplicate = next(tx for tx in events[0].transactions if tx.id == second.transaction_id)
        self.assertEqual(duplicate.duplicate_of_id, first.transaction_id)

    def test_arrival_order_does_not_change_the_result(self) -> None:
        manual = self._manual()
        notification = self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        self.assertEqual(notification.match_outcome, "auto_linked")
        self.assertEqual(notification.event_id, manual.event_id)
        manual_first = self._events()

        self.tearDown()
        self.setUp()
        notification = self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        manual = self._manual()
        self.assertEqual(manual.match_outcome, "auto_linked")
        self.assertEqual(manual.event_id, notification.event_id)
        notification_first = self._events()

        for events in (manual_first, notification_first):
            self.assertEqual(len(events), 1)
            self.assertEqual(len(events[0].transactions), 2)
        # The notification is the primary record either way, so the shown values are the same.
        shown = [(e[0].amount, e[0].happened_at, e[0].merchant) for e in (manual_first, notification_first)]
        self.assertEqual(shown[0], shown[1])

    def test_date_only_manual_entry_is_compared_by_day(self) -> None:
        self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        with_merchant = self._manual(happened_at="2026-09-05")
        self.assertEqual(with_merchant.match_outcome, "auto_linked")

        self.tearDown()
        self.setUp()
        self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        # Without a merchant, a description that names the shop is enough to link.
        names_the_shop = self._manual(happened_at="2026-09-05", merchant=None, description="Tesco weekly shop")
        self.assertEqual(names_the_shop.match_outcome, "auto_linked")

        self.tearDown()
        self.setUp()
        self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        # A description that does not name the shop leaves only amount and day, so a person decides.
        description_only = self._manual(happened_at="2026-09-05", merchant=None, description="Weekly shop")
        self.assertEqual(description_only.match_outcome, "needs_review")
        events = self._events()
        self.assertEqual(len(events), 2)
        self.assertEqual({event.review_state for event in events}, {"clear", "needs_review"})

    def test_two_same_amount_notifications_stay_separate(self) -> None:
        first = self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        second = self.service.ingest_notification(
            "user-1", "group-1", "CARD PURCHASE -4500 HUF at Tesco on 2026-09-05 16:52"
        )
        self.assertEqual(second.match_outcome, "separate")
        self.assertNotEqual(first.event_id, second.event_id)
        self.assertEqual(len(self._events()), 2)

    # Further scenarios from the design.

    def test_two_members_log_the_same_dinner(self) -> None:
        first = self._manual(description="Dinner", merchant="Pizzeria Roma", amount="-12000")
        second = self._manual(user="user-2", description="Dinner", merchant="Pizzeria Roma", amount="-12000")
        self.assertEqual(second.match_outcome, "auto_linked")
        self.assertEqual(second.event_id, first.event_id)

    def test_rounded_manual_amount_is_a_candidate(self) -> None:
        self.service.ingest_notification("user-1", "group-1", "CARD PURCHASE -1234.56 HUF at Tesco on 2026-09-05 16:42")
        result = self._manual(amount="-1235")
        decision = self.storage.list_decisions("group-1")[-1]
        self.assertEqual(decision["features"]["a"], 0.7)
        self.assertIn(result.match_outcome, ("auto_linked", "needs_review"))

    def test_manual_without_merchant_between_two_notifications_needs_review(self) -> None:
        self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        self.service.ingest_notification("user-1", "group-1", "CARD PURCHASE -4500 HUF at Tesco on 2026-09-05 17:10")
        result = self._manual(merchant=None, description="Shopping")
        self.assertEqual(result.match_outcome, "needs_review")

    def test_four_days_apart_is_separate(self) -> None:
        self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        self.assertEqual(self._manual(happened_at="2026-09-09").match_outcome, "separate")

    def test_matching_never_crosses_groups(self) -> None:
        self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        self.assertEqual(self._manual(group="group-2").match_outcome, "separate")
        self.assertEqual(len(self._events("group-2")), 1)

    def test_identical_manual_rows_go_to_review_unless_they_share_a_reference(self) -> None:
        self._manual()
        self.assertEqual(self._manual().match_outcome, "needs_review")

        first = self._manual(source_ref="sheet-row-7", happened_at="2026-09-01T10:00:00+00:00")
        again = self._manual(source_ref="sheet-row-7", happened_at="2026-09-01T10:00:00+00:00")
        self.assertEqual(again.match_outcome, "exact_duplicate")
        self.assertEqual(again.event_id, first.event_id)

    def test_bulk_rows_share_a_batch_and_are_matched(self) -> None:
        self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        results = self.service.bulk_create_manual_transactions(
            "user-1",
            "group-1",
            [
                {"amount": "-4500", "currency": "HUF", "description": "Tesco", "happened_at": "2026-09-05"},
                {"amount": "-900", "currency": "HUF", "description": "Bus ticket", "happened_at": "2026-09-05"},
            ],
        )
        self.assertEqual([result.match_outcome for result in results], ["auto_linked", "separate"])
        batch_ids = {tx.import_batch_id for tx in self.service.list_group_transactions("user-1", "group-1") if tx.source == "manual"}
        self.assertEqual(len(batch_ids), 1)
        self.assertIsNotNone(batch_ids.pop())

    def test_bulk_with_an_invalid_third_row_stores_nothing(self) -> None:
        self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        rows = [
            {"amount": "-4500", "currency": "HUF", "description": "Tesco", "happened_at": "2026-09-05"},
            {"amount": "-900", "currency": "HUF", "description": "Bus ticket", "happened_at": "2026-09-05"},
            {"amount": "abc", "currency": "HUF", "description": "Broken", "happened_at": "2026-09-05"},
        ]
        with self.assertRaisesRegex(ValueError, "Row 2"):
            self.service.bulk_create_manual_transactions("user-1", "group-1", rows)
        self.assertEqual(len(self.service.list_group_transactions("user-1", "group-1")), 1)
        self.assertEqual(len(self._events()), 1)
        self.assertEqual([d["outcome"] for d in self.storage.list_decisions("group-1")], ["separate"])

    def test_direction_overrides_the_typed_sign(self) -> None:
        self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        result = self._manual(amount="4500", direction="expense")
        self.assertEqual(result.match_outcome, "auto_linked")
        with self.assertRaisesRegex(ValueError, "direction"):
            self._manual(direction="spending")

    def test_every_record_has_a_decision_with_matcher_version(self) -> None:
        self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        self._manual()
        decisions = self.storage.list_decisions("group-1")
        self.assertEqual([d["outcome"] for d in decisions], ["separate", "auto_linked"])
        self.assertTrue(all(d["matcher_version"] == "rules-3" for d in decisions))


class MigrationTest(unittest.TestCase):
    def test_existing_rows_become_separate_events(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            db_path = os.path.join(tempdir, "legacy.db")
            connection = sqlite3.connect(db_path)
            connection.executescript(
                """
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, group_id TEXT NOT NULL,
                    amount TEXT NOT NULL, currency TEXT NOT NULL, description TEXT NOT NULL, merchant TEXT,
                    category TEXT NOT NULL, source TEXT NOT NULL, happened_at TEXT NOT NULL, created_at TEXT NOT NULL
                );
                INSERT INTO transactions VALUES
                    (1, 'user-1', 'group-1', '-4500', 'HUF', 'card_purchase:Tesco', 'Tesco', 'groceries',
                     'android_notification', '2026-09-05T16:42:00+00:00', '2026-09-05T16:42:05+00:00'),
                    (2, 'user-1', 'group-1', '-4500', 'HUF', 'Weekly shop', 'Tesco', 'groceries',
                     'manual', '2026-09-05T16:50:00+00:00', '2026-09-05T17:00:00+00:00');
                """
            )
            connection.close()

            storage = FinSyncStorage(db_path)
            events = storage.list_events("group-1")
            self.assertEqual(len(events), 2)
            decisions = storage.list_decisions("group-1")
            self.assertEqual({(d["outcome"], d["decided_by"]) for d in decisions}, {("separate", "migration")})

            FinSyncStorage(db_path)  # opening again does not migrate twice
            self.assertEqual(len(storage.list_events("group-1")), 2)


if __name__ == "__main__":
    unittest.main()
