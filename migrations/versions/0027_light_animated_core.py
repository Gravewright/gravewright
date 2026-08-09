"""pulsing core option for light sources

Revision ID: 0027_light_animated_core
Revises: 0026_lighting_sources_and_vision

O nucleo pulsante troca a textura de queda e recompoe a escuridao a cada quadro
de animacao. E o efeito mais bonito e o mais caro da camada, entao e opcional por
foco: o padrao 0 mantem o comportamento barato que ja existia.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0027_light_animated_core"
down_revision = "0026_lighting_sources_and_vision"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    return any(
        column["name"] == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def upgrade() -> None:
    if _has_table("scene_lights") and not _has_column("scene_lights", "animated_core"):
        op.add_column(
            "scene_lights",
            sa.Column("animated_core", sa.Integer(), server_default=sa.text("0"), nullable=False),
        )


def downgrade() -> None:
    if _has_table("scene_lights") and _has_column("scene_lights", "animated_core"):
        with op.batch_alter_table("scene_lights") as batch:
            batch.drop_column("animated_core")
