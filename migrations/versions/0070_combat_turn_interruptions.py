"""Persist resumable combat turn interruptions.

Revision ID: 0070_combat_turn_interruptions
Revises: 0069_fractional_grid_size
"""
from alembic import op
import sqlalchemy as sa


revision = "0070_combat_turn_interruptions"
down_revision = "0069_fractional_grid_size"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    return any(
        column["name"] == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def upgrade() -> None:
    if _has_column("combat_encounters", "interrupted_turn_index"):
        return
    with op.batch_alter_table("combat_encounters") as batch:
        batch.add_column(sa.Column("interrupted_turn_index", sa.Integer(), nullable=True))


def downgrade() -> None:
    if not _has_column("combat_encounters", "interrupted_turn_index"):
        return
    with op.batch_alter_table("combat_encounters") as batch:
        batch.drop_column("interrupted_turn_index")
