"""Web app sign-in: member passwords and sessions.

The web app signs a member in with their e-mail address or member id (one field) and password and then works with an HttpOnly
session cookie; the Android app and scripts keep using API tokens ([ADR 0010](../../docs/architecture/decisions/0010-web-sign-in.md)).
Passwords are stored as salted scrypt hashes, sessions as the SHA-256 hash of a random secret.
A session belongs to one member of one group, like a token. State-changing requests made with the
cookie must also carry the session's CSRF token in a header, which a page on another site cannot read.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import re
import secrets

from finsync.core.auth import AuthenticationError, Principal
from finsync.core.service import AuthorizationError
from finsync.storage import FinSyncStorage, WebSessionRecord

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 256
SESSION_LIFETIME = timedelta(hours=12)
SESSION_PREFIX = "fss_"
_SESSION_FORMAT = re.compile(r"^fss_[A-Za-z0-9_-]{43}$")
# scrypt cost: one of the OWASP Password Storage Cheat Sheet settings (N=2^14, r=8, p=5): 16 MiB of memory.
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 5
_SIGN_IN_ERROR = "Wrong e-mail address, member id or password"
_EMAIL_FORMAT = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_EMAIL_LENGTH = 254


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(
            password.encode("utf-8"), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


_dummy_hashes: dict[tuple[int, int, int], str] = {}


def _dummy_hash() -> str:
    """Checked when the login is unknown, so a wrong login takes as long as a wrong password."""
    cost = (_SCRYPT_N, _SCRYPT_R, _SCRYPT_P)
    if cost not in _dummy_hashes:
        _dummy_hashes[cost] = hash_password(secrets.token_urlsafe(16))
    return _dummy_hashes[cost]


def csrf_token(session_secret: str) -> str:
    """The CSRF token of a session, derived from its secret, so it never has to be stored."""
    return hashlib.sha256(f"csrf:{session_secret}".encode("utf-8")).hexdigest()


def _hash_secret(session_secret: str) -> str:
    return hashlib.sha256(session_secret.encode("utf-8")).hexdigest()


class SessionService:
    def __init__(self, storage: FinSyncStorage, lifetime: timedelta = SESSION_LIFETIME) -> None:
        self._storage = storage
        self._lifetime = lifetime

    def set_password(self, user_id: str, password: str) -> None:
        """Set or replace a member's password. Every open web session of the member ends."""
        user_id = self._member(user_id)
        if not MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH:
            raise ValueError(f"the password must be {MIN_PASSWORD_LENGTH} to {MAX_PASSWORD_LENGTH} characters long")
        self._storage.set_member_password(user_id, hash_password(password))

    def set_email(self, user_id: str, email: str) -> str:
        """Set or replace a member's sign-in e-mail address; returns it normalised to lower case."""
        user_id, email = self._member(user_id), email.strip().lower()
        if len(email) > MAX_EMAIL_LENGTH or not _EMAIL_FORMAT.match(email):
            raise ValueError("not a valid e-mail address")
        self._storage.set_member_email(user_id, email)
        return email

    def _member(self, user_id: str) -> str:
        user_id = user_id.strip()
        if not user_id or not self._storage.list_member_groups(user_id):
            raise ValueError(f"{user_id or 'the member'} is not a member of any group")
        if "@" in user_id:
            raise ValueError("a member id with @ cannot sign in; the sign-in field reads it as an e-mail address")
        return user_id

    def sign_in(self, login: str, password: str, group_id: str | None = None) -> tuple[str, WebSessionRecord]:
        """Check the password and open a session for one of the member's groups.

        ``login`` is the member's e-mail address (any case) or member id. Returns the session secret
        (for the cookie; it is not stored) and the stored session. An unknown login, a member
        without a password and a wrong password get the same answer.
        """
        login = login.strip()
        found = self._storage.find_member_account(login.lower() if "@" in login else login) if login else None
        user_id, stored = found if found else ("", None)
        if len(password) > MAX_PASSWORD_LENGTH or not verify_password(password, stored or _dummy_hash()) or not stored:
            raise AuthenticationError(_SIGN_IN_ERROR)
        groups = self._storage.list_member_groups(user_id)
        if group_id is None or not group_id.strip():
            if not groups:
                raise AuthenticationError(_SIGN_IN_ERROR)
            if len(groups) > 1:
                raise ValueError("group_id is required: the member belongs to several groups")
            group_id = groups[0]
        group_id = group_id.strip()
        if group_id not in groups:
            raise AuthorizationError("User is not authorized for this group")
        secret = SESSION_PREFIX + secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + self._lifetime
        self._storage.insert_web_session(user_id, group_id, _hash_secret(secret), expires_at)
        record = self._storage.find_web_session(_hash_secret(secret))
        assert record is not None
        return secret, record

    def session(self, session_secret: str | None) -> WebSessionRecord:
        """The open session behind a cookie value."""
        secret = (session_secret or "").strip()
        if not _SESSION_FORMAT.match(secret):
            raise AuthenticationError("Sign in again: no valid session")
        record = self._storage.find_web_session(_hash_secret(secret))
        if record is None or record.revoked_at is not None or record.expires_at <= datetime.now(timezone.utc):
            raise AuthenticationError("Sign in again: no valid session")
        return record

    def authenticate(self, session_secret: str | None, csrf_header: str | None, state_changing: bool) -> Principal:
        """Resolve a session cookie to its member and group; state-changing requests also need the CSRF token."""
        record = self.session(session_secret)
        if state_changing and not hmac.compare_digest(
            (csrf_header or "").encode("utf-8"), csrf_token(str(session_secret).strip()).encode("utf-8")
        ):
            raise AuthorizationError("Missing or invalid CSRF token")
        return Principal(user_id=record.user_id, group_id=record.group_id, session_id=record.id)

    def sign_out(self, session_id: int) -> bool:
        return self._storage.revoke_web_session(session_id)
