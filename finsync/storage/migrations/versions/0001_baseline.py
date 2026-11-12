"""Baseline: the schema of the last hand-written SQLite migration (version 4), on SQLite and PostgreSQL.

A SQLite file from before Alembic is upgraded to version 4 by FinSyncStorage and then stamped with this
revision, so both paths end in the same tables. Text columns hold decimals (exact) and UTC ISO instants.

Revision ID: 0001
Revises:
Create Date: 2026-11-12
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def _id() -> sa.Column:
    return sa.Column("id", sa.Integer, primary_key=True, autoincrement=True)


def upgrade() -> None:
    sqlite = op.get_bind().dialect.name == "sqlite"
    # AUTOINCREMENT on SQLite, as before: an id is never reused, even after the highest row is gone.
    table_options = {"sqlite_autoincrement": True}

    op.create_table(
        "group_memberships",
        sa.Column("user_id", sa.Text, primary_key=True),
        sa.Column("group_id", sa.Text, primary_key=True),
    )
    # transactions.event_id and events.primary_transaction_id point at each other. SQLite accepts the
    # forward reference inline; PostgreSQL gets the first foreign key once both tables exist.
    op.create_table(
        "transactions",
        _id(),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("group_id", sa.Text, nullable=False),
        sa.Column("amount", sa.Text, nullable=False),
        sa.Column("currency", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("merchant", sa.Text),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=False),
        sa.Column("happened_at", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("event_id", sa.Integer, sa.ForeignKey("events.id") if sqlite else None),
        sa.Column("direction", sa.Text),
        sa.Column("happened_at_precision", sa.Text, nullable=False, server_default="minute"),
        sa.Column("fingerprint", sa.Text),
        sa.Column("duplicate_of_id", sa.Integer, sa.ForeignKey("transactions.id")),
        sa.Column("raw_payload", sa.Text),
        sa.Column("source_ref", sa.Text),
        sa.Column("import_batch_id", sa.Text),
        **table_options,
    )
    op.create_table(
        "events",
        _id(),
        sa.Column("group_id", sa.Text, nullable=False),
        sa.Column("amount", sa.Text, nullable=False),
        sa.Column("currency", sa.Text, nullable=False),
        sa.Column("direction", sa.Text, nullable=False),
        sa.Column("happened_at", sa.Text, nullable=False),
        sa.Column("merchant", sa.Text),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("primary_transaction_id", sa.Integer, sa.ForeignKey("transactions.id")),
        sa.Column("review_state", sa.Text, nullable=False, server_default="clear"),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("updated_at", sa.Text, nullable=False),
        **table_options,
    )
    if not sqlite:
        op.create_foreign_key("transactions_event_id_fkey", "transactions", "events", ["event_id"], ["id"])
    op.create_table(
        "match_decisions",
        _id(),
        sa.Column("group_id", sa.Text, nullable=False),
        sa.Column("transaction_id", sa.Integer, sa.ForeignKey("transactions.id"), nullable=False),
        sa.Column("candidate_event_id", sa.Integer, sa.ForeignKey("events.id")),
        sa.Column("outcome", sa.Text, nullable=False),
        sa.Column("score", sa.Float),
        sa.Column("features", sa.Text),
        sa.Column("matcher_version", sa.Text, nullable=False),
        sa.Column("decided_by", sa.Text, nullable=False),
        sa.Column("supersedes_id", sa.Integer, sa.ForeignKey("match_decisions.id")),
        sa.Column("created_at", sa.Text, nullable=False),
        **table_options,
    )
    op.create_index("idx_transactions_candidates", "transactions", ["group_id", "currency", "happened_at"])
    op.create_index("idx_transactions_fingerprint", "transactions", ["group_id", "fingerprint"])
    op.create_index("idx_match_decisions_outcome", "match_decisions", ["group_id", "outcome"])
    op.create_table(
        "api_tokens",
        _id(),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("group_id", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("token_hash", sa.Text, nullable=False, unique=True),
        sa.Column("prefix", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("last_used_at", sa.Text),
        sa.Column("revoked_at", sa.Text),
        **table_options,
    )
    op.create_table(
        "member_accounts",
        sa.Column("user_id", sa.Text, primary_key=True),
        sa.Column("email", sa.Text, unique=True),
        sa.Column("password_hash", sa.Text),
        sa.Column("updated_at", sa.Text, nullable=False),
    )
    op.create_table(
        "web_sessions",
        _id(),
        sa.Column("user_id", sa.Text, nullable=False),
        sa.Column("group_id", sa.Text, nullable=False),
        sa.Column("session_hash", sa.Text, nullable=False, unique=True),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("expires_at", sa.Text, nullable=False),
        sa.Column("revoked_at", sa.Text),
        **table_options,
    )


def downgrade() -> None:
    raise NotImplementedError("the baseline is not downgraded; restore a backup instead")
