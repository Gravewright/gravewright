"""campaign snapshots

Revision ID: 0019_campaign_snapshots
Revises: 0018_campaign_join_codes
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0019_campaign_snapshots"
down_revision = "0018_campaign_join_codes"
branch_labels = None
depends_on = None

ID = sa.String(length=64)
STR = sa.String(length=191)



def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()

def upgrade() -> None:
    # Reentrante: um banco que ja tem a tabela apenas segue adiante.
    if _has_table("campaign_snapshots"):
        return
    op.create_table(
        "campaign_snapshots",
        sa.Column("id", ID, nullable=False),
        sa.Column("campaign_id", ID, nullable=False),
        sa.Column("created_by_user_id", ID, nullable=False),
        sa.Column("name", STR, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("kind", STR, server_default=sa.text("'manual'"), nullable=False),
        sa.Column("format_version", sa.Integer(), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_campaign_snapshots_campaign_created",
        "campaign_snapshots",
        ["campaign_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    if not _has_table("campaign_snapshots"):
        return
    op.drop_index("idx_campaign_snapshots_campaign_created", table_name="campaign_snapshots")
    op.drop_table("campaign_snapshots")
