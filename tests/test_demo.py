"""The M2 demo seed (`python -m finsync.api.demo`) gives the situation the demo guide walks through."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime
import io
from pathlib import Path
import tempfile
import unittest

from finsync.api import demo
from finsync.core import FinSyncService, SessionService
from finsync.core.overview import is_uncertain
from finsync.storage import FinSyncStorage

TODAY = date(2026, 11, 26)


class DemoSeedTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.storage = FinSyncStorage(str(Path(self.tempdir.name) / "demo.db"))
        self.token = demo.seed(self.storage, TODAY)
        self.service = FinSyncService(self.storage)

    def events(self):
        return self.service.list_group_events(demo.ADMIN, demo.GROUP)

    def test_the_seed_has_members_sign_in_a_token_and_one_open_review(self) -> None:
        roles = {user: role for user, _email, role in self.storage.list_group_members(demo.GROUP)}
        self.assertEqual(roles, {"anna": "admin", "balint": "member"})
        self.assertIsNotNone(SessionService(self.storage).sign_in("anna@example.org", demo.DEMO_PASSWORD))
        self.assertTrue(self.token.startswith("fs_"))
        self.assertEqual(len(self.service.list_open_reviews(demo.ADMIN, demo.GROUP)), 1)

        by_amount = {str(event.amount): event for event in self.events()}
        self.assertEqual(by_amount["-20000"].direction, "transfer")
        self.assertEqual(by_amount["-1450"].category_confidence, "high")  # BKK, settled by the dictionary
        self.assertTrue(is_uncertain(by_amount["-12990"]))  # Tesco: a mixed-assortment supermarket
        self.assertTrue(is_uncertain(by_amount["-3200"]))  # a cryptic card terminal text

    def test_the_phone_purchase_and_the_export_row_become_one_event_and_the_coffees_stay_two(self) -> None:
        before = len(self.events())
        phone = self.service.ingest_notification(
            demo.ADMIN, demo.GROUP, demo.PHONE_NOTIFICATION,
            posted_at=datetime.combine(TODAY, datetime.min.time().replace(hour=10, minute=30), demo.BUDAPEST).isoformat(),
        )
        result = self.service.import_file(demo.ADMIN, demo.GROUP, demo.bank_export(TODAY))
        outcomes = [row.match_outcome for row in result.results]
        self.assertEqual(outcomes, ["auto_linked", "separate", "separate"])
        self.assertEqual(result.results[0].event_id, phone.event_id)
        self.assertEqual(len(self.events()), before + 3)

    def test_the_command_refuses_an_existing_file_and_writes_the_export(self) -> None:
        existing = Path(self.tempdir.name) / "demo.db"
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertEqual(demo.main(["--db", str(existing)]), 2)
        self.assertIn("already", err.getvalue())  # the file, or on PostgreSQL the group

        fresh = Path(self.tempdir.name) / "fresh.db"
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(demo.main(["--db", str(fresh), "--export-dir", self.tempdir.name]), 0)
        self.assertIn("demo-csalad", out.getvalue())
        self.assertTrue((Path(self.tempdir.name) / demo.EXPORT_NAME).read_text(encoding="utf-8").startswith("date,"))


if __name__ == "__main__":
    unittest.main()
