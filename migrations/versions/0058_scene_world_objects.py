"""Add package-defined, core-owned scene world objects.

Revision ID: 0058_scene_world_objects
Revises: 0057_scene_zones
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "0058_scene_world_objects"
down_revision = "0057_scene_zones"
branch_labels = None
depends_on = None

def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()

def upgrade() -> None:
    if not _has_table("scene_object_types"):
        op.create_table("scene_object_types",
            sa.Column("campaign_id",sa.String(64),sa.ForeignKey("campaigns.id",ondelete="CASCADE"),primary_key=True),
            sa.Column("package_id",sa.String(191),primary_key=True),sa.Column("type_id",sa.String(191),primary_key=True),
            sa.Column("definition_json",sa.Text(),nullable=False),sa.Column("schema_version",sa.Integer(),nullable=False),
            sa.Column("active",sa.Integer(),nullable=False,server_default="1"),sa.Column("created_at",sa.Integer(),nullable=False),sa.Column("updated_at",sa.Integer(),nullable=False))
        op.create_index("idx_scene_object_types_type","scene_object_types",["campaign_id","type_id","active"])
    if not _has_table("scene_objects"):
        op.create_table("scene_objects",
            sa.Column("id",sa.String(64),primary_key=True),sa.Column("scene_id",sa.String(64),sa.ForeignKey("scenes.id",ondelete="CASCADE"),nullable=False),
            sa.Column("type_id",sa.String(191),nullable=False),sa.Column("provider_package_id",sa.String(191),nullable=False),sa.Column("schema_version",sa.Integer(),nullable=False),
            sa.Column("geometry_json",sa.Text(),nullable=False),sa.Column("transform_json",sa.Text(),nullable=False),sa.Column("presentation_json",sa.Text(),nullable=False),
            sa.Column("data_json",sa.Text(),nullable=False),sa.Column("audience_json",sa.Text(),nullable=False),sa.Column("enabled",sa.Integer(),nullable=False,server_default="1"),
            sa.Column("min_x",sa.Float(),nullable=False),sa.Column("min_y",sa.Float(),nullable=False),sa.Column("max_x",sa.Float(),nullable=False),sa.Column("max_y",sa.Float(),nullable=False),
            sa.Column("search_text",sa.Text(),nullable=False,server_default=""),sa.Column("version",sa.Integer(),nullable=False,server_default="1"),
            sa.Column("created_at",sa.Integer(),nullable=False),sa.Column("updated_at",sa.Integer(),nullable=False))
        op.create_index("idx_scene_objects_scene_bounds","scene_objects",["scene_id","enabled","min_x","max_x","min_y","max_y"])
        op.create_index("idx_scene_objects_provider","scene_objects",["provider_package_id","type_id"])

def downgrade() -> None:
    if _has_table("scene_objects"): op.drop_table("scene_objects")
    if _has_table("scene_object_types"): op.drop_table("scene_object_types")
