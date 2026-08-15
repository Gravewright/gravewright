"""locked door state for dynamic lighting

Revision ID: 0025_door_locked_state
Revises: 0024_scene_walls

Widens ``scene_walls.door_state`` from ('closed','open') to also allow 'locked'.
Existing rows are already inside the new set, so no data is rewritten going up.

SQLite cannot alter a CHECK in place, so alembic batch mode rebuilds the table.
The rebuild copies from ``_walls_snapshot()`` rather than from reflection because
SQLAlchemy does not reflect CHECK constraints on SQLite: reflecting would
silently drop ``ck_scene_walls_kind``. The snapshot mirrors the schema as of
``0024``. PostgreSQL/MySQL get plain DROP/ADD CONSTRAINT and ignore it.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0025_door_locked_state"
down_revision = "0024_scene_walls"
branch_labels = None
depends_on = None

ID = sa.String(length=64)
STR = sa.String(length=191)
DOOR_CK = "ck_scene_walls_door_state"
OLD_STATES = "door_state IN ('closed','open')"
NEW_STATES = "door_state IN ('closed','open','locked')"


def _walls_snapshot(door_states: str) -> sa.Table:
    return sa.Table(
        "scene_walls",
        sa.MetaData(),
        sa.Column("id", ID, nullable=False),
        sa.Column("campaign_id", ID, nullable=False),
        sa.Column("scene_id", ID, nullable=False),
        sa.Column("kind", STR, server_default=sa.text("'wall'"), nullable=False),
        sa.Column("door_state", STR, server_default=sa.text("'closed'"), nullable=False),
        sa.Column("x1", sa.Float(), nullable=False),
        sa.Column("y1", sa.Float(), nullable=False),
        sa.Column("x2", sa.Float(), nullable=False),
        sa.Column("y2", sa.Float(), nullable=False),
        sa.Column("created_by_user_id", ID, nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_scene_walls"),
        sa.CheckConstraint("kind IN ('wall','door')", name="ck_scene_walls_kind"),
        sa.CheckConstraint(door_states, name=DOOR_CK),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["campaigns.id"],
            name="fk_scene_walls_campaign_id_campaigns", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scene_id"], ["scenes.id"],
            name="fk_scene_walls_scene_id_scenes", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"],
            name="fk_scene_walls_created_by_user_id_users", ondelete="CASCADE",
        ),
        sa.Index("idx_scene_walls_scene", "scene_id", "created_at"),
    )


def _swap_door_check(*, copy_from: str, to: str) -> None:
    with op.batch_alter_table("scene_walls", copy_from=_walls_snapshot(copy_from)) as batch:
        batch.drop_constraint(op.f(DOOR_CK), type_="check")
        batch.create_check_constraint(op.f(DOOR_CK), to)


def upgrade() -> None:
    _swap_door_check(copy_from=OLD_STATES, to=NEW_STATES)


def downgrade() -> None:
    # Trancada vira fechada: ambas bloqueiam visao, entao nenhuma cena muda de
    # comportamento e nenhuma linha fica fora do dominio antigo.
    op.execute("UPDATE scene_walls SET door_state = 'closed' WHERE door_state = 'locked'")
    _swap_door_check(copy_from=NEW_STATES, to=OLD_STATES)
