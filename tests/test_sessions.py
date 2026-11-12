from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import timedelta
import io
import json
import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from finsync.api import create_app
from finsync.api.passwords import main as passwords_cli
from finsync.api.server import CSRF_HEADER, SESSION_COOKIE
from finsync.core import AuthenticationError, AuthorizationError, SessionService, TokenService
from finsync.core import sessions as sessions_module
from finsync.core.sessions import csrf_token, hash_password, verify_password
from finsync.storage import FinSyncStorage

PASSWORD_A = "anna-jelszava-1"
PASSWORD_C = "cecil-jelszava-1"
MANUAL = {"amount": "-4500", "currency": "HUF", "description": "Weekly shop", "happened_at": "2026-09-05"}

_PRODUCTION_COST = (sessions_module._SCRYPT_N, sessions_module._SCRYPT_R, sessions_module._SCRYPT_P)
# The production scrypt cost takes about 0.2 s per hash; the tests use a cheap one so the suite stays
# fast. test_the_production_cost_is_stored_with_the_hash checks the real setting.
_cheap_scrypt = mock.patch.multiple(sessions_module, _SCRYPT_N=2**10, _SCRYPT_P=1)


def setUpModule() -> None:
    _cheap_scrypt.start()


def tearDownModule() -> None:
    _cheap_scrypt.stop()


class PasswordHashTest(unittest.TestCase):
    def test_the_production_cost_is_stored_with_the_hash(self) -> None:
        self.assertEqual(_PRODUCTION_COST, (2**14, 8, 5))
        with mock.patch.multiple(sessions_module, _SCRYPT_N=_PRODUCTION_COST[0], _SCRYPT_P=_PRODUCTION_COST[2]):
            stored = hash_password(PASSWORD_A)
        self.assertTrue(stored.startswith("scrypt$16384$8$5$"))
        self.assertTrue(verify_password(PASSWORD_A, stored))
        self.assertFalse(verify_password(PASSWORD_A + "x", stored))
        for broken in ("", "scrypt$1$2", "bcrypt$16384$8$5$c2FsdA==$aGFzaA==", "scrypt$x$8$5$c2FsdA==$aGFzaA=="):
            with self.subTest(stored=broken):
                self.assertFalse(verify_password(PASSWORD_A, broken))


class SessionServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tempdir.name, "test.db")
        self.storage = FinSyncStorage(self.db_path)
        self.storage.add_group_membership("user-a", "group-1")
        self.sessions = SessionService(self.storage)
        self.sessions.set_password("user-a", PASSWORD_A)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_only_salted_hashes_are_stored(self) -> None:
        secret, _ = self.sessions.sign_in("user-a", PASSWORD_A)
        connection = sqlite3.connect(self.db_path)
        try:
            dump = "\n".join(connection.iterdump())
        finally:
            connection.close()
        self.assertNotIn(PASSWORD_A, dump)
        self.assertNotIn(secret, dump)
        self.assertNotIn(secret[4:], dump)
        stored = self.storage.get_member_password("user-a")
        self.assertTrue(stored.startswith("scrypt$"))
        self.assertTrue(verify_password(PASSWORD_A, stored))
        # The same password gives a different hash for another member (salt).
        self.storage.add_group_membership("user-b", "group-1")
        self.sessions.set_password("user-b", PASSWORD_A)
        self.assertNotEqual(self.storage.get_member_password("user-b"), stored)

    def test_passwords_are_set_only_for_members_and_with_a_sensible_length(self) -> None:
        with self.assertRaisesRegex(ValueError, "not a member"):
            self.sessions.set_password("stranger", PASSWORD_A)
        with self.assertRaisesRegex(ValueError, "characters"):
            self.sessions.set_password("user-a", "short")
        with self.assertRaisesRegex(ValueError, "characters"):
            self.sessions.set_password("user-a", "x" * 257)

    def test_wrong_password_unknown_member_and_member_without_password_get_the_same_answer(self) -> None:
        self.storage.add_group_membership("user-b", "group-1")  # a member without a password
        messages = set()
        for user, password in (("user-a", "wrong-password"), ("nobody", PASSWORD_A), ("user-b", PASSWORD_A), ("", "")):
            with self.subTest(user=user), self.assertRaises(AuthenticationError) as caught:
                self.sessions.sign_in(user, password)
            messages.add(str(caught.exception))
        self.assertEqual(len(messages), 1)

    def test_the_same_field_takes_the_e_mail_address_or_the_member_id(self) -> None:
        self.assertEqual(self.sessions.set_email("user-a", " Anna.Minta@Example.com "), "anna.minta@example.com")
        for login in ("user-a", "anna.minta@example.com", "ANNA.MINTA@example.COM"):
            with self.subTest(login=login):
                _, record = self.sessions.sign_in(login, PASSWORD_A)
                self.assertEqual(record.user_id, "user-a")
        with self.assertRaises(AuthenticationError):
            self.sessions.sign_in("other@example.com", PASSWORD_A)

    def test_e_mail_addresses_are_checked_and_unique(self) -> None:
        self.storage.add_group_membership("user-b", "group-1")
        self.sessions.set_email("user-a", "anna@example.com")
        with self.assertRaisesRegex(ValueError, "another member"):
            self.sessions.set_email("user-b", "ANNA@example.com")
        for bad in ("anna", "anna@", "@example.com", "an na@example.com", "a@b", "x" * 250 + "@example.com"):
            with self.subTest(email=bad), self.assertRaisesRegex(ValueError, "e-mail"):
                self.sessions.set_email("user-b", bad)
        with self.assertRaisesRegex(ValueError, "not a member"):
            self.sessions.set_email("stranger", "stranger@example.com")
        # Setting the address keeps the password, and setting the password keeps the address.
        self.sessions.sign_in("anna@example.com", PASSWORD_A)
        self.sessions.set_password("user-a", "uj-jelszo-1234")
        self.assertEqual(self.storage.get_member_email("user-a"), "anna@example.com")

    def test_a_member_of_several_groups_names_the_group(self) -> None:
        self.storage.add_group_membership("user-a", "group-2")
        with self.assertRaisesRegex(ValueError, "group_id is required"):
            self.sessions.sign_in("user-a", PASSWORD_A)
        _, record = self.sessions.sign_in("user-a", PASSWORD_A, "group-2")
        self.assertEqual(record.group_id, "group-2")
        with self.assertRaises(AuthorizationError):
            self.sessions.sign_in("user-a", PASSWORD_A, "group-3")

    def test_expired_revoked_and_malformed_sessions_are_rejected(self) -> None:
        expired, _ = SessionService(self.storage, lifetime=timedelta(seconds=-1)).sign_in("user-a", PASSWORD_A)
        secret, record = self.sessions.sign_in("user-a", PASSWORD_A)
        self.sessions.sign_out(record.id)
        for value in (expired, secret, None, "", "fss_short", "fss_" + "A" * 43):
            with self.subTest(value=value), self.assertRaises(AuthenticationError):
                self.sessions.session(value)

    def test_a_new_password_ends_open_sessions(self) -> None:
        secret, _ = self.sessions.sign_in("user-a", PASSWORD_A)
        self.sessions.set_password("user-a", "uj-jelszo-1234")
        with self.assertRaises(AuthenticationError):
            self.sessions.session(secret)
        with self.assertRaises(AuthenticationError):
            self.sessions.sign_in("user-a", PASSWORD_A)
        self.sessions.sign_in("user-a", "uj-jelszo-1234")

    def test_a_version_3_database_gets_the_sign_in_tables(self) -> None:
        connection = sqlite3.connect(self.db_path)
        with connection:
            connection.execute("DROP TABLE member_accounts")
            connection.execute("DROP TABLE web_sessions")
            connection.execute("DELETE FROM schema_version WHERE version = 4")
        connection.close()
        sessions = SessionService(FinSyncStorage(self.db_path))
        sessions.set_password("user-a", PASSWORD_A)
        secret, _ = sessions.sign_in("user-a", PASSWORD_A)
        self.assertEqual(sessions.session(secret).user_id, "user-a")

    def test_command_line_sets_a_password(self) -> None:
        with mock.patch("sys.stdin", io.StringIO("parancssori-jelszo\n")), redirect_stdout(io.StringIO()):
            self.assertEqual(passwords_cli(["--db", self.db_path, "set", "--user", "user-a", "--password-stdin"]), 0)
        self.sessions.sign_in("user-a", "parancssori-jelszo")
        with mock.patch("sys.stdin", io.StringIO("rovid\n")), redirect_stderr(io.StringIO()):
            self.assertEqual(passwords_cli(["--db", self.db_path, "set", "--user", "user-a", "--password-stdin"]), 2)
        with mock.patch("sys.stdin", io.StringIO("parancssori-jelszo\n")), redirect_stderr(io.StringIO()):
            self.assertEqual(passwords_cli(["--db", self.db_path, "set", "--user", "nobody", "--password-stdin"]), 2)
        # With an e-mail address; a short password refuses the whole command.
        args = ["--db", self.db_path, "set", "--user", "user-a", "--email", "anna@example.com", "--password-stdin"]
        with mock.patch("sys.stdin", io.StringIO("rovid\n")), redirect_stderr(io.StringIO()):
            self.assertEqual(passwords_cli(args), 2)
        self.assertIsNone(self.storage.get_member_email("user-a"))
        with mock.patch("sys.stdin", io.StringIO("email-es-jelszo\n")), redirect_stdout(io.StringIO()):
            self.assertEqual(passwords_cli(args), 0)
        self.sessions.sign_in("anna@example.com", "email-es-jelszo")


