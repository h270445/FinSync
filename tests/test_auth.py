from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from finsync.api import create_app
from finsync.api.tokens import main as tokens_cli
from finsync.core import AuthenticationError, TokenService
from finsync.core.auth import hash_token
from finsync.storage import FinSyncStorage

NOTIFICATION = "CARD PURCHASE -4500 HUF at Tesco on 2026-09-05 16:42"
MANUAL = {"amount": "-4500", "currency": "HUF", "description": "Weekly shop", "happened_at": "2026-09-05"}

# Every route of finsync/api/server.py. A new route must be added here, so it gets the checks below;
# test_every_route_is_listed fails otherwise.
ENDPOINTS = (
    ("POST", "/v1/notifications/ingest"),
    ("POST", "/v1/transactions"),
    ("POST", "/v1/transactions/bulk"),
    ("GET", "/v1/transactions"),
    ("GET", "/v1/events"),
    ("GET", "/v1/events/{event}/decisions"),
    ("GET", "/v1/matches/review"),
    ("POST", "/v1/matches/{decision}/confirm"),
    ("POST", "/v1/matches/{decision}/reject"),
    ("POST", "/v1/events/{event}/split"),
)


class TokenServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.db")
        self.storage = FinSyncStorage(self.db_path)
        self.storage.add_group_membership("user-a", "group-1")
        self.tokens = TokenService(self.storage)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_a_token_resolves_to_its_member_and_group(self) -> None:
        token, record = self.tokens.create("user-a", "group-1", "phone")
        self.assertTrue(token.startswith("fs_"))
        self.assertEqual(record.prefix, token[:8])
        self.assertIsNone(record.last_used_at)
        principal = self.tokens.authenticate(f"Bearer {token}")
        self.assertEqual((principal.user_id, principal.group_id, principal.token_id), ("user-a", "group-1", record.id))
        self.assertIsNotNone(self.tokens.list("user-a")[0].last_used_at)

    def test_only_the_hash_is_stored(self) -> None:
        token, _ = self.tokens.create("user-a", "group-1", "phone")
        connection = sqlite3.connect(self.db_path)
        try:
            dump = "\n".join(connection.iterdump())
        finally:
            connection.close()
        self.assertNotIn(token, dump)
        self.assertNotIn(token[8:], dump)
        self.assertIn(hash_token(token), dump)

    def test_tokens_are_issued_only_to_members(self) -> None:
        with self.assertRaisesRegex(ValueError, "not a member"):
            self.tokens.create("user-a", "group-2", "phone")
        with self.assertRaisesRegex(ValueError, "required"):
            self.tokens.create("user-a", "group-1", " ")

    def test_missing_malformed_unknown_and_revoked_tokens_are_rejected(self) -> None:
        token, record = self.tokens.create("user-a", "group-1", "phone")
        unknown = "fs_" + "A" * 43
        for header in (None, "", token, f"Basic {token}", "Bearer ", "Bearer fs_short", f"Bearer {unknown}"):
            with self.subTest(header=header), self.assertRaises(AuthenticationError):
                self.tokens.authenticate(header)
        self.assertTrue(self.tokens.revoke(record.id))
        self.assertFalse(self.tokens.revoke(record.id))
        with self.assertRaises(AuthenticationError):
            self.tokens.authenticate(f"Bearer {token}")

    def test_each_token_is_independent(self) -> None:
        phone, phone_record = self.tokens.create("user-a", "group-1", "phone")
        sheet, _ = self.tokens.create("user-a", "group-1", "sheet")
        self.assertNotEqual(phone, sheet)
        self.tokens.revoke(phone_record.id)
        self.assertEqual(self.tokens.authenticate(f"bearer {sheet}").user_id, "user-a")

    def test_a_version_2_database_gets_the_token_table(self) -> None:
        connection = sqlite3.connect(self.db_path)
        with connection:
            connection.execute("DROP TABLE api_tokens")
            connection.execute("DELETE FROM schema_version WHERE version = 3")
        connection.close()
        token, _ = TokenService(FinSyncStorage(self.db_path)).create("user-a", "group-1", "phone")
        self.assertEqual(self.tokens.authenticate(f"Bearer {token}").user_id, "user-a")

    def test_a_rejected_create_command_does_not_restore_membership(self) -> None:
        from contextlib import redirect_stderr
        import io

        self.storage.remove_group_membership("user-a", "group-1")
        with redirect_stderr(io.StringIO()):
            code = tokens_cli(["--db", self.db_path, "create", "--user", "user-a", "--group", "group-1", "--name", " "])
        self.assertEqual(code, 2)
        self.assertFalse(self.storage.is_user_in_group("user-a", "group-1"))
        self.assertEqual(self.tokens.list("user-a"), [])

    def test_command_line_creates_lists_and_revokes(self) -> None:
        from contextlib import redirect_stderr, redirect_stdout
        import io

        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            self.assertEqual(
                tokens_cli(["--db", self.db_path, "create", "--user", "user-b", "--group", "group-2", "--name", "laptop"]), 0
            )
        token = out.getvalue().splitlines()[1]
        self.assertEqual(self.tokens.authenticate(f"Bearer {token}").group_id, "group-2")

        out = io.StringIO()
        with redirect_stdout(out):
            tokens_cli(["--db", self.db_path, "list"])
        self.assertIn("laptop", out.getvalue())
        self.assertNotIn(token, out.getvalue())

        token_id = self.tokens.list("user-b")[0].id
        with redirect_stdout(io.StringIO()):
            self.assertEqual(tokens_cli(["--db", self.db_path, "revoke", str(token_id)]), 0)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(tokens_cli(["--db", self.db_path, "revoke", str(token_id)]), 1)
        with self.assertRaises(AuthenticationError):
            self.tokens.authenticate(f"Bearer {token}")


