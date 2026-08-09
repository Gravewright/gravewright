"""troca a emissão farol por fumaça

Revision ID: 0035_smoke_replaces_beacon
Revises: 0034_light_emission_check_repair

O farol saiu do conjunto: um facho varrendo é efeito de cena, não fonte de luz de
mesa, e ele competia com a atenção do mapa. No lugar entra a fumaça, que é o que
uma tocha ou fogueira produz de verdade.

Focos que já eram farol viram fumaça em vez de sumir: apagá-los deixaria buracos
escuros numa cena que o mestre já montou, e o alcance e a cor deles continuam
fazendo sentido para a luz nova.

A troca é feita em três passos, e não em dois: as duas ordens possíveis falham
por motivos simétricos — converter antes esbarra no CHECK em vigor, recriar
antes esbarra nas linhas antigas durante a cópia. Ver ``_swap``.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0035_smoke_replaces_beacon"
down_revision = "0034_light_emission_check_repair"
branch_labels = None
depends_on = None

_TABLE = "scene_lights"
_CHECK = "ck_scene_lights_animation"

_BEFORE = ("none", "candle", "torch", "fire", "pulse", "arcane", "beacon")
_AFTER = ("none", "candle", "torch", "fire", "pulse", "arcane", "smoke")


def _in_clause(values: tuple[str, ...]) -> str:
    return "animation IN (" + ",".join(f"'{value}'" for value in values) + ")"


def _columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(_TABLE)}


def _check_clause() -> str | None:
    inspector = sa.inspect(op.get_bind())
    for check in inspector.get_check_constraints(_TABLE):
        if check.get("name") == _CHECK:
            return str(check.get("sqltext") or "")
    return None


def _table(columns_present: set[str], check_clause: str) -> sa.Table:
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
    optional = {
        "angle": lambda: sa.Column(
            "angle", sa.Float(), nullable=False, server_default=sa.text("360.0")
        ),
        "rotation": lambda: sa.Column(
            "rotation", sa.Float(), nullable=False, server_default=sa.text("0.0")
        ),
    }
    for name, build in optional.items():
        if name in columns_present:
            columns.append(build())

    return sa.Table(
        _TABLE,
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
    existing = _columns()
    current = _check_clause() or clause
    if current == clause:
        return
    with op.batch_alter_table(_TABLE, copy_from=_table(existing, current)) as batch:
        batch.drop_constraint(op.f(_CHECK), type_="check")
        batch.create_check_constraint(op.f(_CHECK), clause)


def _swap(*, source: str, target: str, animations: tuple[str, ...]) -> None:
    """Troca uma emissão por outra sem que o CHECK barre o próprio caminho.

    Dois passos não bastam, e as duas ordens falham por motivos simétricos:

      converter antes    o CHECK em vigor ainda não conhece a emissão nova, e o
                         UPDATE é recusado;
      recriar antes      a tabela nova nasce com o CHECK final, e as linhas com a
                         emissão velha são recusadas durante a própria cópia.

    Então são três: alarga o CHECK para aceitar as duas, converte as linhas com
    folga, e só aí estreita para a lista final.
    """
    if not _columns():
        return

    both = tuple(dict.fromkeys(_BEFORE + _AFTER))
    _rebuild_check(_in_clause(both))

    op.get_bind().execute(
        sa.text(f"UPDATE {_TABLE} SET animation = :target WHERE animation = :source"),
        {"target": target, "source": source},
    )

    _rebuild_check(_in_clause(animations))


def upgrade() -> None:
    _swap(source="beacon", target="smoke", animations=_AFTER)


def downgrade() -> None:
    _swap(source="smoke", target="beacon", animations=_BEFORE)
