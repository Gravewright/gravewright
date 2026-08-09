"""separate glow opacity for light sources

Revision ID: 0028_light_opacity
Revises: 0027_light_animated_core

``intensity`` diz quanto o foco levanta a escuridao; ``opacity`` diz quanto o
brilho colorido aparece por cima do mapa. Eram a mesma coisa, entao nao havia
como ter um foco que ilumina bastante com tinta discreta — ou o contrario.

Padrao 1.0 reproduz exatamente o brilho anterior.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0028_light_opacity"
down_revision = "0027_light_animated_core"
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
    if _has_table("scene_lights") and not _has_column("scene_lights", "opacity"):
        op.add_column(
            "scene_lights",
            sa.Column("opacity", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        )


def downgrade() -> None:
    if _has_table("scene_lights") and _has_column("scene_lights", "opacity"):
        with op.batch_alter_table("scene_lights") as batch:
            batch.drop_column("opacity")
