"""Add closed semantic wall channels and audience presentation.

Revision ID: 0052_geometry_semantic_channels
Revises: 0051_semantic_shader_presets
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0052_geometry_semantic_channels"
down_revision = "0051_semantic_shader_presets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    names = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("scene_walls")}
    with op.batch_alter_table("scene_walls") as batch:
        for name in ("movement_behavior", "vision_behavior", "light_behavior"):
            if name not in names: batch.add_column(sa.Column(name, sa.String(length=191), nullable=False, server_default="block"))
        if "presentation" not in names: batch.add_column(sa.Column("presentation", sa.String(length=191), nullable=False, server_default="normal"))
        if "discovered" not in names: batch.add_column(sa.Column("discovered", sa.Integer(), nullable=False, server_default="0"))
        for name in ("movement_behavior", "vision_behavior", "light_behavior"):
            batch.create_check_constraint(op.f(f"ck_scene_walls_{name}"), f"{name} IN ('block','pass')")
        batch.create_check_constraint(op.f("ck_scene_walls_presentation"), "presentation IN ('normal','window','bars','invisible','secret')")


def downgrade() -> None:
    names = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("scene_walls")}
    with op.batch_alter_table("scene_walls") as batch:
        batch.drop_constraint(op.f("ck_scene_walls_presentation"), type_="check")
        for name in ("light_behavior", "vision_behavior", "movement_behavior"):
            batch.drop_constraint(op.f(f"ck_scene_walls_{name}"), type_="check")
        for name in ("discovered", "presentation", "light_behavior", "vision_behavior", "movement_behavior"):
            if name in names: batch.drop_column(name)
