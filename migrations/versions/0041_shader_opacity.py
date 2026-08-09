"""opacidade independente dos shaders de cena

Revision ID: 0041_shader_opacity
Revises: 0040_shader_blend_mode
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0041_shader_opacity"
down_revision = "0040_shader_blend_mode"
branch_labels = None
depends_on = None

_TABLE = "scene_shaders"
_COLUMN = "opacity"


def _columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(_TABLE)}


def upgrade() -> None:
    present = _columns()
    if present and _COLUMN not in present:
        op.add_column(_TABLE, sa.Column(_COLUMN, sa.Float(), nullable=False,
                                        server_default=sa.text("1.0")))


def downgrade() -> None:
    if _COLUMN in _columns():
        op.drop_column(_TABLE, _COLUMN)
