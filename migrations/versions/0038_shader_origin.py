"""o shader ganha um lugar na cena

Revision ID: 0038_shader_origin
Revises: 0037_scene_shaders

Um shader sem origem só sabe ser clima: ele cobre a tela inteira e pronto. Isso
serve para chuva e granulado, e não serve para a fogueira que fumega naquele
canto — que é justamente o efeito que dá sentido a uma cena.

O passe continua sendo de tela, porque é o que um filtro sabe fazer. O que muda é
que ele passa a *receber onde fica*: origem em coordenadas de mundo e raio em
células, os mesmos que o foco de luz e o emissor de partícula já usam.

``radius`` zero mantém o que existe hoje — cena inteira —, então o que já estava
gravado continua exatamente como estava.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0038_shader_origin"
down_revision = "0037_scene_shaders"
branch_labels = None
depends_on = None

_TABLE = "scene_shaders"
_COLUMNS = (
    ("x", sa.Column("x", sa.Float(), nullable=False, server_default=sa.text("0.0"))),
    ("y", sa.Column("y", sa.Float(), nullable=False, server_default=sa.text("0.0"))),
    ("radius", sa.Column("radius", sa.Float(), nullable=False, server_default=sa.text("0.0"))),
)


def _existing() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(_TABLE)}


def upgrade() -> None:
    present = _existing()
    if not present:
        return
    for name, column in _COLUMNS:
        if name not in present:
            op.add_column(_TABLE, column)


def downgrade() -> None:
    present = _existing()
    for name, _column in reversed(_COLUMNS):
        if name in present:
            op.drop_column(_TABLE, name)
