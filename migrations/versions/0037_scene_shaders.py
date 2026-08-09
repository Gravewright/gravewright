"""shaders de cena escritos pelo mestre

Revision ID: 0037_scene_shaders
Revises: 0036_scene_particles

Partícula é efeito pronto: o mestre escolhe fumaça e recebe fumaça. Shader é o
contrário — ele descreve o efeito que ninguém previu, e por isso o texto GLSL
precisa de um lugar para morar junto da cena.

Quem escreve é só o mestre da mesa. O texto nunca é executado no servidor; ele
viaja até a GPU de quem está jogando. A tabela guarda o texto e os quatro botões
que viram uniform (intensidade, escala, velocidade, cor) — o shader não escolhe
o que recebe, senão cada um viraria uma API diferente.

Nada é migrado: a tabela nasce vazia.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0037_scene_shaders"
down_revision = "0036_scene_particles"
branch_labels = None
depends_on = None

_TABLE = "scene_shaders"


def upgrade() -> None:
    if _TABLE in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        _TABLE,
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("campaign_id", sa.String(length=64), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scene_id", sa.String(length=64), sa.ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=191), nullable=False, server_default=sa.text("''")),
        sa.Column("source", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("intensity", sa.Float(), nullable=False, server_default=sa.text("0.6")),
        sa.Column("scale", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("speed", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("color", sa.String(length=191), nullable=False, server_default=sa.text("'#8fb6ff'")),
        sa.Column("enabled", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by_user_id", sa.String(length=64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
    )
    op.create_index("idx_scene_shaders_scene", _TABLE, ["scene_id", "created_at"])


def downgrade() -> None:
    if _TABLE not in sa.inspect(op.get_bind()).get_table_names():
        return
    op.drop_index("idx_scene_shaders_scene", table_name=_TABLE)
    op.drop_table(_TABLE)
