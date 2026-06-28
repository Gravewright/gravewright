"""asset library folders

Revision ID: 0011_asset_library
Revises: 0010_scene_images
Create Date: 2026-06-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0011_asset_library"
down_revision = "0010_scene_images"
branch_labels = None
depends_on = None

ID = sa.String(length=64)


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in sa.inspect(op.get_bind()).get_columns(table_name))


def upgrade() -> None:
    if _has_table("journal_assets") and not _has_column("journal_assets", "folder_id"):
        op.add_column("journal_assets", sa.Column("folder_id", ID, nullable=True))
        op.create_index("idx_journal_assets_folder", "journal_assets", ["campaign_id", "folder_id"])

    if not _has_table("asset_folders"):
        op.create_table(
            "asset_folders",
            sa.Column("id", ID, primary_key=True),
            sa.Column("campaign_id", ID, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
            sa.Column("parent_id", ID, nullable=True),
            sa.Column("name", sa.String(length=191), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.Integer(), nullable=False),
            sa.Column("updated_at", sa.Integer(), nullable=False),
        )
        op.create_index(
            "idx_asset_folders_campaign_parent",
            "asset_folders",
            ["campaign_id", "parent_id", "sort_order", "name"],
        )


def downgrade() -> None:
    if _has_table("asset_folders"):
        op.drop_table("asset_folders")
    if _has_table("journal_assets") and _has_column("journal_assets", "folder_id"):
        op.drop_index("idx_journal_assets_folder", table_name="journal_assets")
        op.drop_column("journal_assets", "folder_id")
