"""persistent administrative audit events

Revision ID: 0020_audit_events
Revises: 0019_campaign_snapshots
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0020_audit_events"
down_revision = "0019_campaign_snapshots"
branch_labels = None
depends_on = None

ID = sa.String(length=64)
STR = sa.String(length=191)



def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()

def upgrade() -> None:
    # Reentrante: um banco que ja tem a tabela apenas segue adiante.
    if _has_table("audit_events"):
        return
    op.create_table(
        "audit_events",
        sa.Column("id", ID, nullable=False),
        sa.Column("campaign_id", ID, nullable=False),
        sa.Column("actor_user_id", ID, nullable=True),
        sa.Column("catalog_version", sa.Integer(), nullable=False),
        sa.Column("event_type", STR, nullable=False),
        sa.Column("subject_type", STR, nullable=True),
        sa.Column("subject_id", ID, nullable=True),
        sa.Column("action", STR, nullable=False),
        sa.Column("result", STR, nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_events_campaign_created", "audit_events", ["campaign_id", "created_at"])
    op.create_index("idx_audit_events_campaign_type_created", "audit_events", ["campaign_id", "event_type", "created_at"])


def downgrade() -> None:
    if not _has_table("audit_events"):
        return
    op.drop_index("idx_audit_events_campaign_type_created", table_name="audit_events")
    op.drop_index("idx_audit_events_campaign_created", table_name="audit_events")
    op.drop_table("audit_events")
