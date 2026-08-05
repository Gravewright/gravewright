"""scene image gm-only layer flag

Revision ID: 0013_scene_image_gm_layer
Revises: 0012_library_assets
Create Date: 2026-06-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0013_scene_image_gm_layer"
down_revision = "0012_library_assets"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in sa.inspect(op.get_bind()).get_columns(table_name))


def upgrade() -> None:
    if _has_table("scene_image_placements") and not _has_column("scene_image_placements", "gm_only"):
        op.add_column(
            "scene_image_placements",
            sa.Column("gm_only", sa.Integer(), nullable=False, server_default=sa.text("0")),
        )


def downgrade() -> None:
    if _has_table("scene_image_placements") and _has_column("scene_image_placements", "gm_only"):
        op.drop_column("scene_image_placements", "gm_only")
