"""Add first-class semantic scene zones.

Revision ID: 0057_scene_zones
Revises: 0056_package_onboarding_seen
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "0057_scene_zones"
down_revision = "0056_package_onboarding_seen"
branch_labels = None
depends_on = None

def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()

def upgrade() -> None:
    if _has_table("scene_zones"):
        return
    op.create_table("scene_zones",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("scene_id", sa.String(64), sa.ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("zone_type", sa.String(191), nullable=False, server_default="standard"),
        sa.Column("geometry_json", sa.Text(), nullable=False),
        sa.Column("vertical_bottom", sa.Float(), nullable=True), sa.Column("vertical_top", sa.Float(), nullable=True),
        sa.Column("audience_json", sa.Text(), nullable=False), sa.Column("enabled", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("tags_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("package_id", sa.String(191), nullable=False), sa.Column("provider_id", sa.String(191), nullable=True),
        sa.Column("min_x", sa.Float(), nullable=False), sa.Column("min_y", sa.Float(), nullable=False),
        sa.Column("max_x", sa.Float(), nullable=False), sa.Column("max_y", sa.Float(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.Integer(), nullable=False), sa.Column("updated_at", sa.Integer(), nullable=False))
    op.create_index("idx_scene_zones_scene_bounds", "scene_zones", ["scene_id","enabled","min_x","max_x","min_y","max_y"])
    op.create_index("idx_scene_zones_package", "scene_zones", ["package_id"])

def downgrade() -> None:
    if _has_table("scene_zones"):
        op.drop_table("scene_zones")
