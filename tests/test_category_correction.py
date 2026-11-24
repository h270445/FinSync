"""Category correction: a member confirms or changes an event's category, marks it mixed, splits it into
category lines or marks it as a transfer ([categorization design](../docs/design/categorization.md#mixed-baskets)).

Synthetic members (anna, balint, user-c) and made-up shops only.
"""

from __future__ import annotations

from decimal import Decimal
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from finsync.api import create_app
from finsync.core import AuthorizationError, ConflictError, FinSyncService, NotFoundError, TokenService
from finsync.storage import FinSyncStorage

# "Minta Kozert" is not in the built-in dictionary (a clear merchant nobody knows yet); Tesco is on its
# mixed-assortment list; BKK is a clear merchant of the dictionary.
NOTIFICATION = "CARD PURCHASE -4500 HUF at Tesco on 2026-09-05 16:42"


class CategoryCorrectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        self.service = FinSyncService(self.storage)
        for user, group in (("anna", "group-1"), ("balint", "group-1"), ("user-c", "group-2")):
            self.storage.add_group_membership(user, group)  # anna is group 1's admin, balint a member

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _manual(self, merchant: str | None = "Minta Kozert", amount: str = "-12000", day: str = "2026-11-10",
                description: str = "Bevasarlas", user: str = "anna"):
        result = self.service.create_manual_transaction(user, "group-1", {
            "amount": amount, "currency": "HUF", "description": description, "merchant": merchant,
            "happened_at": f"{day}T10:00",
        })
        return result.event_id

    def _event(self, event_id: int):
        return next(e for e in self.service.list_group_events("anna", "group-1") if e.id == event_id)

    def _state(self):
        return (
            self.storage.list_events("group-1"),
            self.storage.list_transactions("group-1"),
            self.storage.list_merchant_categories("group-1"),
            self.storage.list_category_changes("group-1", 1),
        )

    # Where a category came from

    def test_every_new_event_says_where_its_category_came_from(self) -> None:
        tesco = self._event(self._manual("Tesco"))
        bkk = self._event(self._manual("BKK", day="2026-11-11"))
        unknown = self._event(self._manual(day="2026-11-12"))
        self.assertEqual((tesco.category, tesco.category_source, tesco.category_confidence), ("groceries", "dictionary", "low"))
        self.assertEqual((bkk.category, bkk.category_source, bkk.category_confidence), ("transport", "dictionary", "high"))
        self.assertEqual((unknown.category, unknown.category_source), ("other", "none"))
        self.assertEqual(tesco.transactions[0].category_source, "dictionary")

    # Confirm or change

    def test_a_member_changes_the_category_and_it_is_logged(self) -> None:
        event_id = self._manual("Tesco")
        result = self.service.set_event_category("balint", "group-1", event_id, "clothing")
        self.assertEqual(
            (result.event.category, result.event.category_source, result.event.category_confidence),
            ("clothing", "user", "high"),
        )
        self.assertIsNone(result.merchant_rule_outcome)
        [change] = self.service.list_category_changes("anna", "group-1", event_id)
        self.assertEqual((change["kind"], change["changed_by"]), ("category", "balint"))
        self.assertEqual(change["old_value"], {"category": "groceries", "source": "dictionary", "confidence": "low"})
        self.assertEqual(change["new_value"]["category"], "clothing")
        # Confirming the suggestion as it is settles it too.
        confirmed = self.service.set_event_category("anna", "group-1", self._manual("Spar", day="2026-11-11"), "groceries")
        self.assertEqual((confirmed.event.category_source, confirmed.event.category_confidence), ("user", "high"))

    def test_a_members_category_survives_a_record_linked_later(self) -> None:
        notification = self.service.ingest_notification("anna", "group-1", NOTIFICATION)
        self.service.set_event_category("anna", "group-1", notification.event_id, "clothing")
        manual = self.service.create_manual_transaction("anna", "group-1", {
            "amount": "-4500", "currency": "HUF", "description": "Weekly shop", "merchant": "Tesco",
            "happened_at": "2026-09-05T16:50:00+00:00",
        })
        self.assertEqual(manual.event_id, notification.event_id)  # linked automatically
        event = self._event(notification.event_id)
        self.assertEqual((len(event.transactions), event.category, event.category_source), (2, "clothing", "user"))

    def test_refused_changes_leave_everything_unchanged(self) -> None:
        event_id = self._manual("Tesco")
        before = self._state()
        with self.assertRaisesRegex(ValueError, "category must be one of"):
            self.service.set_event_category("anna", "group-1", event_id, "food")
        with self.assertRaisesRegex(ValueError, "cannot be remembered"):
            self.service.set_event_category("anna", "group-1", event_id, "clothing", remember=True)  # Tesco is mixed
        with self.assertRaises(NotFoundError):
            self.service.set_event_category("user-c", "group-2", event_id, "clothing")  # another group's event
        with self.assertRaises(AuthorizationError):
            self.service.set_event_category("user-c", "group-1", event_id, "clothing")  # not a member
        self.assertEqual(self._state(), before)

    # Merchant memory

    def test_remember_teaches_the_group_a_rule_for_a_clear_merchant(self) -> None:
        first = self._manual()
        self.assertEqual(self._event(first).category, "other")
        learned = self.service.set_event_category("balint", "group-1", first, "groceries", remember=True)
        self.assertEqual(learned.merchant_rule_outcome, "created")
        self.assertEqual((learned.merchant_rule.merchant_key, learned.merchant_rule.category), ("minta kozert", "groceries"))
        # The next purchase there is categorized by the rule.
        second = self._event(self._manual(day="2026-11-12"))
        self.assertEqual((second.category, second.category_source, second.category_confidence), ("groceries", "merchant_rule", "high"))
        again = self.service.set_event_category("anna", "group-1", second.id, "groceries", remember=True)
        self.assertEqual((again.merchant_rule_outcome, again.merchant_rule.times_confirmed), ("confirmed", 2))

    def test_only_an_admin_changes_an_existing_rule_through_a_correction(self) -> None:
        first = self._manual()
        self.service.set_event_category("anna", "group-1", first, "groceries", remember=True)
        second = self._manual(day="2026-11-12")
        kept = self.service.set_event_category("balint", "group-1", second, "household", remember=True)
        self.assertEqual((kept.merchant_rule_outcome, kept.merchant_rule.category), ("kept", "groceries"))
        self.assertEqual(kept.event.category, "household")  # the correction itself stays on the event
        updated = self.service.set_event_category("anna", "group-1", second, "household", remember=True)
        self.assertEqual((updated.merchant_rule_outcome, updated.merchant_rule.category), ("updated", "household"))

    def test_no_rule_is_learned_for_a_mixed_or_split_event_or_a_mixed_assortment_merchant(self) -> None:
        tesco = self._event(self._manual("Tesco"))
        self.assertIsNone(self._offer(tesco))
        event_id = self._manual()
        self.assertEqual(self._offer(self._event(event_id)), "Minta Kozert")
        self.service.set_event_mixed("anna", "group-1", event_id, True)
        self.assertIsNone(self._offer(self._event(event_id)))
        with self.assertRaisesRegex(ValueError, "cannot be remembered"):
            self.service.set_event_category("anna", "group-1", event_id, "groceries", remember=True)
        self.assertEqual(self.storage.list_merchant_categories("group-1"), [])

    @staticmethod
    def _offer(event):
        from finsync.core import merchant_rule_offer

        return merchant_rule_offer(event)

    # Mixed and category lines

    def test_mixed_flag_is_counted_on_the_overview(self) -> None:
        event_id = self._manual("Tesco")
        event = self.service.set_event_mixed("balint", "group-1", event_id, True)
        self.assertTrue(event.mixed)
        self.service.set_event_mixed("balint", "group-1", event_id, True)  # no change, not logged again
        [total] = self.service.overview("anna", "group-1", "2026-11").totals
        self.assertEqual((total.mixed_count, total.mixed_amount), (1, Decimal("12000")))
        self.assertEqual((total.uncertain_count, total.uncertain_amount), (1, Decimal("12000")))
        self.assertEqual([c["kind"] for c in self.service.list_category_changes("anna", "group-1", event_id)], ["mixed"])

    def test_category_lines_split_the_amount_and_the_overview_follows(self) -> None:
        event_id = self._manual("Tesco")
        event = self.service.set_category_lines("balint", "group-1", event_id, [
            {"category": "groceries", "amount": "-9000"}, {"category": "clothing", "amount": "-3000"},
        ])
        self.assertEqual([(l.category, l.amount) for l in event.lines], [("groceries", Decimal("-9000")), ("clothing", Decimal("-3000"))])
        self.assertEqual((event.category, event.category_source), ("groceries", "user"))  # the largest line
        overview = self.service.overview("anna", "group-1", "2026-11")
        self.assertEqual(
            sorted((c.key, c.expense, c.event_count) for c in overview.categories),
            [("clothing", Decimal("3000"), 1), ("groceries", Decimal("9000"), 1)],
        )
        self.assertEqual([(t.expense, t.event_count, t.uncertain_count) for t in overview.totals], [(Decimal("12000"), 1, 0)])
        with self.assertRaisesRegex(ConflictError, "category lines"):
            self.service.set_event_category("anna", "group-1", event_id, "clothing")
        # Saving the lines again replaces them as one change; an empty list removes the split.
        self.service.set_category_lines("anna", "group-1", event_id, [
            {"category": "clothing", "amount": "-6000"}, {"category": "household", "amount": "-6000"},
        ])
        cleared = self.service.set_category_lines("anna", "group-1", event_id, [])
        self.assertEqual((cleared.lines, cleared.category), ((), "clothing"))  # the first of the equal lines
        changes = self.service.list_category_changes("anna", "group-1", event_id)
        self.assertEqual([c["kind"] for c in changes], ["lines", "lines", "lines"])
        self.assertEqual(changes[2]["old_value"], [{"category": "clothing", "amount": "-6000"}, {"category": "household", "amount": "-6000"}])
        self.assertEqual(changes[2]["new_value"], [])

    def test_lines_must_add_up_with_the_events_sign(self) -> None:
        event_id = self._manual("Tesco")
        before = self._state()
        cases = {
            "add up to": [{"category": "groceries", "amount": "-9000"}, {"category": "clothing", "amount": "-2000"}],
            "sign": [{"category": "groceries", "amount": "-15000"}, {"category": "clothing", "amount": "3000"}],
            "already a line": [{"category": "groceries", "amount": "-6000"}, {"category": "groceries", "amount": "-6000"}],
            "at least two": [{"category": "groceries", "amount": "-12000"}],
            "category must be one of": [{"category": "food", "amount": "-6000"}, {"category": "groceries", "amount": "-6000"}],
            "invalid amount": [{"category": "clothing", "amount": "sok"}, {"category": "groceries", "amount": "-6000"}],
            "non-zero": [{"category": "clothing", "amount": "0"}, {"category": "groceries", "amount": "-12000"}],
        }
        for reason, lines in cases.items():
            with self.subTest(reason), self.assertRaisesRegex(ValueError, reason):
                self.service.set_category_lines("anna", "group-1", event_id, lines)
        self.assertEqual(self._state(), before)

    def test_lines_stay_on_the_original_event_when_a_record_is_split_off(self) -> None:
        notification = self.service.ingest_notification("anna", "group-1", NOTIFICATION)
        self.service.create_manual_transaction("anna", "group-1", {
            "amount": "-4500", "currency": "HUF", "description": "Weekly shop", "merchant": "Tesco",
            "happened_at": "2026-09-05T16:50:00+00:00",
        })
        self.service.set_category_lines("anna", "group-1", notification.event_id, [
            {"category": "groceries", "amount": "-4000"}, {"category": "clothing", "amount": "-500"},
        ])
        manual_record = next(tx for tx in self._event(notification.event_id).transactions if tx.source == "manual")
        split = self.service.split_event("anna", "group-1", notification.event_id, manual_record.id)
        self.assertEqual(len(self._event(notification.event_id).lines), 2)
        new = self._event(split.event_id)
        self.assertEqual((new.lines, new.mixed, new.category_source), ((), False, "dictionary"))

    # Transfers

    def test_marking_a_transfer_leaves_it_out_of_the_totals_and_undoing_restores_it(self) -> None:
        event_id = self._manual("Minta Anna", description="Atutalas")
        self.service.set_event_mixed("anna", "group-1", event_id, True)
        marked = self.service.set_event_transfer("balint", "group-1", event_id, True)
        self.assertEqual((marked.direction, marked.category, marked.category_source, marked.mixed), ("transfer", "transfer", "user", False))
        self.assertEqual({(tx.direction, tx.category) for tx in marked.transactions}, {("transfer", "transfer")})
        overview = self.service.overview("anna", "group-1", "2026-11")
        self.assertEqual((overview.transfer_count, overview.totals), (1, []))
        with self.assertRaisesRegex(ConflictError, "transfer"):
            self.service.set_event_category("anna", "group-1", event_id, "groceries")
        with self.assertRaisesRegex(ConflictError, "transfer"):
            self.service.set_event_mixed("anna", "group-1", event_id, True)

        undone = self.service.set_event_transfer("balint", "group-1", event_id, False)
        self.assertEqual((undone.direction, undone.category, undone.category_source), ("expense", "other", "none"))
        self.assertEqual({tx.direction for tx in undone.transactions}, {"expense"})
        kinds = [c["kind"] for c in self.service.list_category_changes("anna", "group-1", event_id)]
        self.assertEqual(kinds, ["mixed", "transfer", "transfer"])

    def test_an_event_split_into_lines_is_not_marked_as_a_transfer(self) -> None:
        event_id = self._manual("Tesco")
        self.service.set_category_lines("anna", "group-1", event_id, [
            {"category": "groceries", "amount": "-6000"}, {"category": "household", "amount": "-6000"},
        ])
        with self.assertRaisesRegex(ConflictError, "lines"):
            self.service.set_event_transfer("anna", "group-1", event_id, True)

    # HTTP

    def test_corrections_over_http(self) -> None:
        event_id = self._manual()
        token, _ = TokenService(self.storage).create("balint", "group-1", "test")
        other, _ = TokenService(self.storage).create("user-c", "group-2", "test")
        headers = {"Authorization": f"Bearer {token}"}
        with TestClient(create_app(self.storage)) as client:
            listed = client.get("/v1/events", headers=headers).json()["events"][0]
            self.assertEqual(
                {k: listed[k] for k in ("category", "category_source", "uncertain", "mixed", "lines", "remember_merchant")},
                {"category": "other", "category_source": "none", "uncertain": True, "mixed": False, "lines": [],
                 "remember_merchant": "Minta Kozert"},
            )
            corrected = client.put(f"/v1/events/{event_id}/category", json={"category": "groceries", "remember": True}, headers=headers)
            self.assertEqual(corrected.status_code, 200)
            body = corrected.json()
            self.assertEqual((body["event"]["category"], body["event"]["uncertain"]), ("groceries", False))
            self.assertEqual((body["merchant_rule_outcome"], body["merchant_rule"]["merchant_key"]), ("created", "minta kozert"))
            lines = client.put(f"/v1/events/{event_id}/category-lines", headers=headers, json={"lines": [
                {"category": "groceries", "amount": "-10000"}, {"category": "household", "amount": "-2000"},
            ]})
            self.assertEqual((lines.status_code, lines.json()["lines_match_amount"]), (200, True))
            self.assertIsNone(lines.json()["remember_merchant"])
            self.assertEqual(client.put(f"/v1/events/{event_id}/transfer", json={"transfer": True}, headers=headers).status_code, 409)
            self.assertEqual(client.put(f"/v1/events/{event_id}/category", json={"category": "x"}, headers=headers).status_code, 400)
            bad = client.put(f"/v1/events/{event_id}/category-lines", json={"lines": [{"category": "groceries", "amount": "-1"}] * 2}, headers=headers)
            self.assertEqual(bad.status_code, 400)
            self.assertEqual(client.put(f"/v1/events/{event_id}/mixed", json={"mixed": True}, headers=headers).status_code, 200)
            changes = client.get(f"/v1/events/{event_id}/category-changes", headers=headers).json()["changes"]
            self.assertEqual([c["kind"] for c in changes], ["category", "lines", "mixed"])
            self.assertEqual(changes[0]["changed_by"], "balint")
            foreign = {"Authorization": f"Bearer {other}"}
            for method, path, body in (
                ("PUT", "category", {"category": "groceries"}), ("PUT", "mixed", {"mixed": False}),
                ("PUT", "transfer", {"transfer": True}), ("GET", "category-changes", None),
            ):
                with self.subTest(path=path):
                    response = client.request(method, f"/v1/events/{event_id}/{path}", json=body, headers=foreign)
                    self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
