"""Add semantic identity and versions to scene shaders.

Revision ID: 0051_semantic_shader_presets
Revises: 0050_scene_image_versions
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0051_semantic_shader_presets"
down_revision = "0050_scene_image_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    names = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("scene_shaders")}
    if "preset_id" not in names:
        op.add_column("scene_shaders", sa.Column("preset_id", sa.String(length=191), nullable=True))
    if "preset_schema_version" not in names:
        op.add_column("scene_shaders", sa.Column("preset_schema_version", sa.Integer(), nullable=True))
    if "version" not in names:
        op.add_column("scene_shaders", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    names = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("scene_shaders")}
    for name in ("version", "preset_schema_version", "preset_id"):
        if name in names:
            op.drop_column("scene_shaders", name)
