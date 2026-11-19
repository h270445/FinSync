"""One category list: the nine categories of the labelled dataset (author's decision, 2026-11-19).

The keyword rules called one category `housing`; the allowed list, the merchant rules and the
categorization dataset call it `housing_utilities`. Stored records and events are renamed so that the
overview, the rules and the measurement count the same thing.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-19
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE transactions SET category = 'housing_utilities' WHERE category = 'housing'")
    op.execute("UPDATE events SET category = 'housing_utilities' WHERE category = 'housing'")


def downgrade() -> None:
    op.execute("UPDATE transactions SET category = 'housing' WHERE category = 'housing_utilities'")
    op.execute("UPDATE events SET category = 'housing' WHERE category = 'housing_utilities'")
