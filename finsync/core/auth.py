"""Per-user API tokens: issue, check and revoke.

A token belongs to one member of one group. The request's user and group come from the token,
never from headers the client sends. Only the SHA-256 hash of a token is stored; the token
itself is shown once, when it is created ([ADR 0009](../../docs/architecture/decisions/0009-api-tokens.md)).
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import secrets

from finsync.storage import ApiTokenRecord, FinSyncStorage

TOKEN_PREFIX = "fs_"
_TOKEN_BYTES = 32
# "fs_" plus the URL-safe base64 text of 32 random bytes (43 characters).
_TOKEN_FORMAT = re.compile(r"^fs_[A-Za-z0-9_-]{43}$")
_SHOWN_PREFIX_LENGTH = 8


class AuthenticationError(Exception):
    """Raised when a request carries no token, or one that is unknown or revoked."""


@dataclass(frozen=True)
class Principal:
    """Who is calling: the token's member and group."""

    user_id: str
    group_id: str
    token_id: int


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class TokenService:
    def __init__(self, storage: FinSyncStorage) -> None:
        self._storage = storage

    def create(self, user_id: str, group_id: str, name: str) -> tuple[str, ApiTokenRecord]:
        """Issue a token for a member of a group. The returned token is not stored and cannot be shown again."""
        user_id, group_id, name = user_id.strip(), group_id.strip(), name.strip()
        if not user_id or not group_id or not name:
            raise ValueError("user, group and name are required")
        if not self._storage.is_user_in_group(user_id, group_id):
            raise ValueError(f"{user_id} is not a member of {group_id}")
        token = TOKEN_PREFIX + secrets.token_urlsafe(_TOKEN_BYTES)
        token_id = self._storage.insert_api_token(
            user_id, group_id, name, hash_token(token), token[:_SHOWN_PREFIX_LENGTH]
        )
        record = next(item for item in self._storage.list_api_tokens(user_id) if item.id == token_id)
        return token, record

    def authenticate(self, authorization: str | None) -> Principal:
        """Resolve an ``Authorization: Bearer <token>`` header value to its member and group."""
        scheme, _, token = (authorization or "").strip().partition(" ")
        token = token.strip()
        if scheme.lower() != "bearer" or not token:
            raise AuthenticationError("An API token is required: Authorization: Bearer <token>")
        if not _TOKEN_FORMAT.match(token):
            raise AuthenticationError("Invalid API token")
        record = self._storage.find_api_token(hash_token(token))
        if record is None or record.revoked_at is not None:
            raise AuthenticationError("Invalid API token")
        self._storage.touch_api_token(record.id)
        return Principal(user_id=record.user_id, group_id=record.group_id, token_id=record.id)

    def revoke(self, token_id: int) -> bool:
        return self._storage.revoke_api_token(token_id)

    def list(self, user_id: str | None = None) -> list[ApiTokenRecord]:
        return self._storage.list_api_tokens(user_id)
