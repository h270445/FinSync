from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from finsync.api import create_app
from finsync.api.server import MAX_BODY_BYTES, MAX_BULK_BODY_BYTES, BodySizeLimit
from finsync.core import TokenService
from finsync.storage import FinSyncStorage

ROW = {"amount": "-4500", "currency": "HUF", "description": "Weekly shop", "happened_at": "2026-09-05"}


class RequestLimitTest(unittest.TestCase):
    """Oversized, unsized and malformed requests are refused before anything is stored."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.storage = FinSyncStorage(os.path.join(self.tempdir.name, "test.db"))
        self.storage.add_group_membership("user-1", "group-1")
        token, _ = TokenService(self.storage).create("user-1", "group-1", "test")
        self.headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        self.client = TestClient(create_app(self.storage))

    def tearDown(self) -> None:
        self.client.close()
        self.tempdir.cleanup()

    def _post(self, path: str, content: bytes):
        return self.client.post(path, content=content, headers=self.headers)

    def _stored(self) -> int:
        return len(self.storage.list_transactions("group-1"))

    def test_a_body_over_the_limit_is_refused_with_413(self) -> None:
        padded = json.dumps({**ROW, "description": "x" * MAX_BODY_BYTES}).encode()
        response = self._post("/v1/transactions", padded)
        self.assertEqual(response.status_code, 413)
        self.assertIn("larger than", response.json()["error"])
        self.assertEqual(self._stored(), 0)

    def test_bulk_import_has_a_larger_limit(self) -> None:
        # Few, long rows: the size is what matters here, and matching cost grows with the row count.
        rows = [{**ROW, "description": "x" * 4000, "source_ref": f"row-{index}"} for index in range(20)]
        body = json.dumps({"rows": rows}).encode()
        self.assertGreater(len(body), MAX_BODY_BYTES)
        self.assertEqual(self._post("/v1/transactions/bulk", body).status_code, 201)

        too_big = json.dumps({"rows": [{**ROW, "description": "x" * MAX_BULK_BODY_BYTES}]}).encode()
        self.assertEqual(self._post("/v1/transactions/bulk", too_big).status_code, 413)
        self.assertEqual(self._stored(), 20)

    def test_chunked_bodies_are_counted(self) -> None:
        def chunks(body: bytes):
            for start in range(0, len(body), 4096):
                yield body[start : start + 4096]

        small = json.dumps(ROW).encode()
        response = self.client.post("/v1/transactions", content=chunks(small), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        large = json.dumps({**ROW, "description": "x" * MAX_BODY_BYTES}).encode()
        response = self.client.post("/v1/transactions", content=chunks(large), headers=self.headers)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self._stored(), 1)

    def test_a_small_content_length_does_not_let_a_large_body_through(self) -> None:
        """Content-Length 10 with a chunked body of 100 KiB: the bytes that arrive are what counts."""
        reached_app = []

        async def app(scope, receive, send):
            reached_app.append(await receive())

        chunk = b"x" * 1024
        messages = [{"type": "http.request", "body": chunk, "more_body": True} for _ in range(100)]
        sent = []

        async def receive():
            return messages.pop(0)

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/v1/transactions",
            "headers": [(b"content-length", b"10"), (b"transfer-encoding", b"chunked")],
        }
        asyncio.run(BodySizeLimit(app)(scope, receive, send))
        self.assertEqual(reached_app, [])
        self.assertEqual(sent[0]["status"], 413)

    def test_malformed_requests_get_a_clear_400(self) -> None:
        cases = {
            "invalid JSON": ("/v1/transactions", b"{not json"),
            "not an object": ("/v1/transactions", b"[1, 2]"),
            "missing field": ("/v1/transactions", json.dumps({"amount": "-1"}).encode()),
            "zero amount": ("/v1/transactions", json.dumps({**ROW, "amount": "0"}).encode()),
            "rows not a list": ("/v1/transactions/bulk", json.dumps({"rows": "x"}).encode()),
            "one bad row": ("/v1/transactions/bulk", json.dumps({"rows": [ROW, {**ROW, "amount": "x"}]}).encode()),
            "empty message": ("/v1/notifications/ingest", json.dumps({"message": " "}).encode()),
            "post time without offset": ("/v1/notifications/ingest", json.dumps({"message": "-4 990 Ft, Minta Anna", "posted_at": "2026-11-12T09:15"}).encode()),
            "sign-in without password": ("/v1/session", json.dumps({"login": "user-a"}).encode()),
        }
        for name, (path, content) in cases.items():
            with self.subTest(name):
                response = self._post(path, content)
                self.assertEqual(response.status_code, 400)
                self.assertTrue(response.json()["error"])
        self.assertEqual(self._stored(), 0)

    def test_unknown_routes_answer_in_the_same_error_shape(self) -> None:
        response = self.client.get("/v1/nothing", headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.json())

    def test_the_openapi_schema_describes_what_the_api_does(self) -> None:
        schema = self.client.get("/openapi.json").json()
        self.assertIn("EventOut", schema["components"]["schemas"])
        for path, operations in schema["paths"].items():
            for method, operation in operations.items():
                with self.subTest(path=path, method=method):
                    # Validation errors are answered with 400, never 422.
                    self.assertNotIn("422", operation["responses"])
                    # Every data route takes the bearer token, so /docs and generated clients send it.
                    # Signing in needs nothing; the other session routes take the session cookie.
                    if path == "/v1/session":
                        expected = [] if method == "post" else [{"SessionCookie": []}]
                    else:
                        expected = [{"HTTPBearer": []}]
                    self.assertEqual(operation["security"], expected)
        bulk = schema["components"]["schemas"]["BulkIn"]["properties"]["rows"]
        self.assertEqual(bulk["items"], {"$ref": "#/components/schemas/ManualTransactionIn"})


if __name__ == "__main__":
    unittest.main()
