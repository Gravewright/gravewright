"""Persist the first player interface introduction per campaign.

Revision ID: 0049_campaign_player_onboarding
Revises: 0048_remove_quest_board_filters
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0049_campaign_player_onboarding"
down_revision = "0048_remove_quest_board_filters"
branch_labels = None
depends_on = None

ID = sa.String(length=64)


def upgrade() -> None:
    if "campaign_player_onboarding" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "campaign_player_onboarding",
        sa.Column("campaign_id", ID, nullable=False),
        sa.Column("user_id", ID, nullable=False),
        sa.Column("shown_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("campaign_id", "user_id"),
    )
    op.create_index(
        "idx_campaign_player_onboarding_user",
        "campaign_player_onboarding",
        ["user_id", "shown_at"],
        unique=False,
    )


def downgrade() -> None:
    if "campaign_player_onboarding" not in sa.inspect(op.get_bind()).get_table_names():
        return
    op.drop_index(
        "idx_campaign_player_onboarding_user", table_name="campaign_player_onboarding"
    )
    op.drop_table("campaign_player_onboarding")
