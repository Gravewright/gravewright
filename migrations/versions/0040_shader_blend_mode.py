"""modo de composicao dos shaders de cena

Revision ID: 0040_shader_blend_mode
Revises: 0039_shader_rotation
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0040_shader_blend_mode"
down_revision = "0039_shader_rotation"
branch_labels = None
depends_on = None

_TABLE = "scene_shaders"
_COLUMN = "blend_mode"


def _columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(_TABLE)}


def upgrade() -> None:
    present = _columns()
    if present and _COLUMN not in present:
        op.add_column(_TABLE, sa.Column(_COLUMN, sa.String(length=191), nullable=False,
                                        server_default=sa.text("'normal'")))


def downgrade() -> None:
    if _COLUMN in _columns():
        op.drop_column(_TABLE, _COLUMN)
