"""reconcilia a forma do foco em bancos que aplicaram a 0033 pela metade

Revision ID: 0034_light_emission_check_repair
Revises: 0033_light_emission_shape

A 0033 saiu numa primeira versão que acrescentava ``angle``/``rotation`` e
derrubava ``opacity``/``animated_core``, mas não mexia no CHECK de ``animation``.
Quem migrou naquele momento ficou com a tabela nova e a lista de emissões velha:
gravar uma vela ou um farol falha com ``CHECK constraint failed``.

Corrigir o arquivo da 0033 não resolve: Alembic não reaplica revisão já
carimbada, e o banco de quem migrou continua como estava. Reparo de migração
aplicada mora numa revisão nova; é o que esta é.

Ela é idempotente de propósito: num banco que já está na forma certa (instalação
nova, que aplicou a 0033 corrigida) não faz nada.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0034_light_emission_check_repair"
down_revision = "0033_light_emission_shape"
branch_labels = None
depends_on = None

_TABLE = "scene_lights"
_CHECK = "ck_scene_lights_animation"
_ANIMATIONS = ("none", "candle", "torch", "fire", "pulse", "arcane", "beacon")
_DROPPED = ("opacity", "animated_core")
_ADDED = {
    "angle": lambda: sa.Column(
        "angle", sa.Float(), nullable=False, server_default=sa.text("360.0")
    ),
    "rotation": lambda: sa.Column(
        "rotation", sa.Float(), nullable=False, server_default=sa.text("0.0")
    ),
}


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
    """A tabela como ela está agora, para o batch recriá-la sem perder nada."""
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
        "opacity": lambda: sa.Column(
            "opacity", sa.Float(), nullable=False, server_default=sa.text("1.0")
        ),
        "animated_core": lambda: sa.Column(
            "animated_core", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        **_ADDED,
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


def upgrade() -> None:
    existing = _columns()
    if not existing:
        return

    to_drop = tuple(name for name in _DROPPED if name in existing)
    to_add = {name: build for name, build in _ADDED.items() if name not in existing}
    # A cláusula gravada, não a que a revisão anterior deveria ter deixado: quem
    # recria a tabela leva junto a constraint do ``copy_from``.
    current = _check_clause() or _in_clause(_ANIMATIONS)
    check_wrong = current != _in_clause(_ANIMATIONS)

    if not to_drop and not to_add and not check_wrong:
        return

    with op.batch_alter_table(
        _TABLE, copy_from=_table(existing, current)
    ) as batch:
        for name in to_drop:
            batch.drop_column(name)
        for build in to_add.values():
            batch.add_column(build())
        if check_wrong:
            batch.drop_constraint(op.f(_CHECK), type_="check")
            batch.create_check_constraint(op.f(_CHECK), _in_clause(_ANIMATIONS))


def downgrade() -> None:
    # Nada a desfazer: esta revisão só termina o que a 0033 se propôs a fazer, e
    # voltar atrás é papel do downgrade dela.
    pass
