"""guarda a qualidade da visão dinâmica escolhida por cada pessoa

Revision ID: 0032_vision_mode_preference
Revises: 0031_token_bar_slots

A visão dinâmica passou a ter dois modos: ``classic``, de borda dura e sem
halo, e ``cinematic``, com penumbra, brilho e filtros. Qual deles roda não é
propriedade da campanha — a mesma cena é desenhada no notebook fraco de um
jogador e na máquina do mestre —, então a escolha mora ao lado do modo de
interface, em ``user_preferences``.

O padrão é ``cinematic`` porque é o que todo mundo já via antes desta coluna
existir: quem não escolher nada não deve perceber mudança nenhuma.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0032_vision_mode_preference"
down_revision = "0031_token_bar_slots"
branch_labels = None
depends_on = None

_TABLE = "user_preferences"
_COLUMN = "vision_mode"


def _has_column() -> bool:
    inspector = sa.inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        return True
    return any(column["name"] == _COLUMN for column in inspector.get_columns(_TABLE))


def upgrade() -> None:
    if _has_column():
        return
    op.add_column(
        _TABLE,
        sa.Column(
            _COLUMN,
            sa.String(length=191),
            nullable=False,
            server_default=sa.text("'cinematic'"),
        ),
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        return
    if not any(column["name"] == _COLUMN for column in inspector.get_columns(_TABLE)):
        return
    op.drop_column(_TABLE, _COLUMN)
