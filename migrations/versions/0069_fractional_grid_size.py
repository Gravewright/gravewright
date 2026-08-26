"""Preserve fractional calibrated grid sizes without accumulated drift.

Revision ID: 0069_fractional_grid_size
Revises: 0068_scene_grid_offsets
"""
from alembic import op
import sqlalchemy as sa

revision = "0069_fractional_grid_size"
down_revision = "0068_scene_grid_offsets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("scenes") as batch:
        batch.alter_column("grid_size", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("scenes") as batch:
        batch.alter_column("grid_size", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=False)