class SessionApiTest(unittest.TestCase):
    """Member A is in group 1 and member C in group 2, both with a password; B has a token in group 1."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        for user, group in (("user-a", "group-1"), ("user-b", "group-1"), ("user-c", "group-2")):
            self.storage.add_group_membership(user, group)
        sessions = SessionService(self.storage)
        sessions.set_password("user-a", PASSWORD_A)
        sessions.set_password("user-c", PASSWORD_C)
        self.token_b, _ = TokenService(self.storage).create("user-b", "group-1", "phone")
        # https, so the client sends the Secure cookie back, as a browser does.
        self.client = TestClient(create_app(self.storage), base_url="https://testserver")

    def tearDown(self) -> None:
        self.client.close()
        self.tempdir.cleanup()

    def _sign_in(self, user: str = "user-a", password: str = PASSWORD_A) -> dict:
        response = self.client.post("/v1/session", json={"login": user, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def _state(self):
        return (self.storage.list_transactions("group-1"), self.storage.list_transactions("group-2"))

    def test_sign_in_sets_a_strict_httponly_secure_cookie(self) -> None:
        response = self.client.post("/v1/session", json={"login": "user-a", "password": PASSWORD_A})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual((body["user_id"], body["group_id"]), ("user-a", "group-1"))
        cookie = response.headers["set-cookie"]
        for attribute in ("HttpOnly", "Secure", "SameSite=strict", "Path=/v1", "Max-Age=43200"):
            self.assertIn(attribute.lower(), cookie.lower())
        secret = self.client.cookies.get(SESSION_COOKIE)
        self.assertTrue(secret.startswith("fss_"))
        self.assertNotIn(secret, response.text)  # The secret is only in the cookie, never readable by scripts.
        self.assertEqual(body["csrf_token"], csrf_token(secret))

    def test_a_failed_sign_in_says_nothing_about_the_member_and_sets_no_cookie(self) -> None:
        answers = set()
        for user, password in (("user-a", "wrong-password"), ("nobody", PASSWORD_A), ("user-b", PASSWORD_A)):
            with self.subTest(user=user):
                response = self.client.post("/v1/session", json={"login": user, "password": password})
                self.assertEqual(response.status_code, 401)
                self.assertNotIn("set-cookie", response.headers)
                answers.add(response.text)
        self.assertEqual(len(answers), 1)

    def test_the_session_reads_the_members_own_group_only(self) -> None:
        self.client.post("/v1/transactions", json=MANUAL, headers={"Authorization": f"Bearer {self.token_b}"})
        self._sign_in("user-c", PASSWORD_C)
        response = self.client.get("/v1/events", headers={"X-User-Id": "user-a", "X-Group-Id": "group-1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["events"], [])
        self.client.cookies.clear()
        self._sign_in()
        listed = json.dumps(self.client.get("/v1/events").json())
        self.assertIn("group-1", listed)

    def test_writes_with_the_cookie_need_the_csrf_token(self) -> None:
        session = self._sign_in()
        before = self._state()
        for headers in ({}, {CSRF_HEADER: "0" * 64}, {CSRF_HEADER: ""}):
            with self.subTest(headers=headers):
                response = self.client.post("/v1/transactions", json=MANUAL, headers=headers)
                self.assertEqual(response.status_code, 403)
                self.assertIn("CSRF", response.json()["error"])
        self.assertEqual(self._state(), before)
        response = self.client.post("/v1/transactions", json=MANUAL, headers={CSRF_HEADER: session["csrf_token"]})
        self.assertEqual(response.status_code, 201)
        stored = self.storage.list_transactions("group-1")
        self.assertEqual([(tx.user_id, tx.group_id) for tx in stored], [("user-a", "group-1")])

    def test_another_sessions_csrf_token_does_not_work(self) -> None:
        other = self._sign_in("user-c", PASSWORD_C)
        self.client.cookies.clear()
        self._sign_in()
        response = self.client.post("/v1/transactions", json=MANUAL, headers={CSRF_HEADER: other["csrf_token"]})
        self.assertEqual(response.status_code, 403)

    def test_a_token_wins_over_the_cookie(self) -> None:
        self._sign_in()
        response = self.client.post("/v1/transactions", json=MANUAL, headers={"Authorization": f"Bearer {self.token_b}"})
        self.assertEqual(response.status_code, 201)  # No CSRF token needed: a token is not sent by the browser.
        self.assertEqual([tx.user_id for tx in self.storage.list_transactions("group-1")], ["user-b"])

    def test_the_current_session_survives_a_page_reload(self) -> None:
        session = self._sign_in()
        response = self.client.get("/v1/session")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), session)
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/v1/session").status_code, 401)
        self.assertEqual(self.client.get("/v1/events").status_code, 401)

    def test_sign_out_needs_the_csrf_token_and_ends_the_session(self) -> None:
        session = self._sign_in()
        secret = self.client.cookies.get(SESSION_COOKIE)
        self.assertEqual(self.client.delete("/v1/session").status_code, 403)
        self.assertEqual(self.client.get("/v1/session").status_code, 200)
        response = self.client.delete("/v1/session", headers={CSRF_HEADER: session["csrf_token"]})
        self.assertEqual(response.status_code, 204)
        self.assertIn("max-age=0", response.headers["set-cookie"].lower())
        # Even a client that kept the cookie is signed out on the server.
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/v1/events", headers={"Cookie": f"{SESSION_COOKIE}={secret}"}).status_code, 401)

    def test_a_session_stops_working_when_its_member_leaves_the_group(self) -> None:
        session = self._sign_in()
        self.storage.remove_group_membership("user-a", "group-1")
        self.assertEqual(self.client.get("/v1/events").status_code, 403)
        response = self.client.post("/v1/transactions", json=MANUAL, headers={CSRF_HEADER: session["csrf_token"]})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.storage.list_transactions("group-1"), [])


if __name__ == "__main__":
    unittest.main()
