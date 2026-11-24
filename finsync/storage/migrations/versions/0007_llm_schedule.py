"""The LLM layer in the live flow: the group's schedule setting, due times and a log of every call.

- `group_llm_settings` (one row per group; no row means the default): `mode` is `never` (default:
  nothing leaves the system), `after_arrival` (X hours after the record arrived), `daily` (at a set
  Budapest time) or `weekly` (on a set weekday and time); `monthly_budget_usd` stops the runs when the
  month's calls reach it.
- `events.llm_due_at`: when the scheduled run may ask the model about this uncertain event; cleared when
  the run or a member decides it.
- `events.category_agreement`: the share of the model's samples that agree with its answer (0..1),
  shown next to an `llm` category.
- `llm_calls`: who asked (`schedule` or a member), for which event, how many new calls, tokens and cost.
  It is both the cost guard's ledger and the record of what data left the system.
([design](../../../../docs/design/categorization.md#when-the-llm-is-called-proposed-by-the-author-2026-11-19))

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-24
"""

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "group_llm_settings",
        sa.Column("group_id", sa.Text, primary_key=True),
        sa.Column("mode", sa.Text, nullable=False, server_default="never"),
        sa.Column("hours_after", sa.Integer, nullable=False, server_default="24"),
        # Budapest wall-clock time "HH:MM" for the daily and weekly runs.
        sa.Column("run_time", sa.Text, nullable=False, server_default="20:00"),
        # 0 = Monday ... 6 = Sunday, for the weekly run.
        sa.Column("weekday", sa.Integer, nullable=False, server_default="6"),
        # Decimal as text, like amounts.
        sa.Column("monthly_budget_usd", sa.Text, nullable=False, server_default="1.00"),
        sa.Column("updated_by", sa.Text, nullable=False),
        sa.Column("updated_at", sa.Text, nullable=False),
    )
    op.add_column("events", sa.Column("llm_due_at", sa.Text))
    op.add_column("events", sa.Column("category_agreement", sa.Float))
    op.create_index("ix_events_llm_due", "events", ["llm_due_at"])
    op.create_table(
        "llm_calls",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.Text, nullable=False),
        sa.Column("event_id", sa.Integer, sa.ForeignKey("events.id"), nullable=False),
        sa.Column("requested_by", sa.Text, nullable=False),
        sa.Column("model", sa.Text, nullable=False),
        sa.Column("new_calls", sa.Integer, nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False),
        sa.Column("output_tokens", sa.Integer, nullable=False),
        sa.Column("cost_usd", sa.Text, nullable=False),
        sa.Column("created_at", sa.Text, nullable=False),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_llm_calls_group", "llm_calls", ["group_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_llm_calls_group", "llm_calls")
    op.drop_table("llm_calls")
    op.drop_index("ix_events_llm_due", "events")
    with op.batch_alter_table("events") as batch:
        batch.drop_column("category_agreement")
        batch.drop_column("llm_due_at")
    op.drop_table("group_llm_settings")
