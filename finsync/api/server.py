"""HTTP layer: the FastAPI app, request and response models, and how a caller is identified.

Routes only translate between HTTP and `FinSyncService`; every rule lives in the service. Identity comes
from an API token or the web session cookie, never from the request body or headers (ADR 0009, 0010).
Errors are 400/403/404/409/413 with `{"error": ...}`, never 422 ([API guide](../../docs/guides/api.md)).
"""

import base64
import binascii
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, StrictInt, WithJsonSchema
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from finsync.core import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    FinSyncService,
    ImportResult,
    NotFoundError,
    Principal,
    ReviewItem,
    SessionService,
    StoreResult,
    TokenService,
    WebSessionRequired,
    require_web_session,
)
from finsync.categorization import CATEGORIES
from finsync.core.overview import Bucket
from finsync.core.sessions import SESSION_LIFETIME, csrf_token
from finsync.ingestion import ColumnMapping
from finsync.storage import (
    ApiTokenRecord,
    EventRecord,
    FinSyncStorage,
    MerchantCategoryRecord,
    OwnAccountRecord,
    TransactionRecord,
    WebSessionRecord,
)

# Request body limits. A bulk import or an export file carries many rows; every other request is one small object.
MAX_BODY_BYTES = 64 * 1024
MAX_BULK_BODY_BYTES = 1024 * 1024
_BULK_PATH = "/v1/transactions/bulk"
_IMPORT_PATH = "/v1/imports"
_LARGE_BODY_PATHS = {_BULK_PATH, _IMPORT_PATH}

# Web sign-in (ADR 0010): the session secret travels only in this HttpOnly cookie; state-changing
# requests made with it also send the session's CSRF token in the header.
SESSION_COOKIE = "finsync_session"
CSRF_HEADER = "X-CSRF-Token"
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# Methods whose body BodySizeLimit counts.
_BODY_METHODS = {"POST", "PUT", "PATCH"}


# Request bodies. The service validates the values again, so the HTTP layer and the tests on the
# service keep one set of rules; these models describe the shapes for the OpenAPI schema.


class NotificationIn(BaseModel):
    # The notification text (for Android: the notification's text, which carries the amount).
    message: str
    # Sent by the Android app: the notification title, the phone's post time as an ISO 8601 instant
    # with offset (ADR 0008), and the bank's transaction id when the notification carries one.
    title: str | None = None
    posted_at: str | None = None
    source_ref: str | None = None
    # The phone's IANA time zone at capture, kept with the raw record for diagnosis only (ADR 0008).
    device_zone: str | None = None


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


class ColumnMappingIn(BaseModel):
    # Header names in the file; matching ignores case. The defaults are FinSync's own generic headers.
    date: str = "date"
    amount: str = "amount"
    description: str = "description"
    merchant: str | None = "merchant"
    currency: str | None = "currency"
    reference: str | None = "reference"
    default_currency: str = "HUF"


class ImportIn(BaseModel):
    # Exactly one of the two. A CSV file as text (the client decodes it, for example from UTF-8 or
    # Windows-1250), or an XLSX workbook as base64; the server reads its first sheet.
    content: str | None = None
    xlsx_base64: str | None = None
    mapping: ColumnMappingIn = ColumnMappingIn()
    # True: check the file and return the rows and errors for the preview, without storing anything.
    dry_run: bool = False


class SplitIn(BaseModel):
    transaction_id: StrictInt


class MerchantRuleIn(BaseModel):
    # The merchant as the member types it ("SPAR"); matched on its normalised words.
    merchant: str
    # One of the allowed categories (GET /v1/merchant-rules lists them).
    category: str


class OwnAccountIn(BaseModel):
    # An account number or IBAN (at least 8 digits), or a name as the bank prints it ("KISS ANNA").
    label: str


class TokenIn(BaseModel):
    # What the token is for, shown in the list, for example "Anna phone".
    name: str


