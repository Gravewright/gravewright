"""store initiative as text and move the ordering key to sort_value

Revision ID: 0030_combat_initiative_text
Revises: 0029_simplify_combat

``0029`` left initiative as a float, which quietly made the core assume every
game ranks turns by a number it can compare. It does not: a table may track the
order with a drawn card, a named phase, or a word the GM types off a sheet.

So the value the table sees becomes text the core never parses, and the single
thing ordering reads moves to ``sort_value`` — the parsed number for systems
that count, or the hand-arranged position for systems that do not.

The old numeric initiative becomes both: it keeps ordering as ``sort_value`` and
is rendered into ``initiative`` as the text it always displayed.

Idempotent: a database that already has ``sort_value`` is left alone.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0030_combat_initiative_text"
down_revision = "0029_simplify_combat"
branch_labels = None
depends_on = None

# SQLite renders 18.0 as "18.0"; the table always saw "18".
_BACKFILL = sa.text(
    "UPDATE combat_combatants SET initiative = "
    "CASE WHEN sort_value IS NULL THEN NULL "
    "WHEN sort_value = CAST(sort_value AS INTEGER) "
    "THEN CAST(CAST(sort_value AS INTEGER) AS TEXT) "
    "ELSE CAST(sort_value AS TEXT) END"
)


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    if "combat_combatants" not in sa.inspect(op.get_bind()).get_table_names():
        return
    existing = _columns("combat_combatants")
    if "sort_value" in existing:
        return

    with op.batch_alter_table("combat_combatants") as batch:
        if "initiative" in existing:
            batch.alter_column(
                "initiative", new_column_name="sort_value", existing_type=sa.Float()
            )
        else:
            batch.add_column(sa.Column("sort_value", sa.Float(), nullable=True))

    op.add_column(
        "combat_combatants", sa.Column("initiative", sa.String(length=191), nullable=True)
    )
    op.execute(_BACKFILL)


def downgrade() -> None:
    """Back to a numeric initiative. Values that were never numbers are lost."""
    if "combat_combatants" not in sa.inspect(op.get_bind()).get_table_names():
        return
    if "sort_value" not in _columns("combat_combatants"):
        return

    with op.batch_alter_table("combat_combatants") as batch:
        batch.drop_column("initiative")
        batch.alter_column(
            "sort_value", new_column_name="initiative", existing_type=sa.Float()
        )
