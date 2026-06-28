"""scene image placements

Revision ID: 0010_scene_images
Revises: 0009_cards_system
Create Date: 2026-06-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0010_scene_images"
down_revision = "0009_cards_system"
branch_labels = None
depends_on = None

ID = sa.String(length=64)


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("scene_image_placements"):
        op.create_table(
            "scene_image_placements",
            sa.Column("id", ID, primary_key=True),
            sa.Column("campaign_id", ID, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
            sa.Column("scene_id", ID, sa.ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("asset_id", ID, nullable=False),
            sa.Column("owner_user_id", ID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("x", sa.Float(), nullable=False),
            sa.Column("y", sa.Float(), nullable=False),
            sa.Column("rotation", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("scale", sa.Float(), nullable=False, server_default=sa.text("1")),
            sa.Column("z_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("natural_width", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("natural_height", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("locked", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("metadata_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.Integer(), nullable=False),
            sa.Column("updated_at", sa.Integer(), nullable=False),
        )
        op.create_index("idx_scene_image_placements_scene", "scene_image_placements", ["scene_id", "z_index"])
        op.create_index("idx_scene_image_placements_campaign", "scene_image_placements", ["campaign_id"])


def downgrade() -> None:
    if _has_table("scene_image_placements"):
        op.drop_table("scene_image_placements")
