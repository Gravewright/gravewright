"""mais tipos de emissores de particulas

Revision ID: 0042_particle_kinds
Revises: 0041_shader_opacity
"""
from __future__ import annotations

from alembic import op

revision = "0042_particle_kinds"
down_revision = "0041_shader_opacity"
branch_labels = None
depends_on = None

_TABLE = "scene_particles"
_OLD = "kind IN ('smoke','ember','dust','arcane')"
_NEW = "kind IN ('smoke','ember','dust','arcane','rain','snow','firefly','leaves','bubbles','ash','blood','runes')"


def _replace(expression: str) -> None:
    # batch_alter_table recria a tabela no SQLite, onde CHECK nao pode ser
    # alterado diretamente, e usa ALTER apropriado nos demais bancos.
    with op.batch_alter_table(_TABLE) as batch:
        # op.f congela o nome ja convencionado; sem ele a naming_convention
        # prefixaria novamente para ck_scene_particles_ck_scene_particles_kind.
        batch.drop_constraint(op.f("ck_scene_particles_kind"), type_="check")
        batch.create_check_constraint("kind", expression)


def upgrade() -> None:
    _replace(_NEW)


def downgrade() -> None:
    # Linhas novas precisam voltar a um valor aceito antes do CHECK antigo.
    op.execute("UPDATE scene_particles SET kind='dust' WHERE kind NOT IN ('smoke','ember','dust','arcane')")
    _replace(_OLD)
