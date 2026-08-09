"""giro do shader

Revision ID: 0039_shader_rotation
Revises: 0038_shader_origin

Escala e velocidade não dão direção. Chuva torta, varredura de facho e faixa de
poeira precisam de um ângulo, e sem ele o único jeito de girar um efeito era
reescrever o GLSL — o que transforma um botão em trabalho de programação.

Zero é o que já existia, então nada muda para o que está gravado.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0039_shader_rotation"
down_revision = "0038_shader_origin"
branch_labels = None
depends_on = None

_TABLE = "scene_shaders"
_COLUMN = "rotation"


def _columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(_TABLE)}


def upgrade() -> None:
    present = _columns()
    if present and _COLUMN not in present:
        op.add_column(_TABLE, sa.Column(_COLUMN, sa.Float(), nullable=False, server_default=sa.text("0.0")))


def downgrade() -> None:
    if _COLUMN in _columns():
        op.drop_column(_TABLE, _COLUMN)
