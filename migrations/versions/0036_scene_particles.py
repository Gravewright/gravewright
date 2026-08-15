"""separa efeito de cena de fonte de luz

Revision ID: 0036_scene_particles
Revises: 0035_smoke_replaces_beacon

Vela, fogueira, arcana e fumaça nunca foram maneiras de uma luz *iluminar* -
eram maneiras de uma cena ter vida. Estavam no foco de luz porque era o lugar que
existia, e o resultado é um editor cheio de controles que não acendem nada.

Fonte de luz fica com o que de fato muda a iluminação: chama irregular (tocha) e
respiração (pulso). O resto vira ``scene_particles``, que não emite luz nenhuma.

O que acontece com o que já está gravado:

  vela, fogueira  → tocha, que é a mesma chama em outro ritmo
  arcana          → pulso, que é a respiração que ela já tinha
  fumaça          → vira emissor de partícula e o foco some, porque ele já era
                    um foco que quase não iluminava; o brilho dele existia só
                    para segurar as partículas

Nada é apagado sem substituto: uma fumaça vira fumaça, no mesmo lugar, com o
alcance dela virando escala.
"""
from __future__ import annotations

import time
import uuid

import sqlalchemy as sa
from alembic import op

revision = "0036_scene_particles"
down_revision = "0035_smoke_replaces_beacon"
branch_labels = None
depends_on = None

_LIGHTS = "scene_lights"
_PARTICLES = "scene_particles"
_CHECK = "ck_scene_lights_animation"

_BEFORE = ("none", "candle", "torch", "fire", "pulse", "arcane", "smoke")
_AFTER = ("none", "torch", "pulse")
# Enquanto as linhas viajam de um conjunto para o outro, o CHECK precisa aceitar
# os dois: converter antes esbarra na constraint em vigor, e recriar antes
# esbarra nas linhas antigas durante a cópia.
_BOTH = tuple(dict.fromkeys(_BEFORE + _AFTER))


def _in_clause(values: tuple[str, ...]) -> str:
    return "animation IN (" + ",".join(f"'{value}'" for value in values) + ")"


