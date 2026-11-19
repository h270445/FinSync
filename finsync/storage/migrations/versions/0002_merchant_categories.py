"""Group merchant → category rules: the first, deterministic layer of the hybrid categorizer (W8).

One row per group and merchant key. A member adds, changes or deletes them on the W8 settings screen;
later, category corrections will add and confirm rows (`times_confirmed`). The key is the merchant name
as `merchant_key()` normalises it (lowercase, accent-free words without store numbers and legal suffixes).

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "merchant_categories",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.Text, nullable=False),
        sa.Column("merchant_key", sa.Text, nullable=False),
        # What the member typed, for display ("SPAR"); the key is what is matched.
        sa.Column("merchant_label", sa.Text, nullable=False),
        sa.Column("category", sa.Text, nullable=False),
        sa.Column("times_confirmed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sa.Column("updated_at", sa.Text, nullable=False),
        sa.UniqueConstraint("group_id", "merchant_key", name="uq_merchant_categories_group_key"),
        sqlite_autoincrement=True,
    )


def downgrade() -> None:
    op.drop_table("merchant_categories")
