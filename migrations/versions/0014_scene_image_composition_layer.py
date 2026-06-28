"""scene image composition layer

Revision ID: 0014_scene_image_composition
Revises: 0013_scene_image_gm_layer
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0014_scene_image_composition"
down_revision = "0013_scene_image_gm_layer"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in sa.inspect(op.get_bind()).get_columns(table_name))


def upgrade() -> None:
    if _has_table("scene_image_placements") and not _has_column("scene_image_placements", "layer"):
        op.add_column(
            "scene_image_placements",
            sa.Column("layer", sa.String(length=191), nullable=False, server_default=sa.text("'game'")),
        )
        op.execute(sa.text("UPDATE scene_image_placements SET layer = 'gm' WHERE gm_only = 1"))


def downgrade() -> None:
    if _has_table("scene_image_placements") and _has_column("scene_image_placements", "layer"):
        op.drop_column("scene_image_placements", "layer")