class SignInIn(BaseModel):
    # The member's e-mail address or member id.
    login: str
    password: str
    # Needed only when the member belongs to several groups.
    group_id: str | None = None


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


class ImportRowOut(BaseModel):
    line: int
    happened_on: str
    amount: str
    currency: str
    description: str
    merchant: str | None
    reference: str | None


class RowErrorOut(BaseModel):
    line: int
    error: str


class ImportOut(BaseModel):
    import_batch_id: str
    already_imported: bool
    rows: list[ImportRowOut]
    errors: list[RowErrorOut]
    # One result per row, in file order; empty for a preview.
    results: list[StoreResultOut]
    # Rows per match outcome, for the summary screen.
    summary: dict[str, int]


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


class OverviewBucketOut(BaseModel):
    # "all" for the month total, the category for a category row, the member id for a member row.
    key: str
    currency: str
    # Positive sums; expense and income are never netted.
    expense: str
    income: str
    event_count: int
    # Events in this bucket still waiting for review: already in the sums above, counted here too.
    review_count: int
    review_amount: str


class OverviewOut(BaseModel):
    month: str
    # Months that have events, newest first, for the month picker.
    months: list[str]
    totals: list[OverviewBucketOut]
    categories: list[OverviewBucketOut]
    members: list[OverviewBucketOut]
    # Transfers between the group's own accounts are left out of every sum; only their number is given.
    transfer_count: int


class MerchantRuleOut(BaseModel):
    id: int
    merchant: str
    # The normalised words the rule matches: "SPAR 0123 Kft." -> "spar".
    merchant_key: str
    category: str
    created_by: str
    created_at: str
    updated_at: str


class MerchantRulesOut(BaseModel):
    rules: list[MerchantRuleOut]
    # The categories a rule may name.
    categories: list[str]


class OwnAccountOut(BaseModel):
    id: int
    label: str
    # "account" (matched on its digits) or "name" (matched on its words).
    kind: str
    match_key: str
    created_by: str
    created_at: str


class OwnAccountsOut(BaseModel):
    own_accounts: list[OwnAccountOut]


class MemberRoleIn(BaseModel):
    # "admin" (changes the group's settings) or "member".
    role: str


class MemberOut(BaseModel):
    user_id: str
    # The member's sign-in address, if they have a web password.
    email: str | None
    # "admin" or "member". Only an admin changes group settings (merchant rules, roles).
    role: str
    # True for the signed-in caller.
    is_me: bool


class MembersOut(BaseModel):
    members: list[MemberOut]


class TokenOut(BaseModel):
    id: int
    name: str
    # The first 8 characters, to recognise the token; the token itself is never stored.
    prefix: str
    created_at: str
    last_used_at: str | None
    revoked_at: str | None


class TokensOut(BaseModel):
    tokens: list[TokenOut]


class CreatedTokenOut(BaseModel):
    # Shown once: only its hash is stored, so it cannot be retrieved again.
    token: str
    record: TokenOut


class SessionOut(BaseModel):
    user_id: str
    group_id: str
    expires_at: str
    # Send it back in the X-CSRF-Token header with every POST, PUT, PATCH or DELETE.
    csrf_token: str


# "4XX" also replaces FastAPI's default 422 entry: validation errors are answered with 400.
_ERRORS: dict[int | str, dict[str, Any]] = {
    status: {"model": ErrorOut} for status in (400, 401, 403, 404, 409, 413, "4XX")
}


