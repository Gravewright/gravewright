"""GM onboarding preferences

Revision ID: 0023_campaign_gm_onboarding
Revises: 0022_campaign_lobby_states
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0023_campaign_gm_onboarding"
down_revision = "0022_campaign_lobby_states"
branch_labels = None
depends_on = None

ID = sa.String(length=64)



def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()

def upgrade() -> None:
    # Reentrante: um banco que ja tem a tabela apenas segue adiante.
    if _has_table("campaign_gm_onboarding"):
        return
    op.create_table(
        "campaign_gm_onboarding",
        sa.Column("campaign_id", ID, nullable=False),
        sa.Column("user_id", ID, nullable=False),
        sa.Column("dismissed_at", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("campaign_id", "user_id"),
    )
    op.create_index(
        "idx_campaign_gm_onboarding_user",
        "campaign_gm_onboarding", ["user_id", "updated_at"], unique=False,
    )


def downgrade() -> None:
    if not _has_table("campaign_gm_onboarding"):
        return
    op.drop_index("idx_campaign_gm_onboarding_user", table_name="campaign_gm_onboarding")
    op.drop_table("campaign_gm_onboarding")
