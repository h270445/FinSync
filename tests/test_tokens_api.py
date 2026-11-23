"""W8 actions that widen access, only from a web session (least privilege, ADR 0012).

Token management (GET/POST /v1/tokens, POST /v1/tokens/{id}/revoke) and role changes
(PUT /v1/members/{id}/role): an API token gets 403 for them, even an admin's.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from finsync.api import create_app
from finsync.api.server import CSRF_HEADER
from finsync.core import SessionService, TokenService
from finsync.core import sessions as sessions_module
from finsync.storage import FinSyncStorage

PASSWORD_A = "anna-jelszava-1"
PASSWORD_C = "cecil-jelszava-1"


class TokensApiTest(unittest.TestCase):
    """A and B are in group 1, C in group 2; A and C have passwords, B and C have a phone token."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        for user, group in (("user-a", "group-1"), ("user-b", "group-1"), ("user-c", "group-2")):
            self.storage.add_group_membership(user, group)
        self.storage.set_member_email("user-a", "anna@example.org")
        with mock.patch.multiple(sessions_module, _SCRYPT_N=2**10, _SCRYPT_P=1):
            sessions = SessionService(self.storage)
            sessions.set_password("user-a", PASSWORD_A)
            sessions.set_password("user-c", PASSWORD_C)
        self.tokens = TokenService(self.storage)
        self.token_b, self.record_b = self.tokens.create("user-b", "group-1", "Balint phone")
        self.token_c, self.record_c = self.tokens.create("user-c", "group-2", "Cecil phone")
        self.client = TestClient(create_app(self.storage), base_url="https://testserver")

    def tearDown(self) -> None:
        self.client.close()
        self.tempdir.cleanup()

    def _sign_in(self, user: str = "user-a", password: str = PASSWORD_A) -> dict[str, str]:
        # The cheap scrypt cost of setUp is stored with the hash, so signing in is fast too.
        response = self.client.post("/v1/session", json={"login": user, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return {CSRF_HEADER: response.json()["csrf_token"]}

    def test_a_member_creates_lists_and_revokes_their_own_token(self) -> None:
        csrf = self._sign_in()
        self.assertEqual(self.client.get("/v1/tokens").json(), {"tokens": []})

        created = self.client.post("/v1/tokens", json={"name": " Anna phone "}, headers=csrf)
        self.assertEqual(created.status_code, 201)
        body = created.json()
        self.assertTrue(body["token"].startswith(body["record"]["prefix"]))
        self.assertEqual((body["record"]["name"], body["record"]["revoked_at"]), ("Anna phone", None))

        # The new token works for the Android app, and the list never shows it again.
        used = self.client.get("/v1/events", headers={"Authorization": f"Bearer {body['token']}"})
        self.assertEqual(used.status_code, 200)
        listed = self.client.get("/v1/tokens").json()["tokens"]
        self.assertEqual([t["id"] for t in listed], [body["record"]["id"]])
        self.assertIsNotNone(listed[0]["last_used_at"])
        self.assertNotIn(body["token"], str(listed))

        revoked = self.client.post(f"/v1/tokens/{body['record']['id']}/revoke", headers=csrf)
        self.assertEqual(revoked.status_code, 200)
        self.assertIsNotNone(revoked.json()["revoked_at"])
        again = self.client.get("/v1/events", headers={"Authorization": f"Bearer {body['token']}"})
        self.assertEqual(again.status_code, 401)
        # Revoking twice answers the same revoked record.
        self.assertEqual(self.client.post(f"/v1/tokens/{body['record']['id']}/revoke", headers=csrf).status_code, 200)

    def test_another_members_or_groups_token_is_not_found(self) -> None:
        csrf = self._sign_in()
        self.assertEqual(self.client.get("/v1/tokens").json(), {"tokens": []})
        for token_id in (self.record_b.id, self.record_c.id, 9999):
            with self.subTest(token_id=token_id):
                response = self.client.post(f"/v1/tokens/{token_id}/revoke", headers=csrf)
                self.assertEqual(response.status_code, 404)
        self.assertTrue(all(t.revoked_at is None for t in self.tokens.list()))

    def test_api_tokens_cannot_manage_tokens(self) -> None:
        bearer = {"Authorization": f"Bearer {self.token_b}"}
        for method, path, body in (
            ("GET", "/v1/tokens", None),
            ("POST", "/v1/tokens", {"name": "second phone"}),
            ("POST", f"/v1/tokens/{self.record_b.id}/revoke", None),
        ):
            with self.subTest(method=method, path=path):
                response = self.client.request(method, path, json=body, headers=bearer)
                self.assertEqual(response.status_code, 403)
                self.assertIn("web app", response.json()["error"])
        self.assertEqual(len(self.tokens.list()), 2)
        self.assertIsNone(self.tokens.list("user-b")[0].revoked_at)

    def test_writes_need_the_csrf_token_and_a_name(self) -> None:
        csrf = self._sign_in()
        self.assertEqual(self.client.post("/v1/tokens", json={"name": "phone"}).status_code, 403)
        for body in ({"name": "  "}, {"name": "x" * 81}, {}):
            with self.subTest(body=body):
                response = self.client.post("/v1/tokens", json=body, headers=csrf)
                self.assertEqual(response.status_code, 400)
                self.assertIn("name", response.json()["error"])
        self.assertEqual(self.tokens.list("user-a"), [])

    def test_unauthenticated_and_removed_members_are_refused(self) -> None:
        self.assertEqual(self.client.get("/v1/tokens").status_code, 401)
        csrf = self._sign_in()
        self.storage.remove_group_membership("user-a", "group-1")
        self.assertEqual(self.client.get("/v1/tokens").status_code, 403)
        self.assertEqual(self.client.post("/v1/tokens", json={"name": "phone"}, headers=csrf).status_code, 403)

    def test_roles_change_only_from_the_web_session(self) -> None:
        # B's phone token cannot make B an admin, even after A made B an admin once.
        bearer_b = {"Authorization": f"Bearer {self.token_b}"}
        refused = self.client.put("/v1/members/user-b/role", json={"role": "admin"}, headers=bearer_b)
        self.assertEqual(refused.status_code, 403)
        self.assertIn("web app", refused.json()["error"])

        csrf = self._sign_in()
        self.assertEqual(self.client.put("/v1/members/user-b/role", json={"role": "admin"}).status_code, 403)  # no CSRF
        promoted = self.client.put("/v1/members/user-b/role", json={"role": "admin"}, headers=csrf)
        self.assertEqual(promoted.status_code, 200)
        self.assertEqual({m["user_id"]: m["role"] for m in promoted.json()["members"]}, {"user-a": "admin", "user-b": "admin"})

        # Now an admin, B still cannot change roles with the phone token.
        demote = self.client.put("/v1/members/user-a/role", json={"role": "member"}, headers=bearer_b)
        self.assertEqual(demote.status_code, 403)
        self.assertIn("web app", demote.json()["error"])
        # Another group's member is not found from A's session.
        self.assertEqual(self.client.put("/v1/members/user-c/role", json={"role": "admin"}, headers=csrf).status_code, 404)
        self.assertEqual(
            {m: r for m, _, r in self.storage.list_group_members("group-1")}, {"user-a": "admin", "user-b": "admin"}
        )

    def test_members_list_shows_the_group_only(self) -> None:
        self._sign_in()
        members = self.client.get("/v1/members").json()["members"]
        self.assertEqual(members, [
            {"user_id": "user-a", "email": "anna@example.org", "role": "admin", "is_me": True},
            {"user_id": "user-b", "email": None, "role": "member", "is_me": False},
        ])
        # The members list also works with an API token, in the token's group.
        other = self.client.get("/v1/members", headers={"Authorization": f"Bearer {self.token_c}"}).json()
        self.assertEqual(other["members"], [{"user_id": "user-c", "email": None, "role": "admin", "is_me": True}])


if __name__ == "__main__":
    unittest.main()