class BodySizeLimit:
    """Rejects a POST or PUT body over the path's limit with 413, before the app parses it.

    A declared ``Content-Length`` over the limit is refused at once. Every body is also counted
    as it arrives and buffered up to the limit, so chunked bodies, or a ``Content-Length`` that
    disagrees with the chunked framing, cannot bring more past it.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _BODY_METHODS:
            await self.app(scope, receive, send)
            return
        limit = MAX_BULK_BODY_BYTES if scope["path"] in _LARGE_BODY_PATHS else MAX_BODY_BYTES
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
    sessions = SessionService(storage)
    app = FastAPI(title="FinSync API", version="0.3.0-dev", responses=_ERRORS)
    app.add_middleware(BodySizeLimit)

    # auto_error=False: TokenService decides and words every refusal; HTTPBearer only reads the
    # header and puts the bearer scheme into the OpenAPI schema (and the /docs "Authorize" button).
    bearer = HTTPBearer(auto_error=False)
    # Only for the /v1/session routes' schema; the data routes read the cookie in principal().
    session_cookie = APIKeyCookie(name=SESSION_COOKIE, scheme_name="SessionCookie", auto_error=False)

    def principal(
        request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
    ) -> Principal:
        """The caller's member and group, from the API token or the web session cookie.

        Client identity headers are ignored. A token wins over a cookie. With the cookie, a
        state-changing request must also carry the session's CSRF token.
        """
        cookie = request.cookies.get(SESSION_COOKIE)
        if credentials is None and cookie is not None:
            return sessions.authenticate(
                cookie, request.headers.get(CSRF_HEADER), request.method not in _SAFE_METHODS
            )
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

    @app.exception_handler(WebSessionRequired)
    async def web_session_required(_: Request, error: WebSessionRequired) -> JSONResponse:
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

    @app.post("/v1/session", openapi_extra={"security": []})
    def sign_in(body: SignInIn, response: Response) -> SessionOut:
        """Sign in to the web app with e-mail address or member id and password; sets the HttpOnly session cookie."""
        secret, record = sessions.sign_in(body.login, body.password, body.group_id)
        response.set_cookie(
            SESSION_COOKIE,
            secret,
            max_age=int(SESSION_LIFETIME.total_seconds()),
            path="/v1",
            secure=True,
            httponly=True,
            samesite="strict",
        )
        return _session(record, secret)

    @app.get("/v1/session")
    def current_session(cookie: Annotated[str | None, Depends(session_cookie)]) -> SessionOut:
        """The signed-in member and group, and the CSRF token, e.g. after a page reload."""
        return _session(sessions.session(cookie), str(cookie))

    @app.delete("/v1/session", status_code=204)
    def sign_out(request: Request, cookie: Annotated[str | None, Depends(session_cookie)]) -> Response:
        """Sign out: the session ends on the server and the cookie is cleared. Needs the CSRF token."""
        caller = sessions.authenticate(cookie, request.headers.get(CSRF_HEADER), state_changing=True)
        assert caller.session_id is not None
        sessions.sign_out(caller.session_id)
        response = Response(status_code=204)
        response.delete_cookie(SESSION_COOKIE, path="/v1", secure=True, httponly=True, samesite="strict")
        return response

    @app.post("/v1/notifications/ingest", status_code=201)
    def ingest_notification(body: NotificationIn, caller: Caller) -> StoreResultOut:
        message = body.message.strip()
        if not message:
            raise ValueError("message is required")
        return _result(
            service.ingest_notification(
                caller.user_id,
                caller.group_id,
                message,
                title=body.title,
                posted_at=body.posted_at,
                source_ref=body.source_ref,
                device_zone=body.device_zone,
            )
        )

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

    @app.post(_IMPORT_PATH, responses={200: {"model": ImportOut, "description": "Preview (dry_run)"}}, status_code=201)
    def import_file(body: ImportIn, caller: Caller, response: Response) -> ImportOut:
        """Import a spreadsheet export (CSV): every row or none; with dry_run, only the preview."""
        mapping = ColumnMapping(**body.mapping.model_dump())
        result = service.import_file(caller.user_id, caller.group_id, _file_content(body), mapping, dry_run=body.dry_run)
        if body.dry_run:
            response.status_code = 200
        return _import(result)

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

    # W8 group merchant → category rules, the first layer of the hybrid categorizer. Every member
    # reads them; only an admin of the group creates, changes or deletes them (403 otherwise).
    @app.get("/v1/merchant-rules")
    def list_merchant_rules(caller: Caller) -> MerchantRulesOut:
        rules = service.list_merchant_rules(caller.user_id, caller.group_id)
        return MerchantRulesOut(rules=[_rule(r) for r in rules], categories=list(CATEGORIES))

    @app.post("/v1/merchant-rules", status_code=201)
    def create_merchant_rule(body: MerchantRuleIn, caller: Caller) -> MerchantRuleOut:
        return _rule(service.create_merchant_rule(caller.user_id, caller.group_id, body.merchant, body.category))

    @app.put("/v1/merchant-rules/{rule_id}")
    def update_merchant_rule(rule_id: int, body: MerchantRuleIn, caller: Caller) -> MerchantRuleOut:
        return _rule(
            service.update_merchant_rule(caller.user_id, caller.group_id, rule_id, body.merchant, body.category)
        )

    @app.delete("/v1/merchant-rules/{rule_id}")
    def delete_merchant_rule(rule_id: int, caller: Caller) -> MerchantRuleOut:
        """Deletes the rule and answers it as it was, so the screen can offer to add it back."""
        return _rule(service.delete_merchant_rule(caller.user_id, caller.group_id, rule_id))

    # W8 own accounts and counterparties: a new record naming one is a transfer within the group,
    # left out of the overview's totals. Every member reads the list; only an admin changes it.
    @app.get("/v1/own-accounts")
    def list_own_accounts(caller: Caller) -> OwnAccountsOut:
        accounts = service.list_own_accounts(caller.user_id, caller.group_id)
        return OwnAccountsOut(own_accounts=[_own_account(a) for a in accounts])

    @app.post("/v1/own-accounts", status_code=201)
    def create_own_account(body: OwnAccountIn, caller: Caller) -> OwnAccountOut:
        return _own_account(service.create_own_account(caller.user_id, caller.group_id, body.label))

    @app.delete("/v1/own-accounts/{account_id}")
    def delete_own_account(account_id: int, caller: Caller) -> OwnAccountOut:
        return _own_account(service.delete_own_account(caller.user_id, caller.group_id, account_id))

    @app.get("/v1/members")
    def list_members(caller: Caller) -> MembersOut:
        members = service.list_members(caller.user_id, caller.group_id)
        return MembersOut(members=[
            MemberOut(user_id=user_id, email=email, role=role, is_me=user_id == caller.user_id)
            for user_id, email, role in members
        ])

    # Changing a role widens access (a new admin), so like token management it works only from the web
    # session; an API token gets 403 even for an admin (least privilege, ADR 0012).
    @app.put("/v1/members/{member_id}/role")
    def set_member_role(member_id: str, body: MemberRoleIn, caller: Caller) -> MembersOut:
        """An admin changes a member's role; the group must keep at least one admin (else 409).
        Web session cookie only; an API token gets 403."""
        require_web_session(caller)
        service.set_member_role(caller.user_id, caller.group_id, member_id, body.role)
        return list_members(caller)

    # Token management (W8) works only with the web session cookie; an API token gets 403, so a leaked
    # phone token cannot issue new tokens. A member sees and revokes only their own tokens in this group.
    @app.get("/v1/tokens")
    def list_tokens(caller: Caller) -> TokensOut:
        """The signed-in member's API tokens in this group. Web session cookie only; an API token gets 403."""
        service.ensure_authorized(caller.user_id, caller.group_id)
        return TokensOut(tokens=[_token(t) for t in tokens.list_own(caller)])

    @app.post("/v1/tokens", status_code=201)
    def create_token(body: TokenIn, caller: Caller) -> CreatedTokenOut:
        """Issue an API token for the Android app or the Sheets script; it is shown only in this answer.
        Web session cookie only; an API token gets 403."""
        service.ensure_authorized(caller.user_id, caller.group_id)
        secret, record = tokens.create_own(caller, body.name)
        return CreatedTokenOut(token=secret, record=_token(record))

    @app.post("/v1/tokens/{token_id}/revoke")
    def revoke_token(token_id: int, caller: Caller) -> TokenOut:
        """Revoke one of the signed-in member's tokens. Web session cookie only; an API token gets 403."""
        service.ensure_authorized(caller.user_id, caller.group_id)
        record = tokens.revoke_own(caller, token_id)
        if record is None:
            raise NotFoundError("Token not found")
        return _token(record)

    @app.get("/v1/overview")
    def overview(caller: Caller, month: str | None = None) -> OverviewOut:
        result = service.overview(caller.user_id, caller.group_id, month)
        return OverviewOut(
            month=result.month,
            months=result.months,
            totals=[_bucket(b) for b in result.totals],
            categories=[_bucket(b) for b in result.categories],
            members=[_bucket(b) for b in result.members],
            transfer_count=result.transfer_count,
        )

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