def _columns(table: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _check_clause() -> str | None:
    inspector = sa.inspect(op.get_bind())
    for check in inspector.get_check_constraints(_LIGHTS):
        if check.get("name") == _CHECK:
            return str(check.get("sqltext") or "")
    return None


def _lights_table(columns_present: set[str], check_clause: str) -> sa.Table:
    columns = [
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("campaign_id", sa.String(64), nullable=False),
        sa.Column("scene_id", sa.String(64), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("bright_radius", sa.Float(), nullable=False, server_default=sa.text("2.0")),
        sa.Column("dim_radius", sa.Float(), nullable=False, server_default=sa.text("4.0")),
        sa.Column("color", sa.String(191), nullable=False, server_default=sa.text("'#ffd8a8'")),
        sa.Column("intensity", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("animation", sa.String(191), nullable=False, server_default=sa.text("'none'")),
        sa.Column("enabled", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by_user_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
    ]
    for name, build in {
        "angle": lambda: sa.Column(
            "angle", sa.Float(), nullable=False, server_default=sa.text("360.0")
        ),
        "rotation": lambda: sa.Column(
            "rotation", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
    }.items():
        if name in columns_present:
            columns.append(build())

    return sa.Table(
        _LIGHTS,
        sa.MetaData(),
        *columns,
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["campaigns.id"],
            name="fk_scene_lights_campaign_id_campaigns", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scene_id"], ["scenes.id"],
            name="fk_scene_lights_scene_id_scenes", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name="fk_scene_lights_created_by_user_id_users", ondelete="CASCADE",
        ),
        sa.CheckConstraint(check_clause, name=_CHECK),
        sa.Index("idx_scene_lights_scene", "scene_id", "created_at"),
    )


def _rebuild_check(clause: str) -> None:
    existing = _columns(_LIGHTS)
    if not existing:
        return
    current = _check_clause() or clause
    if current == clause:
        return
    with op.batch_alter_table(_LIGHTS, copy_from=_lights_table(existing, current)) as batch:
        batch.drop_constraint(op.f(_CHECK), type_="check")
        batch.create_check_constraint(op.f(_CHECK), clause)


def _create_particles() -> None:
    if _columns(_PARTICLES):
        return
    op.create_table(
        _PARTICLES,
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("campaign_id", sa.String(64), nullable=False),
        sa.Column("scene_id", sa.String(64), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("kind", sa.String(191), nullable=False, server_default=sa.text("'smoke'")),
        sa.Column("scale", sa.Float(), nullable=False, server_default=sa.text("3.0")),
        sa.Column("density", sa.Float(), nullable=False, server_default=sa.text("0.6")),
        sa.Column("color", sa.String(191), nullable=False, server_default=sa.text("'#9aa3ad'")),
        sa.Column("enabled", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_by_user_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["campaigns.id"],
            name="fk_scene_particles_campaign_id_campaigns", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scene_id"], ["scenes.id"],
            name="fk_scene_particles_scene_id_scenes", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name="fk_scene_particles_created_by_user_id_users", ondelete="CASCADE",
        ),
        # O nome vai curto: a convenção do metadata prefixa com ``ck_<tabela>_``, e
        # passar o nome já prefixado aqui produziria ck_scene_particles_ck_...
        sa.CheckConstraint("kind IN ('smoke','ember','dust','arcane')", name="kind"),
    )
    op.create_index("idx_scene_particles_scene", _PARTICLES, ["scene_id", "created_at"])


def upgrade() -> None:
    _create_particles()
    if not _columns(_LIGHTS):
        return

    bind = op.get_bind()
    _rebuild_check(_in_clause(_BOTH))

    # A fumaça mudou de tabela, não de existência: mesmo lugar, mesma cor, e o
    # alcance dela vira escala da coluna.
    now = int(time.time())
    for row in bind.execute(
        sa.text(
            "SELECT id, campaign_id, scene_id, x, y, dim_radius, color,"
            " created_by_user_id, enabled FROM scene_lights WHERE animation = 'smoke'"
        )
    ).mappings():
        bind.execute(
            sa.text(
                "INSERT INTO scene_particles (id, campaign_id, scene_id, x, y, kind,"
                " scale, density, color, enabled, created_by_user_id, created_at, updated_at)"
                " VALUES (:id, :campaign_id, :scene_id, :x, :y, 'smoke', :scale, 0.6,"
                " :color, :enabled, :author, :now, :now)"
            ),
            {
                "id": uuid.uuid4().hex,
                "campaign_id": row["campaign_id"],
                "scene_id": row["scene_id"],
                "x": row["x"],
                "y": row["y"],
                "scale": max(1.0, float(row["dim_radius"] or 3.0)),
                "color": row["color"],
                "enabled": row["enabled"],
                "author": row["created_by_user_id"],
                "now": now,
            },
        )
    bind.execute(sa.text("DELETE FROM scene_lights WHERE animation = 'smoke'"))

    # Vela e fogueira são a mesma chama em outro ritmo; arcana era respiração.
    bind.execute(
        sa.text("UPDATE scene_lights SET animation = 'torch' WHERE animation IN ('candle','fire')")
    )
    bind.execute(
        sa.text("UPDATE scene_lights SET animation = 'pulse' WHERE animation = 'arcane'")
    )

    _rebuild_check(_in_clause(_AFTER))


def downgrade() -> None:
    # As emissões voltam a ser aceitas, mas o que virou tocha não tem como saber
    # se era vela ou fogueira: a informação não existe mais na linha.
    _rebuild_check(_in_clause(_BEFORE))
    if _columns(_PARTICLES):
        op.drop_index("idx_scene_particles_scene", table_name=_PARTICLES)
        op.drop_table(_PARTICLES)
