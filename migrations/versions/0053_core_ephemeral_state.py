"""Add the internal mandatory-TTL coordination store.

Revision ID: 0053_core_ephemeral_state
Revises: 0052_geometry_semantic_channels
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "0053_core_ephemeral_state"
down_revision = "0052_geometry_semantic_channels"
branch_labels = None
depends_on = None
ID = sa.String(length=64)
STR = sa.String(length=191)

def upgrade() -> None:
    if "core_ephemeral_states" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "core_ephemeral_states",
        sa.Column("id", ID, primary_key=True),
        sa.Column("namespace", STR, nullable=False),
        sa.Column("campaign_id", ID, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope_id", ID, nullable=False),
        sa.Column("owner_user_id", ID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entry_key", STR, nullable=False),
        sa.Column("audience_json", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("namespace", "campaign_id", "scope_id", "owner_user_id", "entry_key"),
    )
    op.create_index("idx_core_ephemeral_scope", "core_ephemeral_states", ["namespace", "campaign_id", "scope_id", "expires_at"])
    op.create_index("idx_core_ephemeral_expiry", "core_ephemeral_states", ["expires_at"])

def downgrade() -> None:
    if "core_ephemeral_states" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("core_ephemeral_states")
