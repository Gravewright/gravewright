"""light sources, scene darkness and per-token vision

Revision ID: 0026_lighting_sources_and_vision
Revises: 0025_door_locked_state

Three additions that together make dynamic lighting playable rather than just
drawable:

* ``scenes.darkness`` (0..1): how dark the unlit area of the scene is. 0 keeps
  the previous behaviour of a fully lit map for everyone.
* ``tokens.vision_enabled`` / ``tokens.vision_range``: per-token sight, so each
  player sees from the tokens they control. ``vision_range`` is in grid cells;
  0 means "as far as the walls allow", which is what tokens did before.
* ``scene_lights``: placed light sources with a bright/dim falloff and an
  optional 'torch' or 'pulse' animation.

Defaults are chosen so existing scenes render exactly as they did before this
revision: darkness 0 lights everything, and vision_enabled 1 with range 0
reproduces the old unlimited line of sight.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0026_lighting_sources_and_vision"
down_revision = "0025_door_locked_state"
branch_labels = None
depends_on = None

ID = sa.String(length=64)
STR = sa.String(length=191)


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    return any(
        column["name"] == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def _add_column(table_name: str, column: sa.Column) -> None:
    if _has_table(table_name) and not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def upgrade() -> None:
    _add_column("scenes", sa.Column("darkness", sa.Float(), server_default=sa.text("0.0"), nullable=False))
    _add_column("tokens", sa.Column("vision_enabled", sa.Integer(), server_default=sa.text("1"), nullable=False))
    _add_column("tokens", sa.Column("vision_range", sa.Float(), server_default=sa.text("0.0"), nullable=False))

    if _has_table("scene_lights"):
        return
    op.create_table("scene_lights",
        sa.Column("id", ID, nullable=False),
        sa.Column("campaign_id", ID, nullable=False),
        sa.Column("scene_id", ID, nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("bright_radius", sa.Float(), server_default=sa.text("2.0"), nullable=False),
        sa.Column("dim_radius", sa.Float(), server_default=sa.text("4.0"), nullable=False),
        sa.Column("color", STR, server_default=sa.text("'#ffd8a8'"), nullable=False),
        sa.Column("intensity", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("animation", STR, server_default=sa.text("'none'"), nullable=False),
        sa.Column("enabled", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_user_id", ID, nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.CheckConstraint("animation IN ('none','torch','pulse')", name="animation"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"))
    op.create_index("idx_scene_lights_scene", "scene_lights", ["scene_id", "created_at"])


def downgrade() -> None:
    if _has_table("scene_lights"):
        op.drop_index("idx_scene_lights_scene", table_name="scene_lights")
        op.drop_table("scene_lights")
    for table_name, columns in (("tokens", ("vision_range", "vision_enabled")), ("scenes", ("darkness",))):
        present = [c for c in columns if _has_table(table_name) and _has_column(table_name, c)]
        if not present:
            continue
        with op.batch_alter_table(table_name) as batch:
            for column in present:
                batch.drop_column(column)
