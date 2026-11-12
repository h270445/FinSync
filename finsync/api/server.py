from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, StrictInt, WithJsonSchema
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from finsync.core import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    FinSyncService,
    NotFoundError,
    Principal,
    ReviewItem,
    StoreResult,
    TokenService,
)
from finsync.storage import EventRecord, FinSyncStorage, TransactionRecord

# Request body limits. A bulk import carries many rows; every other request is one small object.
MAX_BODY_BYTES = 64 * 1024
MAX_BULK_BODY_BYTES = 1024 * 1024
_BULK_PATH = "/v1/transactions/bulk"


# Request bodies. The service validates the values again, so the HTTP layer and the tests on the
# service keep one set of rules; these models describe the shapes for the OpenAPI schema.


class NotificationIn(BaseModel):
    message: str


class ManualTransactionIn(BaseModel):
    amount: Decimal | str
    currency: str
    description: str
    happened_at: str
    merchant: str | None = None
    direction: Literal["expense", "income"] | None = None
    source_ref: str | None = None


class BulkIn(BaseModel):
    # Rows are validated one by one by the service, so a bad row is reported with its index and
    # the whole import is refused; the schema still tells clients that each row is a manual entry.
    rows: Annotated[
        list[Any],
        WithJsonSchema({"type": "array", "items": {"$ref": "#/components/schemas/ManualTransactionIn"}}),
    ]


class SplitIn(BaseModel):
    transaction_id: StrictInt


# Responses.


class ErrorOut(BaseModel):
    error: str


class StoreResultOut(BaseModel):
    transaction_id: int
    event_id: int
    match_outcome: str


class BulkOut(BaseModel):
    transaction_ids: list[int]
    results: list[StoreResultOut]


class TransactionOut(BaseModel):
    id: int
    user_id: str
    group_id: str
    amount: str
    currency: str
    description: str
    merchant: str | None
    category: str
    source: str
    happened_at: str
    happened_at_precision: str
    created_at: str
    event_id: int | None
    duplicate_of_id: int | None


class TransactionsOut(BaseModel):
    transactions: list[TransactionOut]


class EventOut(BaseModel):
    id: int
    amount: str
    currency: str
    direction: str
    happened_at: str
    merchant: str | None
    category: str
    primary_transaction_id: int | None
    review_state: str
    transactions: list[TransactionOut]


class EventsOut(BaseModel):
    events: list[EventOut]


class ReviewOut(BaseModel):
    decision_id: int
    score: float | None
    features: dict[str, Any] | None
    transaction: TransactionOut
    candidate_event: EventOut


class ReviewsOut(BaseModel):
    reviews: list[ReviewOut]


class DecisionOut(BaseModel):
    id: int
    transaction_id: int
    candidate_event_id: int | None
    outcome: str
    score: float | None
    features: dict[str, Any] | None
    matcher_version: str
    decided_by: str
    supersedes_id: int | None
    superseded: bool
    created_at: str


class DecisionsOut(BaseModel):
    decisions: list[DecisionOut]


# "4XX" also replaces FastAPI's default 422 entry: validation errors are answered with 400.
_ERRORS: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorOut} for status in (400, 401, 403, 404, 409, 413, "4XX")
}


