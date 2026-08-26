"""Persist the visual origin of a calibrated scene grid.

Revision ID: 0068_scene_grid_offsets
Revises: 0067_free_token_position
"""
from alembic import op
import sqlalchemy as sa

revision = "0068_scene_grid_offsets"
down_revision = "0067_free_token_position"
branch_labels = None
depends_on = None


def _has_column(name: str) -> bool:
    return any(column["name"] == name for column in sa.inspect(op.get_bind()).get_columns("scenes"))


def upgrade() -> None:
    if not _has_column("grid_offset_x"):
        op.add_column("scenes", sa.Column("grid_offset_x", sa.Float(), nullable=False, server_default="0.0"))
    if not _has_column("grid_offset_y"):
        op.add_column("scenes", sa.Column("grid_offset_y", sa.Float(), nullable=False, server_default="0.0"))


def downgrade() -> None:
    if _has_column("grid_offset_y"):
        op.drop_column("scenes", "grid_offset_y")
    if _has_column("grid_offset_x"):
        op.drop_column("scenes", "grid_offset_x")
