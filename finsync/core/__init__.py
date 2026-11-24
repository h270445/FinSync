"""Application core: use cases that combine ingestion, categorization, matching and storage."""

from finsync.core.auth import AuthenticationError, Principal, TokenService, WebSessionRequired, require_web_session
from finsync.core.service import (
    AuthorizationError,
    CategoryCorrection,
    ConflictError,
    FinSyncService,
    ImportResult,
    NotFoundError,
    ReviewItem,
    StoreResult,
    TransactionInput,
    is_uncertain,
    merchant_rule_offer,
)
from finsync.core.sessions import SessionService

__all__ = [
    "AuthenticationError",
    "AuthorizationError",
    "CategoryCorrection",
    "ConflictError",
    "FinSyncService",
    "ImportResult",
    "NotFoundError",
    "Principal",
    "ReviewItem",
    "SessionService",
    "StoreResult",
    "TokenService",
    "TransactionInput",
    "WebSessionRequired",
    "is_uncertain",
    "merchant_rule_offer",
    "require_web_session",
]
