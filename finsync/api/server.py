from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import re
from urllib.parse import urlparse

from finsync.core import (
    AuthorizationError,
    ConflictError,
    FinSyncService,
    NotFoundError,
    ReviewItem,
    StoreResult,
)
from finsync.storage import EventRecord, FinSyncStorage, TransactionRecord


_REVIEW_ACTION = re.compile(r"^/v1/matches/(?P<decision_id>\d+)/(?P<action>confirm|reject)$")
_SPLIT = re.compile(r"^/v1/events/(?P<event_id>\d+)/split$")


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
                result = self.service.ingest_notification(user_id, group_id, message)
                self._send_json(HTTPStatus.CREATED, _result_json(result))
                return

            if path == "/v1/transactions":
                result = self.service.create_manual_transaction(user_id, group_id, payload)
                self._send_json(HTTPStatus.CREATED, _result_json(result))
                return

            if path == "/v1/transactions/bulk":
                rows = payload.get("rows")
                if not isinstance(rows, list):
                    raise ValueError("rows must be a list")
                results = self.service.bulk_create_manual_transactions(user_id, group_id, rows)
                self._send_json(
                    HTTPStatus.CREATED,
                    {
                        "transaction_ids": [result.transaction_id for result in results],
                        "results": [_result_json(result) for result in results],
                    },
                )
                return

            review = _REVIEW_ACTION.match(path)
            if review:
                decision_id = int(review.group("decision_id"))
                if review.group("action") == "confirm":
                    result = self.service.confirm_match(user_id, group_id, decision_id)
                else:
                    result = self.service.reject_match(user_id, group_id, decision_id)
                self._send_json(HTTPStatus.OK, _result_json(result))
                return

            split = _SPLIT.match(path)
            if split:
                transaction_id = payload.get("transaction_id")
                if not isinstance(transaction_id, int) or isinstance(transaction_id, bool):
                    raise ValueError("transaction_id must be an integer")
                result = self.service.split_event(user_id, group_id, int(split.group("event_id")), transaction_id)
                self._send_json(HTTPStatus.OK, _result_json(result))
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        except AuthorizationError as error:
            self._send_json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except NotFoundError as error:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": str(error)})
        except ConflictError as error:
            self._send_json(HTTPStatus.CONFLICT, {"error": str(error)})
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def do_GET(self) -> None:  # noqa: N802
        try:
            path = urlparse(self.path).path
            if path == "/v1/transactions":
                user_id, group_id = self._identity()
                transactions = self.service.list_group_transactions(user_id, group_id)
                self._send_json(HTTPStatus.OK, {"transactions": [_transaction_json(tx) for tx in transactions]})
                return

            if path == "/v1/matches/review":
                user_id, group_id = self._identity()
                items = self.service.list_open_reviews(user_id, group_id)
                self._send_json(HTTPStatus.OK, {"reviews": [_review_json(item) for item in items]})
                return

            if path == "/v1/events":
                user_id, group_id = self._identity()
                events = self.service.list_group_events(user_id, group_id)
                self._send_json(HTTPStatus.OK, {"events": [_event_json(event) for event in events]})
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
        except AuthorizationError as error:
            self._send_json(HTTPStatus.FORBIDDEN, {"error": str(error)})
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)})


def _result_json(result: StoreResult) -> dict:
    return {
        "transaction_id": result.transaction_id,
        "event_id": result.event_id,
        "match_outcome": result.match_outcome,
    }


def _review_json(item: ReviewItem) -> dict:
    return {
        "decision_id": item.decision_id,
        "score": item.score,
        "features": item.features,
        "transaction": _transaction_json(item.transaction),
        "candidate_event": _event_json(item.candidate_event),
    }


def _transaction_json(tx: TransactionRecord) -> dict:
    return {
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
        "happened_at_precision": tx.happened_at_precision,
        "created_at": tx.created_at.isoformat(),
        "event_id": tx.event_id,
        "duplicate_of_id": tx.duplicate_of_id,
    }


def _event_json(event: EventRecord) -> dict:
    return {
        "id": event.id,
        "amount": str(event.amount),
        "currency": event.currency,
        "direction": event.direction,
        "happened_at": event.happened_at.isoformat(),
        "merchant": event.merchant,
        "category": event.category,
        "primary_transaction_id": event.primary_transaction_id,
        "review_state": event.review_state,
        "transactions": [_transaction_json(tx) for tx in event.transactions],
    }


def run_server(host: str = "127.0.0.1", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), FinSyncRequestHandler)
    print(f"FinSync API running on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
