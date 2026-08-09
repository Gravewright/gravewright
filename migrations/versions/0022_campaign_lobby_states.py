"""campaign lobby ready state

Revision ID: 0022_campaign_lobby_states
Revises: 0021_handout_grants
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0022_campaign_lobby_states"
down_revision = "0021_handout_grants"
branch_labels = None
depends_on = None

ID = sa.String(length=64)
STR = sa.String(length=191)



def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()

def upgrade() -> None:
    # Reentrante: um banco que ja tem a tabela apenas segue adiante.
    if _has_table("campaign_lobby_states"):
        return
    op.create_table(
        "campaign_lobby_states",
        sa.Column("campaign_id", ID, nullable=False),
        sa.Column("user_id", ID, nullable=False),
        sa.Column("is_ready", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("selected_actor_id", ID, nullable=True),
        sa.Column("assets_state", STR, server_default=sa.text("'unknown'"), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selected_actor_id"], ["actors_core.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("campaign_id", "user_id"),
    )
    op.create_index(
        "idx_campaign_lobby_states_campaign_ready",
        "campaign_lobby_states", ["campaign_id", "is_ready"], unique=False,
    )


def downgrade() -> None:
    if not _has_table("campaign_lobby_states"):
        return
    op.drop_index("idx_campaign_lobby_states_campaign_ready", table_name="campaign_lobby_states")
    op.drop_table("campaign_lobby_states")
