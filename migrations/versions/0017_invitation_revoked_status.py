"""invitation revoked status and canonical enum check names

Revision ID: 0017_invitation_revoked_status
Revises: 0016_enum_check_constraints
Create Date: 2026-08-04

Two schema fixes that both need the same table rebuilds (post-maintenance plan,
Etapa 1):

1. ``campaign_invitations.status`` accepts ``revoked``, so removing or banning a
   member can invalidate that member's still-pending invitations without
   pretending the invited user declined them.
2. The enum CHECK constraints added by ``0016`` land under doubled names
   (``ck_campaign_invitations_ck_campaign_invitations_status``) because the
   already-qualified name was passed through the ``ck_%(table_name)s_...``
   naming convention a second time. A database created from
   ``tables.metadata`` names them ``ck_campaign_invitations_status``, so the two
   creation paths drifted. They are renamed to the metadata form here, which is
   what the schema audit and ``grave db adopt`` compare against.

The ``_*_snapshot()`` tables mirror the schema exactly as of ``0016``. SQLite
cannot alter or rename a CHECK constraint in place, so alembic's batch mode
rebuilds each table from its snapshot; PostgreSQL/MySQL get plain DROP/ADD
CONSTRAINT statements and ignore the snapshot.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017_invitation_revoked_status"
down_revision = "0016_enum_check_constraints"
branch_labels = None
depends_on = None

_ROLE_VALUES = ("gm", "assistant_gm", "player", "streamer")
_OLD_STATUS_VALUES = ("pending", "accepted", "declined")
_NEW_STATUS_VALUES = ("pending", "accepted", "declined", "revoked")

# 0016 wrote these; the naming convention doubled the qualifier.
_LEGACY_MEMBER_ROLE_CK = "ck_campaign_members_ck_campaign_members_role"
_LEGACY_INVITATION_ROLE_CK = "ck_campaign_invitations_ck_campaign_invitations_role"
_LEGACY_INVITATION_STATUS_CK = "ck_campaign_invitations_ck_campaign_invitations_status"
_LEGACY_EFFECT_CK = "ck_campaign_permission_overrides_ck_campaign_permission_overrides_effect"


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    allowed = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({allowed})"


def _members_snapshot(role_check_name: str) -> sa.Table:
    return sa.Table(
        "campaign_members",
        sa.MetaData(),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=191), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_campaign_members"),
        sa.UniqueConstraint(
            "campaign_id", "user_id", name="uq_campaign_members_campaign_id_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name="fk_campaign_members_campaign_id_campaigns",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_campaign_members_user_id_users",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(_in_clause("role", _ROLE_VALUES), name=role_check_name),
        sa.Index("idx_campaign_members_campaign_id", "campaign_id"),
        sa.Index("idx_campaign_members_user_id", "user_id"),
    )


def _invitations_snapshot(
    *, role_check_name: str, status_check_name: str, status_values: tuple[str, ...]
) -> sa.Table:
    return sa.Table(
        "campaign_invitations",
        sa.MetaData(),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("invited_user_id", sa.String(length=64), nullable=False),
        sa.Column("invited_by_user_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=191), nullable=False),
        sa.Column("status", sa.String(length=191), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.Column("responded_at", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_campaign_invitations"),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name="fk_campaign_invitations_campaign_id_campaigns",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_user_id"],
            ["users.id"],
            name="fk_campaign_invitations_invited_by_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_user_id"],
            ["users.id"],
            name="fk_campaign_invitations_invited_user_id_users",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(_in_clause("role", _ROLE_VALUES), name=role_check_name),
        sa.CheckConstraint(_in_clause("status", status_values), name=status_check_name),
        sa.Index(
            "idx_campaign_invitations_invited_user_status",
            "invited_user_id",
            "status",
            "created_at",
        ),
        sa.Index(
            "idx_campaign_invitations_campaign_status",
            "campaign_id",
            "status",
            "created_at",
        ),
        sa.Index("idx_campaign_invitations_invited_by", "invited_by_user_id"),
    )


def _overrides_snapshot(effect_check_name: str) -> sa.Table:
    return sa.Table(
        "campaign_permission_overrides",
        sa.MetaData(),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("subject_type", sa.String(length=191), nullable=False),
        sa.Column("subject_id", sa.String(length=191), nullable=False),
        sa.Column("permission_key", sa.String(length=191), nullable=False),
        sa.Column("effect", sa.String(length=191), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_campaign_permission_overrides"),
        sa.UniqueConstraint(
            "campaign_id",
            "subject_type",
            "subject_id",
            "permission_key",
            name=(
                "uq_campaign_permission_overrides_campaign_id_subject_type"
                "_subject_id_permission_key"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaigns.id"],
            name="fk_campaign_permission_overrides_campaign_id_campaigns",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(_in_clause("effect", ("allow", "deny")), name=effect_check_name),
        sa.Index(
            "idx_campaign_permission_overrides_campaign_subject",
            "campaign_id",
            "subject_type",
            "subject_id",
        ),
        sa.Index("idx_campaign_permission_overrides_permission", "permission_key"),
    )


def _rename_check(table: sa.Table, *, old: str, new: str, condition: str) -> None:
    with op.batch_alter_table(table.name, copy_from=table) as batch:
        batch.drop_constraint(op.f(old), type_="check")
        batch.create_check_constraint(op.f(new), condition)


def upgrade() -> None:
    _rename_check(
        _members_snapshot(_LEGACY_MEMBER_ROLE_CK),
        old=_LEGACY_MEMBER_ROLE_CK,
        new="ck_campaign_members_role",
        condition=_in_clause("role", _ROLE_VALUES),
    )
    _rename_check(
        _overrides_snapshot(_LEGACY_EFFECT_CK),
        old=_LEGACY_EFFECT_CK,
        new="ck_campaign_permission_overrides_effect",
        condition=_in_clause("effect", ("allow", "deny")),
    )

    invitations = _invitations_snapshot(
        role_check_name=_LEGACY_INVITATION_ROLE_CK,
        status_check_name=_LEGACY_INVITATION_STATUS_CK,
        status_values=_OLD_STATUS_VALUES,
    )
    # One rebuild renames both invitation checks and widens the status set.
    with op.batch_alter_table("campaign_invitations", copy_from=invitations) as batch:
        batch.drop_constraint(op.f(_LEGACY_INVITATION_ROLE_CK), type_="check")
        batch.drop_constraint(op.f(_LEGACY_INVITATION_STATUS_CK), type_="check")
        batch.create_check_constraint(
            op.f("ck_campaign_invitations_role"), _in_clause("role", _ROLE_VALUES)
        )
        batch.create_check_constraint(
            op.f("ck_campaign_invitations_status"),
            _in_clause("status", _NEW_STATUS_VALUES),
        )


def downgrade() -> None:
    # No row is dropped: revoked invitations fold back into the closest legacy
    # state so the narrower CHECK can be restored.
    op.execute("UPDATE campaign_invitations SET status = 'declined' WHERE status = 'revoked'")

    invitations = _invitations_snapshot(
        role_check_name="ck_campaign_invitations_role",
        status_check_name="ck_campaign_invitations_status",
        status_values=_NEW_STATUS_VALUES,
    )
    with op.batch_alter_table("campaign_invitations", copy_from=invitations) as batch:
        batch.drop_constraint(op.f("ck_campaign_invitations_role"), type_="check")
        batch.drop_constraint(op.f("ck_campaign_invitations_status"), type_="check")
        batch.create_check_constraint(
            op.f(_LEGACY_INVITATION_ROLE_CK), _in_clause("role", _ROLE_VALUES)
        )
        batch.create_check_constraint(
            op.f(_LEGACY_INVITATION_STATUS_CK),
            _in_clause("status", _OLD_STATUS_VALUES),
        )

    _rename_check(
        _overrides_snapshot("ck_campaign_permission_overrides_effect"),
        old="ck_campaign_permission_overrides_effect",
        new=_LEGACY_EFFECT_CK,
        condition=_in_clause("effect", ("allow", "deny")),
    )
    _rename_check(
        _members_snapshot("ck_campaign_members_role"),
        old="ck_campaign_members_role",
        new=_LEGACY_MEMBER_ROLE_CK,
        condition=_in_clause("role", _ROLE_VALUES),
    )
