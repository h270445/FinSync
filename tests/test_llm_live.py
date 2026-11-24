"""The LLM layer in the live flow: never by default, the admin's schedule, "ask for a suggestion now", the
monthly budget, and a member's decision always winning ([design](../docs/design/categorization.md#when-the-llm-is-called-proposed-by-the-author-2026-11-19)).

Every model answer comes from tests/fake_llm.py; no test makes a paid call.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from finsync.api import create_app
from finsync.core import AuthorizationError, ConflictError, FinSyncService, LlmUnavailable, TokenService, is_uncertain
from finsync.core.llm_schedule import month_start, next_due, validate_settings
from finsync.storage import FinSyncStorage, LlmSettingsRecord

from fake_llm import ScriptedClient, fake_categorizer

UTC = timezone.utc
LATER = timedelta(days=9)  # past any daily, weekly or 24-hour due time


class ScheduleTest(unittest.TestCase):
    def test_due_times_follow_the_setting_in_budapest_time(self) -> None:
        arrived = datetime(2026, 11, 24, 18, 30, tzinfo=UTC)  # 19:30 in Budapest (CET)
        settings = lambda **kw: LlmSettingsRecord("g", **kw)  # noqa: E731
        self.assertIsNone(next_due(settings(), arrived))
        self.assertEqual(next_due(settings(mode="after_arrival", hours_after=24), arrived), arrived + timedelta(hours=24))
        # 20:00 Budapest is 19:00 UTC: later the same day.
        self.assertEqual(next_due(settings(mode="daily", run_time="20:00"), arrived), datetime(2026, 11, 24, 19, 0, tzinfo=UTC))
        # 19:00 Budapest has passed: the next day.
        self.assertEqual(next_due(settings(mode="daily", run_time="19:00"), arrived), datetime(2026, 11, 25, 18, 0, tzinfo=UTC))
        # Weekly on Sunday (6) at 20:00: Sunday 2026-11-29.
        self.assertEqual(
            next_due(settings(mode="weekly", weekday=6, run_time="20:00"), arrived), datetime(2026, 11, 29, 19, 0, tzinfo=UTC)
        )
        # Summer time: 20:00 in Budapest is 18:00 UTC in July.
        july = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)
        self.assertEqual(next_due(settings(mode="daily", run_time="20:00"), july), datetime(2026, 7, 1, 18, 0, tzinfo=UTC))

    def test_invalid_settings_are_refused(self) -> None:
        for kwargs, reason in (
            ({"mode": "sometimes"}, "mode"),
            ({"mode": "after_arrival", "hours_after": 0}, "hours_after"),
            ({"mode": "daily", "run_time": "8:00"}, "run_time"),
            ({"mode": "weekly", "weekday": 7}, "weekday"),
            ({"mode": "never", "monthly_budget_usd": "-1"}, "monthly_budget_usd"),
            ({"mode": "never", "monthly_budget_usd": "sok"}, "monthly_budget_usd"),
        ):
            full = {"hours_after": 24, "run_time": "20:00", "weekday": 6, "monthly_budget_usd": "1", **kwargs}
            with self.subTest(kwargs), self.assertRaisesRegex(ValueError, reason):
                validate_settings("g", full.pop("mode"), **full)

    def test_the_budget_month_starts_at_budapest_midnight(self) -> None:
        self.assertEqual(month_start(datetime(2026, 11, 30, 23, 30, tzinfo=UTC)), datetime(2026, 11, 30, 23, 0, tzinfo=UTC))
        self.assertEqual(month_start(datetime(2026, 11, 15, 12, 0, tzinfo=UTC)), datetime(2026, 10, 31, 23, 0, tzinfo=UTC))


class LiveLlmTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        for user, group in (("anna", "group-1"), ("balint", "group-1"), ("user-c", "group-2")):
            self.storage.add_group_membership(user, group)  # anna is the admin of group 1
        self.use_model("clothing")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def use_model(self, answers) -> None:
        self.llm = fake_categorizer(answers)
        self.service = FinSyncService(self.storage, self.llm)

    @property
    def client(self) -> ScriptedClient:
        return self.llm.client  # type: ignore[return-value]

    def _manual(self, merchant: str = "Tesco", amount: str = "-12000", description: str = "Bevasarlas") -> int:
        return self.service.create_manual_transaction("anna", "group-1", {
            "amount": amount, "currency": "HUF", "description": description, "merchant": merchant,
            "happened_at": "2026-11-20T10:00",
        }).event_id

    def _event(self, event_id: int):
        return next(e for e in self.storage.list_events("group-1") if e.id == event_id)

    def _later(self) -> datetime:
        return datetime.now(UTC) + LATER

    def test_nothing_is_sent_by_default(self) -> None:
        event_id = self._manual()
        self.assertIsNone(self._event(event_id).llm_due_at)
        self.assertEqual(self.service.run_due_llm(self._later()), 0)
        self.assertEqual(self.client.calls, 0)
        status = self.service.llm_status("balint", "group-1")
        self.assertEqual((status.settings.mode, status.available, status.spent_this_month_usd), ("never", True, Decimal("0")))

    def test_the_schedule_asks_about_uncertain_events_only_and_settles_a_clear_answer(self) -> None:
        tesco = self._manual()
        bkk = self._manual("BKK", "-850")  # a clear merchant: never sent
        with self.assertRaisesRegex(AuthorizationError, "admin"):
            self.service.set_llm_settings("balint", "group-1", mode="daily")
        self.service.set_llm_settings("anna", "group-1", mode="daily", run_time="20:00")
        self.assertIsNotNone(self._event(tesco).llm_due_at)
        self.assertIsNone(self._event(bkk).llm_due_at)
        # A record stored after the setting is scheduled too.
        later = self._manual("Minta Kozert", "-3450")
        self.assertIsNotNone(self._event(later).llm_due_at)

        self.assertEqual(self.service.run_due_llm(datetime.now(UTC) - timedelta(hours=1)), 0)  # not due yet
        self.assertEqual(self.service.run_due_llm(self._later()), 2)
        event = self._event(tesco)
        self.assertEqual(
            (event.category, event.category_source, event.category_confidence, event.category_agreement, event.llm_due_at),
            ("clothing", "llm", "high", 1.0, None),
        )
        self.assertEqual({tx.category_source for tx in event.transactions}, {"llm"})
        # Only merchant, description and amount were sent: no member, no group.
        self.assertIn("Merchant: Tesco\nDescription: Bevasarlas\nAmount: 12000 HUF", self.client.prompts[0])
        self.assertFalse(any("anna" in prompt or "group-1" in prompt for prompt in self.client.prompts))
        spent = self.service.llm_status("anna", "group-1").spent_this_month_usd
        self.assertGreater(spent, Decimal("0"))
        self.assertEqual(self.service.run_due_llm(self._later()), 0)  # nothing left

    def test_an_unsure_model_leaves_the_suggestion(self) -> None:
        self.use_model(["clothing", "groceries", "household", "unknown", "unknown"])  # share 0.2 < 0.4
        event_id = self._manual()
        self.service.set_llm_settings("anna", "group-1", mode="after_arrival", hours_after=24)
        self.assertEqual(self.service.run_due_llm(datetime.now(UTC) + timedelta(hours=1)), 0)
        self.assertEqual(self.service.run_due_llm(datetime.now(UTC) + timedelta(hours=25)), 1)
        event = self._event(event_id)
        self.assertEqual((event.category, event.category_source, event.category_confidence), ("groceries", "dictionary", "low"))
        self.assertIsNone(event.llm_due_at)  # asked once; a member decides the rest

    def test_a_members_decision_is_never_overwritten(self) -> None:
        decided = self._manual()
        self.service.set_llm_settings("anna", "group-1", mode="daily")
        self.service.set_event_category("balint", "group-1", decided, "household")
        self.assertIsNone(self._event(decided).llm_due_at)  # decided meanwhile: skipped
        self.assertEqual(self.service.run_due_llm(self._later()), 0)
        self.assertEqual(self.client.calls, 0)

        # A member deciding while the model is being asked wins too.
        racing = self._manual("Minta Kozert", "-3450")
        service = self.service

        class DecidesDuringTheCall(ScriptedClient):
            def complete(self, system, user):
                if self.calls == 0:
                    service.set_event_category("balint", "group-1", racing, "groceries")
                return super().complete(system, user)

        self.llm.client = DecidesDuringTheCall("clothing")
        self.service.run_due_llm(self._later())
        event = self._event(racing)
        self.assertEqual((event.category, event.category_source), ("groceries", "user"))

    def test_ask_now_works_in_every_mode_and_is_refused_when_it_cannot_help(self) -> None:
        event_id = self._manual()
        answered = self.service.suggest_category_now("balint", "group-1", event_id)
        self.assertEqual((answered.category, answered.category_source), ("clothing", "llm"))
        with self.assertRaisesRegex(ConflictError, "settled"):
            self.service.suggest_category_now("balint", "group-1", event_id)
        # The same text again comes from the cache: no new call, no cost.
        calls = self.client.calls
        second = self._manual(amount="-12000")
        self.service.suggest_category_now("balint", "group-1", second)
        self.assertEqual(self.client.calls, calls)
        # No model on the server.
        without = FinSyncService(self.storage)
        with self.assertRaisesRegex(LlmUnavailable, "configured"):
            without.suggest_category_now("balint", "group-1", self._manual("Spar"))

    def test_the_monthly_budget_stops_the_calls(self) -> None:
        self.service.set_llm_settings("anna", "group-1", mode="daily", monthly_budget_usd="0")
        event_id = self._manual()
        self.assertTrue(self.service.llm_status("anna", "group-1").budget_exhausted)
        with self.assertRaisesRegex(LlmUnavailable, "budget"):
            self.service.suggest_category_now("anna", "group-1", event_id)
        self.assertEqual(self.service.run_due_llm(self._later()), 0)
        self.assertEqual(self.client.calls, 0)
        self.assertIsNotNone(self._event(event_id).llm_due_at)  # still due when the budget allows again

    def test_never_clears_the_due_times_and_transfers_are_never_sent(self) -> None:
        event_id = self._manual()
        self.service.set_llm_settings("anna", "group-1", mode="daily")
        self.service.set_event_transfer("anna", "group-1", event_id, True)
        self.assertIsNone(self._event(event_id).llm_due_at)
        other = self._manual("Spar")
        self.service.set_llm_settings("anna", "group-1", mode="never")
        self.assertIsNone(self._event(other).llm_due_at)

    def test_income_is_never_uncertain_and_never_sent(self) -> None:
        salary = self.service.create_manual_transaction("anna", "group-1", {
            "amount": "450000", "currency": "HUF", "description": "MUNKABER", "happened_at": "2026-11-20",
            "direction": "income",
        }).event_id
        self.assertFalse(is_uncertain(self._event(salary)))
        self.service.set_llm_settings("anna", "group-1", mode="daily")
        self.assertIsNone(self._event(salary).llm_due_at)
        with self.assertRaisesRegex(ConflictError, "settled"):
            self.service.suggest_category_now("anna", "group-1", salary)
        self.assertEqual(self.service.run_due_llm(self._later()), 0)
        self.assertEqual(self.client.calls, 0)
        self.assertEqual(self.service.overview("anna", "group-1").totals[0].uncertain_count, 0)

    def test_over_http(self) -> None:
        event_id = self._manual()
        token, _ = TokenService(self.storage).create("anna", "group-1", "phone")
        other, _ = TokenService(self.storage).create("user-c", "group-2", "phone")
        bearer = {"Authorization": f"Bearer {token}"}
        with TestClient(create_app(self.storage, self.llm), base_url="https://testserver") as client:
            settings = client.get("/v1/llm-settings", headers=bearer).json()
            self.assertEqual((settings["mode"], settings["available"], settings["model"]), ("never", True, "claude-haiku-5-5"))
            refused = client.put("/v1/llm-settings", json={"mode": "daily"}, headers=bearer)  # an admin's token
            self.assertEqual(refused.status_code, 403)
            self.assertIn("web app", refused.json()["error"])
            foreign = client.post(f"/v1/events/{event_id}/llm-suggestion", headers={"Authorization": f"Bearer {other}"})
            self.assertEqual(foreign.status_code, 404)
            answered = client.post(f"/v1/events/{event_id}/llm-suggestion", headers=bearer)
            self.assertEqual(answered.status_code, 200)
            self.assertEqual((answered.json()["category_source"], answered.json()["category_agreement"]), ("llm", 1.0))
            self.assertEqual(client.post(f"/v1/events/{event_id}/llm-suggestion", headers=bearer).status_code, 409)

            # The web session (with its CSRF token) may change the setting.
            from finsync.core import SessionService

            SessionService(self.storage).set_password("anna", "jelszo-12345")
            signed_in = client.post("/v1/session", json={"login": "anna", "password": "jelszo-12345"}).json()
            csrf = {"X-CSRF-Token": signed_in["csrf_token"]}
            saved = client.put("/v1/llm-settings", json={"mode": "weekly", "weekday": 0, "run_time": "07:30"}, headers=csrf)
            self.assertEqual(saved.status_code, 200, saved.text)
            self.assertEqual((saved.json()["mode"], saved.json()["updated_by"]), ("weekly", "anna"))
            bad = client.put("/v1/llm-settings", json={"mode": "weekly", "run_time": "7:30"}, headers=csrf)
            self.assertEqual(bad.status_code, 400)


class RunnerThreadTest(unittest.TestCase):
    def test_the_runner_calls_the_scheduled_run_until_stopped_and_survives_a_failure(self) -> None:
        import threading

        from finsync.api.server import start_llm_runner

        runs = threading.Event()

        class Service:
            calls = 0

            def run_due_llm(self) -> int:
                Service.calls += 1
                if Service.calls == 1:
                    raise RuntimeError("provider down")  # logged, retried at the next interval
                runs.set()
                return 0

        stop = start_llm_runner(Service(), 0.01)  # type: ignore[arg-type]
        self.assertTrue(runs.wait(5))
        stop.set()


if __name__ == "__main__":
    unittest.main()
