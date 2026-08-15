"""add versioned virtual-raster scene metadata

Revision ID: 0044_virtual_raster_v2
Revises: 0043_ping_color_preference
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0044_virtual_raster_v2"
down_revision = "0043_ping_color_preference"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table in inspector.get_table_names() and column in {
        item["name"] for item in inspector.get_columns(table)
    }


def upgrade() -> None:
    if _has_column("scenes", "scene_format_version"):
        return
    op.add_column("scenes", sa.Column("grid_size", sa.Integer(), nullable=True))
    op.execute("UPDATE scenes SET grid_size = tile_size WHERE grid_size IS NULL")
    with op.batch_alter_table("scenes") as batch:
        batch.alter_column("grid_size", nullable=False, server_default="70")
        batch.add_column(sa.Column("scene_format_version", sa.Integer(), nullable=False, server_default="1"))

    with op.batch_alter_table("scene_layers") as batch:
        batch.add_column(sa.Column("max_lod", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("tile_index_version", sa.Integer(), nullable=False, server_default="1"))

    with op.batch_alter_table("scene_tiles") as batch:
        batch.add_column(sa.Column("lod", sa.Integer(), nullable=False, server_default="0"))
        batch.drop_index("idx_scene_tiles_layer_coord")
        batch.create_index("idx_scene_tiles_layer_lod_coord", ["layer_id", "lod", "tx", "ty"])

    with op.batch_alter_table("scene_chunks") as batch:
        batch.add_column(sa.Column("lod", sa.Integer(), nullable=False, server_default="0"))
        batch.drop_constraint("uq_scene_chunks_layer_id_cx_cy", type_="unique")
        batch.drop_index("idx_scene_chunks_scene_layer_coord")
        batch.create_unique_constraint("uq_scene_chunks_layer_lod_cx_cy", ["layer_id", "lod", "cx", "cy"])
        batch.create_index(
            "idx_scene_chunks_scene_layer_lod_coord",
            ["scene_id", "layer_id", "lod", "cx", "cy"],
        )


def downgrade() -> None:
    with op.batch_alter_table("scene_chunks") as batch:
        batch.drop_index("idx_scene_chunks_scene_layer_lod_coord")
        batch.drop_constraint("uq_scene_chunks_layer_lod_cx_cy", type_="unique")
        batch.create_unique_constraint("uq_scene_chunks_layer_id_cx_cy", ["layer_id", "cx", "cy"])
        batch.create_index("idx_scene_chunks_scene_layer_coord", ["scene_id", "layer_id", "cx", "cy"])
        batch.drop_column("lod")
    with op.batch_alter_table("scene_tiles") as batch:
        batch.drop_index("idx_scene_tiles_layer_lod_coord")
        batch.create_index("idx_scene_tiles_layer_coord", ["layer_id", "tx", "ty"])
        batch.drop_column("lod")
    with op.batch_alter_table("scene_layers") as batch:
        batch.drop_column("tile_index_version")
        batch.drop_column("max_lod")
    with op.batch_alter_table("scenes") as batch:
        batch.drop_column("scene_format_version")
        batch.drop_column("grid_size")
