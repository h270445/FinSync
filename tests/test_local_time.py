"""Times without an offset are Budapest wall-clock time (ADR 0008, point 3)."""

from __future__ import annotations

from datetime import datetime, timezone
import os
import tempfile
import unittest

from finsync.core import FinSyncService
from finsync.ingestion import parse_notification
from finsync.ingestion.local_time import local_to_utc
from finsync.storage import FinSyncStorage


def utc(*parts: int) -> datetime:
    return datetime(*parts, tzinfo=timezone.utc)


class LocalToUtcTest(unittest.TestCase):
    def test_winter_and_summer_offsets(self) -> None:
        self.assertEqual(local_to_utc(datetime(2026, 1, 15, 12, 0)), utc(2026, 1, 15, 11, 0))
        self.assertEqual(local_to_utc(datetime(2026, 7, 15, 12, 0)), utc(2026, 7, 15, 10, 0))

    def test_the_repeated_autumn_hour_takes_the_first_occurrence(self) -> None:
        # 2026-10-25: clocks go back from 03:00 CEST to 02:00 CET, so 02:30 happens twice.
        self.assertEqual(local_to_utc(datetime(2026, 10, 25, 2, 30)), utc(2026, 10, 25, 0, 30))

    def test_a_time_in_the_skipped_spring_hour_moves_forward(self) -> None:
        # 2027-03-28: clocks jump from 02:00 CET to 03:00 CEST; 02:30 does not exist and becomes 03:30 CEST.
        self.assertEqual(local_to_utc(datetime(2027, 3, 28, 2, 30)), utc(2027, 3, 28, 1, 30))

    def test_a_time_with_an_offset_is_only_converted(self) -> None:
        aware = datetime.fromisoformat("2026-11-12T23:30:00+01:00")
        self.assertEqual(local_to_utc(aware), utc(2026, 11, 12, 22, 30))


class LocalTimeInputTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        self.service = FinSyncService(self.storage)
        self.storage.add_group_membership("anna", "lakas")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _manual(self, happened_at: str):
        result = self.service.create_manual_transaction(
            "anna", "lakas", {"amount": "-4990", "currency": "HUF", "description": "Bolt", "happened_at": happened_at}
        )
        return next(tx for tx in self.storage.list_transactions("lakas") if tx.id == result.transaction_id)

    def test_a_manual_time_without_offset_is_budapest_time(self) -> None:
        stored = self._manual("2026-11-12T23:30")  # read as UTC it would be 23:30 UTC
        self.assertEqual((stored.happened_at, stored.happened_at_precision), (utc(2026, 11, 12, 22, 30), "minute"))

    def test_a_manual_time_with_offset_keeps_its_instant(self) -> None:
        self.assertEqual(self._manual("2026-11-12T23:30:00+00:00").happened_at, utc(2026, 11, 12, 23, 30))

    def test_a_date_stays_the_typed_calendar_day(self) -> None:
        stored = self._manual("2026-11-12")
        self.assertEqual((stored.happened_at, stored.happened_at_precision), (utc(2026, 11, 12), "day"))

    def test_a_late_evening_notification_time_matches_a_date_only_entry_of_the_same_local_day(self) -> None:
        dated = self.service.create_manual_transaction(
            "anna", "lakas", {"amount": "-4990", "currency": "HUF", "description": "Bolt", "merchant": "Peldabolt", "happened_at": "2026-11-12"}
        )
        # 23:30 printed in the text is Budapest time (22:30 UTC), on the same calendar day as the
        # dated entry. (The scorer also tolerates a neighbour day, so this guards the outcome, and the
        # exact instant is checked in test_the_synthetic_notification_text_prints_local_time.)
        result = self.service.ingest_notification("anna", "lakas", "CARD PURCHASE -4990 HUF at Peldabolt on 2026-11-12 23:30")
        self.assertIn(result.match_outcome, ("auto_linked", "needs_review"))
        if result.match_outcome == "auto_linked":
            self.assertEqual(result.event_id, dated.event_id)
        else:
            reviews = self.service.list_open_reviews("anna", "lakas")
            self.assertEqual([item.candidate_event.id for item in reviews], [dated.event_id])

    def test_the_synthetic_notification_text_prints_local_time(self) -> None:
        parsed = parse_notification("CARD PURCHASE -4500 HUF at Tesco on 2026-09-05 16:42")
        self.assertEqual(parsed.happened_at, utc(2026, 9, 5, 14, 42))


if __name__ == "__main__":
    unittest.main()
