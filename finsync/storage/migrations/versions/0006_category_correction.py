"""Category correction: where a category came from, the "mixed" flag, category lines and the change log.

- `transactions` and `events` get `category_source` (who decided: `user`, `merchant_rule`, `dictionary`,
  `keyword`, `llm`, `own_account`, `none`) and `category_confidence` (`high` or `low`). An event decided
  by a member (`user`) keeps its category when records are linked to it or split from it.
- `events.mixed` (0 or 1): a member says the purchase was of several kinds without giving amounts.
- `event_category_lines`: a member splits an event's amount into categories; the lines add up to the
  event's amount and have its sign. They belong to the event, not to a source record.
- `category_changes`: append-only log of every manual change (who, kind, old, new, when), like
  `match_decisions` for matching.

Existing rows did not record where their category came from: they get `none`/`low` (shown as a
suggestion), except transfers, which came from the group's own-accounts list (`own_account`/`high`).
([design](../../../../docs/design/categorization.md#mixed-baskets))

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-24
"""

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("transactions", "events"):
        op.add_column(table, sa.Column("category_source", sa.Text, nullable=False, server_default="none"))
        op.add_column(table, sa.Column("category_confidence", sa.Text, nullable=False, server_default="low"))
        op.execute(
            f"UPDATE {table} SET category_source = 'own_account', category_confidence = 'high' "
            "WHERE category = 'transfer'"
        )
    op.add_column("events", sa.Column("mixed", sa.Integer, nullable=False, server_default="0"))
    op.create_table(
        "event_category_lines",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.Text, nullable=False),
        sa.Column("event_id", sa.Integer, sa.ForeignKey("events.id"), nullable=False),
        sa.Column("category", sa.Text, nullable=False),
        # Decimal as text, with the event's sign, like every other amount.
        sa.Column("amount", sa.Text, nullable=False),
        sa.Column("created_by", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_event_category_lines_event", "event_category_lines", ["event_id"])
    op.create_table(
        "category_changes",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.Text, nullable=False),
        sa.Column("event_id", sa.Integer, sa.ForeignKey("events.id"), nullable=False),
        # `category`, `mixed`, `lines` or `transfer`.
        sa.Column("kind", sa.Text, nullable=False),
        # JSON of the value before and after the change.
        sa.Column("old_value", sa.Text),
        sa.Column("new_value", sa.Text),
        sa.Column("changed_by", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_category_changes_event", "category_changes", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_category_changes_event", "category_changes")
    op.drop_table("category_changes")
    op.drop_index("ix_event_category_lines_event", "event_category_lines")
    op.drop_table("event_category_lines")
    with op.batch_alter_table("events") as batch:
        batch.drop_column("mixed")
        batch.drop_column("category_confidence")
        batch.drop_column("category_source")
    with op.batch_alter_table("transactions") as batch:
        batch.drop_column("category_confidence")
        batch.drop_column("category_source")
