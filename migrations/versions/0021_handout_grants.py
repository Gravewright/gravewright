"""targeted handout grants

Revision ID: 0021_handout_grants
Revises: 0020_audit_events
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0021_handout_grants"
down_revision = "0020_audit_events"
branch_labels = None
depends_on = None

ID = sa.String(length=64)
STR = sa.String(length=191)



def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()

def upgrade() -> None:
    # Reentrante: um banco que ja tem a tabela apenas segue adiante.
    if _has_table("handout_grants"):
        return
    op.create_table(
        "handout_grants",
        sa.Column("id", ID, nullable=False),
        sa.Column("campaign_id", ID, nullable=False),
        sa.Column("resource_type", STR, nullable=False),
        sa.Column("resource_id", ID, nullable=False),
        sa.Column("subject_type", STR, nullable=False),
        sa.Column("subject_id", ID, server_default=sa.text("''"), nullable=False),
        sa.Column("created_by_user_id", ID, nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("revoked_at", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "resource_type", "resource_id", "subject_type", "subject_id"),
    )
    op.create_index("idx_handout_grants_resource", "handout_grants", ["campaign_id", "resource_type", "resource_id"])
    op.create_index("idx_handout_grants_subject", "handout_grants", ["campaign_id", "subject_type", "subject_id", "revoked_at"])


def downgrade() -> None:
    if not _has_table("handout_grants"):
        return
    op.drop_index("idx_handout_grants_subject", table_name="handout_grants")
    op.drop_index("idx_handout_grants_resource", table_name="handout_grants")
    op.drop_table("handout_grants")