class AuthApiTest(unittest.TestCase):
    """Group 1 (members A and B) has a matched purchase waiting for review; member C is in group 2 only."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        for user, group in (("user-a", "group-1"), ("user-b", "group-1"), ("user-c", "group-2")):
            self.storage.add_group_membership(user, group)
        self.tokens = TokenService(self.storage)
        self.token_a, self.record_a = self.tokens.create("user-a", "group-1", "phone")
        self.token_b, _ = self.tokens.create("user-b", "group-1", "phone")
        self.token_c, _ = self.tokens.create("user-c", "group-2", "phone")

        self.app = create_app(self.storage)
        self.client = TestClient(self.app)

        self._call("POST", "/v1/notifications/ingest", self.token_a, {"message": NOTIFICATION})
        self._call("POST", "/v1/transactions", self.token_b, MANUAL)
        [review] = self._call("GET", "/v1/matches/review", self.token_a)[1]["reviews"]
        self.decision_id = review["decision_id"]
        self.event_id = review["candidate_event"]["id"]
        self.group_1_record = review["candidate_event"]["transactions"][0]["id"]

    def tearDown(self) -> None:
        self.client.close()
        self.tempdir.cleanup()

    def _call(self, method: str, path: str, token: str | None, body: dict | None = None, headers: dict | None = None):
        sent = {"Content-Type": "application/json", **(headers or {})}
        if token is not None:
            sent["Authorization"] = f"Bearer {token}"
        response = self.client.request(method, path, content=json.dumps(body or {}), headers=sent)
        return response.status_code, response.json(), response.headers.get("WWW-Authenticate")

    def test_every_route_is_listed(self) -> None:
        routes = {
            (method, route.path.replace("{decision_id}", "{decision}").replace("{event_id}", "{event}"))
            for route in self.app.routes
            if isinstance(route, APIRoute)
            for method in route.methods
        }
        self.assertEqual(routes, set(ENDPOINTS))

    def _endpoints(self):
        for method, path in ENDPOINTS:
            yield method, path.format(decision=self.decision_id, event=self.event_id)

    def _body(self, path: str) -> dict:
        if path.endswith("/ingest"):
            return {"message": NOTIFICATION}
        if path.endswith("/bulk"):
            return {"rows": [MANUAL]}
        if path.endswith("/split"):
            return {"transaction_id": self.group_1_record}
        return MANUAL

    def _group_1_state(self):
        return (
            self.storage.list_transactions("group-1"),
            self.storage.list_events("group-1"),
            self.storage.list_decisions("group-1"),
        )

    def test_every_endpoint_requires_a_valid_token(self) -> None:
        unknown = "fs_" + "A" * 43
        before = self._group_1_state()
        for method, path in self._endpoints():
            for token, headers in (
                (None, {}),
                (None, {"X-User-Id": "user-a", "X-Group-Id": "group-1"}),
                (None, {"Authorization": f"Basic {self.token_a}"}),
                (unknown, {}),
            ):
                with self.subTest(method=method, path=path, headers=headers, token=token):
                    status, body, challenge = self._call(method, path, token, self._body(path), headers)
                    self.assertEqual(status, 401)
                    self.assertEqual(challenge, 'Bearer realm="finsync"')
                    self.assertIn("token", body["error"])
        self.assertEqual(self._group_1_state(), before)

    def test_a_revoked_token_is_rejected_everywhere(self) -> None:
        self.tokens.revoke(self.record_a.id)
        for method, path in self._endpoints():
            with self.subTest(method=method, path=path):
                self.assertEqual(self._call(method, path, self.token_a, self._body(path))[0], 401)
        self.assertEqual(self._call("GET", "/v1/events", self.token_b)[0], 200)

    def test_a_token_stops_working_when_its_member_leaves_the_group(self) -> None:
        self.storage.remove_group_membership("user-a", "group-1")
        before = self._group_1_state()
        for method, path in self._endpoints():
            with self.subTest(method=method, path=path):
                self.assertEqual(self._call(method, path, self.token_a, self._body(path))[0], 403)
        self.assertEqual(self._group_1_state(), before)

    def test_another_groups_member_cannot_read_or_change_group_1(self) -> None:
        group_1_ids = {tx.id for tx in self.storage.list_transactions("group-1")}
        before = self._group_1_state()
        spoofed = {"X-User-Id": "user-a", "X-Group-Id": "group-1"}
        for method, path in self._endpoints():
            with self.subTest(method=method, path=path):
                status, body, _ = self._call(method, path, self.token_c, self._body(path), spoofed)
                if (method == "POST" and path.startswith("/v1/matches/")) or path.startswith("/v1/events/"):
                    # Group 1's decision and event ids do not exist in group 2.
                    self.assertEqual(status, 404)
                elif method == "GET":
                    self.assertEqual(status, 200)
                    listed = json.dumps(body)
                    self.assertNotIn("group-1", listed)
                    self.assertNotIn("user-a", listed)
                else:
                    # Writes go to the token's group, whatever the headers say, and never join a group 1 event.
                    self.assertEqual(status, 201)
                    results = body.get("results", [body])
                    for result in results:
                        self.assertNotIn(result["transaction_id"], group_1_ids)
                        self.assertNotIn(result["event_id"], {e.id for e in before[1]})
        self.assertEqual(self._group_1_state(), before)
        self.assertEqual({tx.group_id for tx in self.storage.list_transactions("group-2")}, {"group-2"})
        self.assertEqual({tx.user_id for tx in self.storage.list_transactions("group-2")}, {"user-c"})

    def test_a_member_acts_as_the_tokens_user_whatever_the_headers_say(self) -> None:
        status, body, _ = self._call(
            "POST", "/v1/transactions", self.token_b, MANUAL, {"X-User-Id": "user-a", "X-Group-Id": "group-2"}
        )
        self.assertEqual(status, 201)
        stored = next(tx for tx in self.storage.list_transactions("group-1") if tx.id == body["transaction_id"])
        self.assertEqual(stored.user_id, "user-b")

    def test_a_member_of_the_group_can_use_every_endpoint(self) -> None:
        for method, path in self._endpoints():
            if path.endswith("/reject"):
                continue  # Confirm answers the same decision first; reject is covered by the review tests.
            with self.subTest(method=method, path=path):
                status = self._call(method, path, self.token_a, self._body(path))[0]
                self.assertIn(status, (200, 201))


if __name__ == "__main__":
    unittest.main()
