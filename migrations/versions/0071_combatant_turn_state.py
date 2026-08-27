"""Persist combatant acted/holding state.

Revision ID: 0071_combatant_turn_state
Revises: 0070_combat_turn_interruptions
"""
from alembic import op
import sqlalchemy as sa


revision = "0071_combatant_turn_state"
down_revision = "0070_combat_turn_interruptions"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in sa.inspect(op.get_bind()).get_columns(table_name))


def upgrade() -> None:
    with op.batch_alter_table("combat_combatants") as batch:
        if not _has_column("combat_combatants", "acted_round"):
            batch.add_column(sa.Column("acted_round", sa.Integer(), nullable=False, server_default="0"))
        if not _has_column("combat_combatants", "holding"):
            batch.add_column(sa.Column("holding", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("combat_combatants") as batch:
        if _has_column("combat_combatants", "holding"):
            batch.drop_column("holding")
        if _has_column("combat_combatants", "acted_round"):
            batch.drop_column("acted_round")
