"""tira os controles redundantes do foco e abre a emissão em cone

Revision ID: 0033_light_emission_shape
Revises: 0032_vision_mode_preference

Duas colunas saem porque deixaram de significar coisas diferentes:

``opacity`` nasceu como "quanto da tinta colorida aparece", separada de
``intensity``, que era "quanto o foco levanta a escuridão". Depois que os dois
modos de visão passaram a apagar o polígono do foco igual e duro — para que
escolher a visão bonita nunca custasse área revelada —, intensidade parou de
mexer no recorte. Sobraram duas réguas multiplicando o mesmo alfa do halo.

``animated_core`` era um botão para deixar a tocha mais bonita, e virou condição
do modo: o miolo respira no cinematográfico e não existe no clássico, que não
tem efeito nenhum. Ninguém precisa escolher o que o modo já decide.

E entram ``angle`` e ``rotation``: até aqui todo foco emitia em círculo. Com
abertura e direção o mesmo foco vira lanterna, facho de porta entreaberta ou
holofote. 360 graus é o círculo de sempre, e é o padrão — nenhum foco existente
muda de aparência.

A lista de animações também cresce, e o CHECK precisa acompanhar: no SQLite ele
só muda recriando a tabela, então tudo acontece num batch com ``copy_from``.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0033_light_emission_shape"
down_revision = "0032_vision_mode_preference"
branch_labels = None
depends_on = None

_TABLE = "scene_lights"
_CHECK = "ck_scene_lights_animation"

_OLD_ANIMATIONS = ("none", "torch", "pulse")
_NEW_ANIMATIONS = ("none", "candle", "torch", "fire", "pulse", "arcane", "beacon")


def _in_clause(values: tuple[str, ...]) -> str:
    return "animation IN (" + ",".join(f"'{value}'" for value in values) + ")"


def _table(*, columns_present: set[str], check_clause: str) -> sa.Table:
    """A tabela como ela está AGORA, para o batch recriá-la sem perder nada.

    Precisa espelhar o que existe de fato, e não o que a versão anterior devia
    ter deixado: o banco chega aqui por mais de um caminho. Quem adota um banco
    legado cria as tabelas pelo metadata de hoje e só então roda as migrações
    desde o começo, de forma que ``angle`` já existe quando a 0027 e a 0028
    recolocam ``animated_core`` e ``opacity``.
    """
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


def _reshape(*, target: tuple[str, ...], drop: tuple[str, ...], add: dict) -> None:
    """Deixa a tabela na forma pedida, mexendo só no que está fora dela."""
    existing = _columns()
    if not existing:
        return

    to_drop = tuple(name for name in drop if name in existing)
    to_add = {name: build for name, build in add.items() if name not in existing}
    # A cláusula que está gravada, não a que a revisão anterior deveria ter
    # deixado: quem recria a tabela leva junto a constraint do ``copy_from``, e
    # passar uma lista fixa aqui rebaixaria um CHECK que já estava correto.
    current = _check_clause() or _in_clause(target)
    check_wrong = current != _in_clause(target)
    if not to_drop and not to_add and not check_wrong:
        return

    with op.batch_alter_table(
        _TABLE, copy_from=_table(columns_present=existing, check_clause=current)
    ) as batch:
        for name in to_drop:
            batch.drop_column(name)
        for build in to_add.values():
            batch.add_column(build())
        if check_wrong:
            batch.drop_constraint(op.f(_CHECK), type_="check")
            batch.create_check_constraint(op.f(_CHECK), _in_clause(target))


def upgrade() -> None:
    _reshape(
        target=_NEW_ANIMATIONS,
        drop=("opacity", "animated_core"),
        add={
            "angle": lambda: sa.Column(
                "angle", sa.Float(), nullable=False, server_default=sa.text("360.0")
            ),
            "rotation": lambda: sa.Column(
                "rotation", sa.Float(), nullable=False, server_default=sa.text("0.0")
            ),
        },
    )


def downgrade() -> None:
    # Emissão em cone não existe no esquema antigo, então um foco em facho volta a
    # iluminar em círculo. Animação nova idem: sem a lista, o CHECK barraria a
    # linha, então ela cai para a fixa antes de a coluna encolher.
    if _columns():
        op.get_bind().execute(
            sa.text(
                "UPDATE scene_lights SET animation = 'none' "
                "WHERE animation NOT IN ('none','torch','pulse')"
            )
        )
    _reshape(
        target=_OLD_ANIMATIONS,
        drop=("angle", "rotation"),
        add={
            "opacity": lambda: sa.Column(
                "opacity", sa.Float(), nullable=False, server_default=sa.text("1.0")
            ),
            "animated_core": lambda: sa.Column(
                "animated_core", sa.Integer(), nullable=False, server_default=sa.text("0")
            ),
        },
    )