def _session(record: WebSessionRecord, secret: str) -> SessionOut:
    return SessionOut(
        user_id=record.user_id,
        group_id=record.group_id,
        expires_at=record.expires_at.isoformat(),
        csrf_token=csrf_token(secret),
    )


def _file_content(body: ImportIn) -> str | bytes:
    if (body.content is None) == (body.xlsx_base64 is None):
        raise ValueError("Send exactly one of content (CSV) and xlsx_base64 (XLSX)")
    if body.content is not None:
        return body.content
    try:
        return base64.b64decode(body.xlsx_base64, validate=True)
    except binascii.Error as error:
        raise ValueError("xlsx_base64 is not valid base64") from error


def _import(result: ImportResult) -> ImportOut:
    summary: dict[str, int] = {}
    for item in result.results:
        summary[item.match_outcome] = summary.get(item.match_outcome, 0) + 1
    return ImportOut(
        import_batch_id=result.import_batch_id,
        already_imported=result.already_imported,
        rows=[
            ImportRowOut(
                line=row.line,
                happened_on=row.happened_on.isoformat(),
                amount=str(row.amount),
                currency=row.currency,
                description=row.description,
                merchant=row.merchant,
                reference=row.reference,
            )
            for row in result.rows
        ],
        errors=[RowErrorOut(line=error.line, error=error.error) for error in result.errors],
        results=[_result(item) for item in result.results],
        summary=summary,
    )