class BodySizeLimit:
    """Rejects a POST body over the path's limit with 413, before the app parses it.

    A declared ``Content-Length`` over the limit is refused at once. Every body is also counted
    as it arrives and buffered up to the limit, so chunked bodies, or a ``Content-Length`` that
    disagrees with the chunked framing, cannot bring more past it.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] != "POST":
            await self.app(scope, receive, send)
            return
        limit = MAX_BULK_BODY_BYTES if scope["path"] == _BULK_PATH else MAX_BODY_BYTES
        length = dict(scope["headers"]).get(b"content-length")
        if length is not None and length.isdigit() and int(length) > limit:
            await _send_error(send, 413, f"Request body is larger than {limit} bytes")
            return

        body = bytearray()
        more = True
        while more:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body += message.get("body", b"")
            if len(body) > limit:
                await _send_error(send, 413, f"Request body is larger than {limit} bytes")
                return
            more = message.get("more_body", False)

        replayed = False

        async def replay() -> Message:
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


async def _send_error(send: Send, status: int, message: str) -> None:
    response = JSONResponse({"error": message}, status_code=status)
    body: Message = {"type": "http.response.body", "body": response.body}
    await send({"type": "http.response.start", "status": status, "headers": response.raw_headers})
    await send(body)


def _validation_message(error: RequestValidationError) -> str:
    parts = []
    for item in error.errors():
        location = ".".join(str(part) for part in item.get("loc", ()) if part != "body")
        parts.append(f"{location}: {item.get('msg')}" if location else str(item.get("msg")))
    return "; ".join(parts) or "Invalid request"


def create_app(storage: FinSyncStorage) -> FastAPI:
    """The /v1 API bound to one database."""
    service = FinSyncService(storage)
    tokens = TokenService(storage)
    app = FastAPI(title="FinSync API", version="0.3.0-dev", responses=_ERRORS)
    app.add_middleware(BodySizeLimit)

    # auto_error=False: TokenService decides and words every refusal; HTTPBearer only reads the
    # header and puts the bearer scheme into the OpenAPI schema (and the /docs "Authorize" button).
    bearer = HTTPBearer(auto_error=False)

    def principal(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> Principal:
        """The caller's member and group, from the API token only; client identity headers are ignored."""
        return tokens.authenticate(f"Bearer {credentials.credentials}" if credentials else None)

    Caller = Annotated[Principal, Depends(principal)]

    @app.exception_handler(AuthenticationError)
    async def unauthorized(_: Request, error: AuthenticationError) -> JSONResponse:
        return JSONResponse(
            {"error": str(error)}, status_code=401, headers={"WWW-Authenticate": 'Bearer realm="finsync"'}
        )

    @app.exception_handler(AuthorizationError)
    async def forbidden(_: Request, error: AuthorizationError) -> JSONResponse:
        return JSONResponse({"error": str(error)}, status_code=403)

    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, error: NotFoundError) -> JSONResponse:
        return JSONResponse({"error": str(error)}, status_code=404)

    @app.exception_handler(ConflictError)
    async def conflict(_: Request, error: ConflictError) -> JSONResponse:
        return JSONResponse({"error": str(error)}, status_code=409)

    @app.exception_handler(ValueError)
    async def bad_request(_: Request, error: ValueError) -> JSONResponse:
        return JSONResponse({"error": str(error)}, status_code=400)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse({"error": _validation_message(error)}, status_code=400)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, error: StarletteHTTPException) -> JSONResponse:
        return JSONResponse({"error": str(error.detail)}, status_code=error.status_code, headers=error.headers)

    @app.post("/v1/notifications/ingest", status_code=201)
    def ingest_notification(body: NotificationIn, caller: Caller) -> StoreResultOut:
        message = body.message.strip()
        if not message:
            raise ValueError("message is required")
        return _result(service.ingest_notification(caller.user_id, caller.group_id, message))

    @app.post("/v1/transactions", status_code=201)
    def create_transaction(body: ManualTransactionIn, caller: Caller) -> StoreResultOut:
        return _result(service.create_manual_transaction(caller.user_id, caller.group_id, _manual(body)))

    @app.post(_BULK_PATH, status_code=201)
    def bulk_create(body: BulkIn, caller: Caller) -> BulkOut:
        results = service.bulk_create_manual_transactions(caller.user_id, caller.group_id, body.rows)
        return BulkOut(
            transaction_ids=[result.transaction_id for result in results],
            results=[_result(result) for result in results],
        )

    @app.post("/v1/matches/{decision_id}/confirm")
    def confirm_match(decision_id: int, caller: Caller) -> StoreResultOut:
        return _result(service.confirm_match(caller.user_id, caller.group_id, decision_id))

    @app.post("/v1/matches/{decision_id}/reject")
    def reject_match(decision_id: int, caller: Caller) -> StoreResultOut:
        return _result(service.reject_match(caller.user_id, caller.group_id, decision_id))

    @app.post("/v1/events/{event_id}/split")
    def split_event(event_id: int, body: SplitIn, caller: Caller) -> StoreResultOut:
        return _result(service.split_event(caller.user_id, caller.group_id, event_id, body.transaction_id))

    @app.get("/v1/transactions")
    def list_transactions(caller: Caller) -> TransactionsOut:
        transactions = service.list_group_transactions(caller.user_id, caller.group_id)
        return TransactionsOut(transactions=[_transaction(tx) for tx in transactions])

    @app.get("/v1/matches/review")
    def list_reviews(caller: Caller) -> ReviewsOut:
        items = service.list_open_reviews(caller.user_id, caller.group_id)
        return ReviewsOut(reviews=[_review(item) for item in items])

    @app.get("/v1/events")
    def list_events(caller: Caller) -> EventsOut:
        events = service.list_group_events(caller.user_id, caller.group_id)
        return EventsOut(events=[_event(event) for event in events])

    @app.get("/v1/events/{event_id}/decisions")
    def list_event_decisions(event_id: int, caller: Caller) -> DecisionsOut:
        decisions = service.list_event_decisions(caller.user_id, caller.group_id, event_id)
        superseded = {d["supersedes_id"] for d in decisions if d["supersedes_id"] is not None}
        return DecisionsOut(decisions=[
            DecisionOut(
                **{key: d[key] for key in DecisionOut.model_fields if key != "superseded"},
                superseded=d["id"] in superseded,
            )
            for d in decisions
        ])

    return app


def _manual(body: ManualTransactionIn) -> dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    payload["amount"] = str(payload["amount"])
    return payload


def _result(result: StoreResult) -> StoreResultOut:
    return StoreResultOut(
        transaction_id=result.transaction_id, event_id=result.event_id, match_outcome=result.match_outcome
    )


def _review(item: ReviewItem) -> ReviewOut:
    return ReviewOut(
        decision_id=item.decision_id,
        score=item.score,
        features=item.features,
        transaction=_transaction(item.transaction),
        candidate_event=_event(item.candidate_event),
    )


def _transaction(tx: TransactionRecord) -> TransactionOut:
    return TransactionOut(
        id=tx.id,
        user_id=tx.user_id,
        group_id=tx.group_id,
        amount=str(tx.amount),
        currency=tx.currency,
        description=tx.description,
        merchant=tx.merchant,
        category=tx.category,
        source=tx.source,
        happened_at=tx.happened_at.isoformat(),
        happened_at_precision=tx.happened_at_precision,
        created_at=tx.created_at.isoformat(),
        event_id=tx.event_id,
        duplicate_of_id=tx.duplicate_of_id,
    )


def _event(event: EventRecord) -> EventOut:
    return EventOut(
        id=event.id,
        amount=str(event.amount),
        currency=event.currency,
        direction=event.direction,
        happened_at=event.happened_at.isoformat(),
        merchant=event.merchant,
        category=event.category,
        primary_transaction_id=event.primary_transaction_id,
        review_state=event.review_state,
        transactions=[_transaction(tx) for tx in event.transactions],
    )


def run_server(host: str = "127.0.0.1", port: int = 8080, db_path: str = "finsync.db") -> None:
    import uvicorn

    print(f"FinSync API running on http://{host}:{port} (database: {db_path}, docs: /docs)")
    uvicorn.run(create_app(FinSyncStorage(db_path)), host=host, port=port)
