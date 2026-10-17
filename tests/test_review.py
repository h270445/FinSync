from __future__ import annotations

import http.client
from http.server import ThreadingHTTPServer
import json
import os
import tempfile
import threading
import unittest

from finsync.core import AuthorizationError, ConflictError, FinSyncService, NotFoundError
from finsync.storage import FinSyncStorage

NOTIFICATION = "CARD PURCHASE -4500 HUF at Tesco on 2026-09-05 16:42"


class ReviewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        self.service = FinSyncService(self.storage)
        self.storage.add_group_membership("user-1", "group-1")
        self.storage.add_group_membership("user-3", "group-2")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _manual(self, **overrides: object):
        row = {
            "amount": "-4500",
            "currency": "HUF",
            "description": "Weekly shop",
            "merchant": "Tesco",
            "happened_at": "2026-09-05T16:50:00+00:00",
        }
        row.update(overrides)
        return self.service.create_manual_transaction("user-1", "group-1", row)

    def _uncertain_pair(self):
        """A notification and a date-only manual entry that only shares the description: needs_review."""
        notification = self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        manual = self._manual(happened_at="2026-09-05", merchant=None, description="Tesco weekly shop")
        self.assertEqual(manual.match_outcome, "needs_review")
        [review] = self.service.list_open_reviews("user-1", "group-1")
        return notification, manual, review

    def _events(self):
        return self.service.list_group_events("user-1", "group-1")

    def test_review_list_shows_record_candidate_and_reason(self) -> None:
        notification, manual, review = self._uncertain_pair()
        self.assertEqual(review.transaction.id, manual.transaction_id)
        self.assertEqual(review.candidate_event.id, notification.event_id)
        self.assertEqual(set(review.features or {}) >= {"a", "t", "m", "score"}, True)

    def test_confirm_links_the_record_and_clears_the_flag(self) -> None:
        notification, manual, review = self._uncertain_pair()
        result = self.service.confirm_match("user-1", "group-1", review.decision_id)

        self.assertEqual(result.event_id, notification.event_id)
        [event] = self._events()
        self.assertEqual(len(event.transactions), 2)
        self.assertEqual(event.review_state, "clear")
        self.assertEqual(self.service.list_open_reviews("user-1", "group-1"), [])
        confirmed = self.storage.list_decisions("group-1")[-1]
        self.assertEqual(
            (confirmed["outcome"], confirmed["decided_by"], confirmed["supersedes_id"]),
            ("confirmed", "user-1", review.decision_id),
        )
        with self.assertRaises(ConflictError):
            self.service.confirm_match("user-1", "group-1", review.decision_id)

    def test_reject_keeps_two_events_and_is_not_proposed_again(self) -> None:
        notification = self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        manual = self._manual(
            happened_at="2026-09-05", merchant=None, description="Tesco weekly shop", source_ref="sheet-row-3"
        )
        [review] = self.service.list_open_reviews("user-1", "group-1")
        self.service.reject_match("user-1", "group-1", review.decision_id)

        events = self._events()
        self.assertEqual(len(events), 2)
        self.assertEqual({event.review_state for event in events}, {"clear"})
        # The same sheet row sent again stays with its own record, not with the rejected event.
        again = self._manual(
            happened_at="2026-09-05", merchant=None, description="Tesco weekly shop", source_ref="sheet-row-3"
        )
        self.assertEqual(again.match_outcome, "exact_duplicate")
        self.assertEqual(again.event_id, manual.event_id)
        self.assertNotEqual(again.event_id, notification.event_id)
        self.assertEqual(self.service.list_open_reviews("user-1", "group-1"), [])

    def test_confirming_an_identical_row_makes_it_a_re_delivery(self) -> None:
        first = self._manual()
        second = self._manual()
        [review] = self.service.list_open_reviews("user-1", "group-1")
        self.service.confirm_match("user-1", "group-1", review.decision_id)

        [event] = self._events()
        moved = next(tx for tx in event.transactions if tx.id == second.transaction_id)
        self.assertEqual(moved.duplicate_of_id, first.transaction_id)

    def test_split_undoes_a_wrong_link(self) -> None:
        notification = self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        repeated = self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        manual = self._manual()
        self.assertEqual(manual.match_outcome, "auto_linked")

        result = self.service.split_event("user-1", "group-1", notification.event_id, notification.transaction_id)

        events = {event.id: event for event in self._events()}
        self.assertEqual(len(events), 2)
        moved_ids = {tx.id for tx in events[result.event_id].transactions}
        self.assertEqual(moved_ids, {notification.transaction_id, repeated.transaction_id})
        self.assertEqual([tx.id for tx in events[manual.event_id].transactions], [manual.transaction_id])
        # The remaining event now shows the manual record's values.
        self.assertEqual(events[manual.event_id].primary_transaction_id, manual.transaction_id)
        split = self.storage.list_decisions("group-1")[-1]
        self.assertEqual((split["outcome"], split["decided_by"]), ("split", "user-1"))

    def test_split_rejects_invalid_targets(self) -> None:
        notification = self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        repeated = self.service.ingest_notification("user-1", "group-1", NOTIFICATION)
        with self.assertRaises(ConflictError):
            self.service.split_event("user-1", "group-1", notification.event_id, notification.transaction_id)
        self._manual()
        with self.assertRaisesRegex(ValueError, "re-delivery"):
            self.service.split_event("user-1", "group-1", notification.event_id, repeated.transaction_id)
        with self.assertRaises(NotFoundError):
            self.service.split_event("user-1", "group-1", notification.event_id + 99, notification.transaction_id)

    def test_other_group_cannot_see_or_decide(self) -> None:
        notification, _, review = self._uncertain_pair()
        self.assertEqual(self.service.list_open_reviews("user-3", "group-2"), [])
        for action in (self.service.confirm_match, self.service.reject_match):
            with self.subTest(action=action.__name__):
                with self.assertRaises(NotFoundError):
                    action("user-3", "group-2", review.decision_id)
                with self.assertRaises(AuthorizationError):
                    action("user-3", "group-1", review.decision_id)
        with self.assertRaises(NotFoundError):
            self.service.split_event("user-3", "group-2", notification.event_id, notification.transaction_id)
        self.assertEqual(len(self.service.list_open_reviews("user-1", "group-1")), 1)


class ReviewApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        self.service = FinSyncService(storage)
        storage.add_group_membership("user-1", "group-1")
        storage.add_group_membership("user-3", "group-2")

        # finsync.api opens a default database at import time; keep it inside the tempdir.
        previous_cwd = os.getcwd()
        os.chdir(self.tempdir.name)
        try:
            from finsync.api import FinSyncRequestHandler
        finally:
            os.chdir(previous_cwd)
        handler = type("Handler", (FinSyncRequestHandler,), {"service": self.service})
        handler.log_message = lambda *args: None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.tempdir.cleanup()

    def _call(self, method: str, path: str, body: dict | None = None, group: str = "group-1", user: str = "user-1"):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1])
        connection.request(
            method,
            path,
            body=json.dumps(body or {}),
            headers={"X-User-Id": user, "X-Group-Id": group, "Content-Type": "application/json"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read())
        connection.close()
        return response.status, payload

    def test_review_flow_over_http(self) -> None:
        self._call("POST", "/v1/notifications/ingest", {"message": NOTIFICATION})
        self._call(
            "POST",
            "/v1/transactions",
            {"amount": "-4500", "currency": "HUF", "description": "Tesco weekly shop", "happened_at": "2026-09-05"},
        )
        status, body = self._call("GET", "/v1/matches/review")
        self.assertEqual(status, 200)
        decision_id = body["reviews"][0]["decision_id"]

        self.assertEqual(self._call("POST", f"/v1/matches/{decision_id}/confirm", group="group-2", user="user-3")[0], 404)
        status, body = self._call("POST", f"/v1/matches/{decision_id}/confirm")
        self.assertEqual((status, body["match_outcome"]), (200, "confirmed"))
        self.assertEqual(self._call("POST", f"/v1/matches/{decision_id}/reject")[0], 409)

        event_id = body["event_id"]
        status, body = self._call("POST", f"/v1/events/{event_id}/split", {"transaction_id": "1"})
        self.assertEqual(status, 400)
        status, body = self._call("POST", f"/v1/events/{event_id}/split", {"transaction_id": 1})
        self.assertEqual((status, body["match_outcome"]), (200, "split"))
        self.assertEqual(len(self._call("GET", "/v1/events")[1]["events"]), 2)


if __name__ == "__main__":
    unittest.main()
