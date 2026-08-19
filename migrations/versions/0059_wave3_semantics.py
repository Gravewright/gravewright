"""Add Wave 3 semantic registries, audio, navigation and bindings.

Revision ID: 0059_wave3_semantics
Revises: 0058_scene_world_objects
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op
revision="0059_wave3_semantics";down_revision="0058_scene_world_objects";branch_labels=None;depends_on=None
def has(name):return name in sa.inspect(op.get_bind()).get_table_names()
def upgrade():
    if not has("sdk_semantic_registrations"):
        op.create_table("sdk_semantic_registrations",sa.Column("campaign_id",sa.String(64),sa.ForeignKey("campaigns.id",ondelete="CASCADE"),primary_key=True),sa.Column("package_id",sa.String(191),primary_key=True),sa.Column("registry",sa.String(191),primary_key=True),sa.Column("entry_id",sa.String(191),primary_key=True),sa.Column("definition_json",sa.Text(),nullable=False),sa.Column("active",sa.Integer(),nullable=False,server_default="1"),sa.Column("created_at",sa.Integer(),nullable=False),sa.Column("updated_at",sa.Integer(),nullable=False));op.create_index("idx_sdk_semantic_registry","sdk_semantic_registrations",["campaign_id","registry","active"])
    if not has("audio_playbacks"):
        op.create_table("audio_playbacks",sa.Column("id",sa.String(64),primary_key=True),sa.Column("campaign_id",sa.String(64),sa.ForeignKey("campaigns.id",ondelete="CASCADE"),nullable=False),sa.Column("package_id",sa.String(191),nullable=False),sa.Column("owner_user_id",sa.String(64),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),sa.Column("asset_json",sa.Text(),nullable=False),sa.Column("channel",sa.String(191),nullable=False),sa.Column("state",sa.String(191),nullable=False),sa.Column("loop",sa.Integer(),nullable=False),sa.Column("gain",sa.Float(),nullable=False),sa.Column("audience_json",sa.Text(),nullable=False),sa.Column("scene_id",sa.String(64),sa.ForeignKey("scenes.id",ondelete="CASCADE")),sa.Column("anchor_json",sa.Text()),sa.Column("idempotency_key",sa.String(191)),sa.Column("started_at",sa.Integer(),nullable=False),sa.Column("expires_at",sa.Integer()),sa.Column("fade_json",sa.Text()),sa.Column("version",sa.Integer(),nullable=False,server_default="1"),sa.Column("created_at",sa.Integer(),nullable=False),sa.Column("updated_at",sa.Integer(),nullable=False),sa.UniqueConstraint("campaign_id","package_id","idempotency_key"));op.create_index("idx_audio_projection","audio_playbacks",["campaign_id","scene_id","state"])
    if not has("user_scene_navigation"):
        op.create_table("user_scene_navigation",sa.Column("campaign_id",sa.String(64),sa.ForeignKey("campaigns.id",ondelete="CASCADE"),primary_key=True),sa.Column("user_id",sa.String(64),sa.ForeignKey("users.id",ondelete="CASCADE"),primary_key=True),sa.Column("scene_id",sa.String(64),sa.ForeignKey("scenes.id",ondelete="CASCADE"),nullable=False),sa.Column("reason",sa.Text(),nullable=False,server_default=""),sa.Column("idempotency_key",sa.String(191)),sa.Column("version",sa.Integer(),nullable=False,server_default="1"),sa.Column("created_at",sa.Integer(),nullable=False),sa.Column("updated_at",sa.Integer(),nullable=False))
    if not has("input_bindings"):
        op.create_table("input_bindings",sa.Column("user_id",sa.String(64),sa.ForeignKey("users.id",ondelete="CASCADE"),primary_key=True),sa.Column("package_id",sa.String(191),primary_key=True),sa.Column("command_id",sa.String(191),primary_key=True),sa.Column("binding",sa.String(191),nullable=False),sa.Column("version",sa.Integer(),nullable=False,server_default="1"),sa.Column("created_at",sa.Integer(),nullable=False),sa.Column("updated_at",sa.Integer(),nullable=False),sa.UniqueConstraint("user_id","binding"))
def downgrade():
    for name in ("input_bindings","user_scene_navigation","audio_playbacks","sdk_semantic_registrations"):
        if has(name):op.drop_table(name)