def _own_account(record: OwnAccountRecord) -> OwnAccountOut:
    return OwnAccountOut(
        id=record.id,
        label=record.label,
        kind=record.kind,
        match_key=record.match_key,
        created_by=record.created_by,
        created_at=record.created_at.isoformat(),
    )


def _rule(record: MerchantCategoryRecord) -> MerchantRuleOut:
    return MerchantRuleOut(
        id=record.id,
        merchant=record.merchant_label,
        merchant_key=record.merchant_key,
        category=record.category,
        created_by=record.created_by,
        created_at=record.created_at.isoformat(),
        updated_at=record.updated_at.isoformat(),
    )


def _token(record: ApiTokenRecord) -> TokenOut:
    return TokenOut(
        id=record.id,
        name=record.name,
        prefix=record.prefix,
        created_at=record.created_at.isoformat(),
        last_used_at=record.last_used_at.isoformat() if record.last_used_at else None,
        revoked_at=record.revoked_at.isoformat() if record.revoked_at else None,
    )


def _bucket(bucket: Bucket) -> OverviewBucketOut:
    return OverviewBucketOut(
        key=bucket.key,
        currency=bucket.currency,
        expense=str(bucket.expense),
        income=str(bucket.income),
        event_count=bucket.event_count,
        review_count=bucket.review_count,
        review_amount=str(bucket.review_amount),
    )


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


def run_server(host: str = "127.0.0.1", port: int = 8080, db: str = "finsync.db") -> None:
    import uvicorn

    storage = FinSyncStorage(db)
    # The URL may carry a database password; print it masked.
    print(f"FinSync API running on http://{host}:{port} (database: {storage.display_url}, docs: /docs)")
    uvicorn.run(create_app(storage), host=host, port=port)
