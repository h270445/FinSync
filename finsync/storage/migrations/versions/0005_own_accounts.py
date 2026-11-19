"""The group's own accounts and counterparties, for transfers within the group (W8).

A record that names one of them gets the direction and category `transfer` and is left out of the
overview's totals. `kind` is `account` (the key is the digits) or `name` (the key is normalised words).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "own_accounts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.Text, nullable=False),
        sa.Column("label", sa.Text, nullable=False),
        sa.Column("kind", sa.Text, nullable=False),
        sa.Column("match_key", sa.Text, nullable=False),
        sa.Column("created_by", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.UniqueConstraint("group_id", "kind", "match_key", name="uq_own_accounts_group_key"),
        sqlite_autoincrement=True,
    )


def downgrade() -> None:
    op.drop_table("own_accounts")
