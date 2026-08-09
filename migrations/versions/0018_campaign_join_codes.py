"""campaign join codes and redemption receipts

Revision ID: 0018_campaign_join_codes
Revises: 0017_invitation_revoked_status
Create Date: 2026-08-05

Static DDL for the reusable player join-code feature. Downgrade removes join-code
data, so operators must back up before downgrading across this revision.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_campaign_join_codes"
down_revision = "0017_invitation_revoked_status"
branch_labels = None
depends_on = None

ID = sa.String(length=64)
STR = sa.String(length=191)



def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()

def upgrade() -> None:
    # Reentrante por tabela: um banco que ja tem uma delas so pula aquele bloco.
    if not _has_table("campaign_join_codes"):
        op.create_table(
            "campaign_join_codes",
            sa.Column("id", ID, nullable=False),
            sa.Column("campaign_id", ID, nullable=False),
            sa.Column("code_hash", sa.String(length=64), nullable=False),
            sa.Column("created_by_user_id", ID, nullable=False),
            sa.Column("role", STR, server_default=sa.text("'player'"), nullable=False),
            sa.Column("max_uses", sa.Integer(), nullable=True),
            sa.Column("use_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
            sa.Column("expires_at", sa.Integer(), nullable=False),
            sa.Column("revoked_at", sa.Integer(), nullable=True),
            sa.Column("last_used_at", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.Integer(), nullable=False),
            sa.Column("updated_at", sa.Integer(), nullable=False),
            sa.CheckConstraint("role = 'player'", name=op.f("ck_campaign_join_codes_role_player")),
            sa.CheckConstraint(
                "use_count >= 0", name=op.f("ck_campaign_join_codes_use_count_nonnegative")
            ),
            sa.CheckConstraint(
                "max_uses IS NULL OR max_uses > 0",
                name=op.f("ck_campaign_join_codes_max_uses_positive"),
            ),
            sa.ForeignKeyConstraint(
                ["campaign_id"],
                ["campaigns.id"],
                name=op.f("fk_campaign_join_codes_campaign_id_campaigns"),
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["created_by_user_id"],
                ["users.id"],
                name=op.f("fk_campaign_join_codes_created_by_user_id_users"),
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_campaign_join_codes")),
            sa.UniqueConstraint("code_hash", name=op.f("uq_campaign_join_codes_code_hash")),
        )
        op.create_index(
            "idx_campaign_join_codes_campaign_state",
            "campaign_join_codes",
            ["campaign_id", "revoked_at", "expires_at"],
            unique=False,
        )
        dialect = op.get_bind().dialect.name
        if dialect in {"sqlite", "postgresql"}:
            op.create_index(
                "uq_campaign_join_codes_active_campaign",
                "campaign_join_codes",
                ["campaign_id"],
                unique=True,
                sqlite_where=sa.text("revoked_at IS NULL"),
                postgresql_where=sa.text("revoked_at IS NULL"),
            )
        else:
            op.create_index(
                "idx_campaign_join_codes_active_campaign",
                "campaign_join_codes",
                ["campaign_id", "revoked_at"],
                unique=False,
            )

    if not _has_table("campaign_join_code_redemptions"):
        op.create_table(
            "campaign_join_code_redemptions",
            sa.Column("id", ID, nullable=False),
            sa.Column("join_code_id", ID, nullable=False),
            sa.Column("campaign_id", ID, nullable=False),
            sa.Column("user_id", ID, nullable=False),
            sa.Column("redeemed_at", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(
                ["campaign_id"],
                ["campaigns.id"],
                name=op.f("fk_campaign_join_code_redemptions_campaign_id_campaigns"),
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["join_code_id"],
                ["campaign_join_codes.id"],
                name=op.f("fk_campaign_join_code_redemptions_join_code_id_campaign_join_codes"),
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
                name=op.f("fk_campaign_join_code_redemptions_user_id_users"),
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_campaign_join_code_redemptions")),
            sa.UniqueConstraint(
                "join_code_id",
                "user_id",
                name=op.f("uq_campaign_join_code_redemptions_join_code_id_user_id"),
            ),
        )
        op.create_index(
            "idx_campaign_join_code_redemptions_campaign_user",
            "campaign_join_code_redemptions",
            ["campaign_id", "user_id"],
            unique=False,
        )



def downgrade() -> None:
    if _has_table("campaign_join_code_redemptions"):
        op.drop_index(
            "idx_campaign_join_code_redemptions_campaign_user",
            table_name="campaign_join_code_redemptions",
        )
        op.drop_table("campaign_join_code_redemptions")
    if _has_table("campaign_join_codes"):
        dialect = op.get_bind().dialect.name
        active_index = (
            "uq_campaign_join_codes_active_campaign"
            if dialect in {"sqlite", "postgresql"}
            else "idx_campaign_join_codes_active_campaign"
        )
        op.drop_index(active_index, table_name="campaign_join_codes")
        op.drop_index("idx_campaign_join_codes_campaign_state", table_name="campaign_join_codes")
        op.drop_table("campaign_join_codes")
