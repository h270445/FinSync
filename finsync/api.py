from __future__ import annotations

from datetime import datetime
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from finsync.service import AuthorizationError, FinSyncService
from finsync.storage import FinSyncStorage


class FinSyncRequestHandler(BaseHTTPRequestHandler):
    service = FinSyncService(FinSyncStorage())
    service.bootstrap_demo_membership()

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as error:
            raise ValueError("Invalid JSON") from error
        if not isinstance(parsed, dict):
            raise ValueError("JSON body must be an object")
        return parsed

    def _identity(self) -> tuple[str, str]:
        user_id = self.headers.get("X-User-Id", "").strip()
        group_id = self.headers.get("X-Group-Id", "").strip()
        if not user_id or not group_id:
            raise ValueError("X-User-Id and X-Group-Id headers are required")
        return user_id, group_id

    def _send_json(self, status: HTTPStatus, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802
        try:
            path = urlparse(self.path).path
            user_id, group_id = self._identity()
            payload = self._read_json()

            if path == "/v1/notifications/ingest":
                message = str(payload.get("message", "")).strip()
                if not message:
                    raise ValueError("message is required")
                transaction_id = self.service.ingest_notification(user_id, group_id, message)
                self._send_json(HTTPStatus.CREATED, {"transaction_id": transaction_id})
                return

            if path == "/v1/transactions":
                transaction_id = self.service.create_manual_transaction(user_id, group_id, payload)
                self._send_json(HTTPStatus.CREATED, {"transaction_id": transaction_id})
                return

            if path == "/v1/transactions/bulk":
                rows = payload.get("rows")
                if not isinstance(rows, list):
                    raise ValueError("rows must be a list")
                transaction_ids = self.service.bulk_create_manual_transactions(user_id, group_id, rows)
                self._send_json(HTTPStatus.CREATED, {"transaction_ids": transaction_ids})
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        except AuthorizationError as error:
            self._send_json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def do_GET(self) -> None:  # noqa: N802
        try:
            path = urlparse(self.path).path
            if path != "/v1/transactions":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
                return

            user_id, group_id = self._identity()
            transactions = self.service.list_group_transactions(user_id, group_id)
            serialized = [
                {
                    "id": tx.id,
                    "user_id": tx.user_id,
                    "group_id": tx.group_id,
                    "amount": str(tx.amount),
                    "currency": tx.currency,
                    "description": tx.description,
                    "merchant": tx.merchant,
                    "category": tx.category,
                    "source": tx.source,
                    "happened_at": tx.happened_at.isoformat(),
                    "created_at": tx.created_at.isoformat(),
                }
                for tx in transactions
            ]
            self._send_json(HTTPStatus.OK, {"transactions": serialized})
        except AuthorizationError as error:
            self._send_json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})


def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), FinSyncRequestHandler)
    print(f"FinSync API running on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
