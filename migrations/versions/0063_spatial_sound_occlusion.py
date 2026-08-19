"""Persist optional wall and door occlusion for spatial sounds.

Revision ID: 0063_spatial_sound_occlusion
Revises: 0062_scene_sound_cas
"""
from alembic import op
import sqlalchemy as sa

revision = "0063_spatial_sound_occlusion"
down_revision = "0062_scene_sound_cas"
branch_labels = None
depends_on = None


def _has_column(table: str, name: str) -> bool:
    return any(column["name"] == name for column in sa.inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    if not _has_column("scene_spatial_sounds", "constrained_by_walls"):
        with op.batch_alter_table("scene_spatial_sounds") as batch:
            batch.add_column(sa.Column("constrained_by_walls", sa.Integer, nullable=False, server_default="1"))


def downgrade() -> None:
    if _has_column("scene_spatial_sounds", "constrained_by_walls"):
        with op.batch_alter_table("scene_spatial_sounds") as batch:
            batch.drop_column("constrained_by_walls")
