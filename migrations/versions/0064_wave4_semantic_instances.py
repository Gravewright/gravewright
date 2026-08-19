"""Durable bounded instances for SDK 1 Wave 4 semantic domains.

Revision ID: 0064_wave4_semantic_instances
Revises: 0063_spatial_sound_occlusion
"""
from alembic import op
import sqlalchemy as sa

revision = "0064_wave4_semantic_instances"
down_revision = "0063_spatial_sound_occlusion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "sdk_semantic_instances" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "sdk_semantic_instances",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("campaign_id", sa.String(64), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("package_id", sa.String(191), nullable=False),
        sa.Column("domain", sa.String(191), nullable=False),
        sa.Column("definition_id", sa.String(191), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scene_id", sa.String(64), sa.ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(191), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("waiting_on", sa.String(191), nullable=True),
        sa.Column("wake_at", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.String(191), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("campaign_id", "package_id", "domain", "idempotency_key"),
    )
    op.create_index("idx_sdk_semantic_instances_campaign_domain", "sdk_semantic_instances", ["campaign_id", "domain", "status"])
    op.create_index("idx_sdk_semantic_instances_due", "sdk_semantic_instances", ["domain", "status", "wake_at"])


def downgrade() -> None:
    op.drop_table("sdk_semantic_instances")
