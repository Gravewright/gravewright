"""dedicated asset library table

Revision ID: 0012_library_assets
Revises: 0011_asset_library
Create Date: 2026-06-23
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0012_library_assets"
down_revision = "0011_asset_library"
branch_labels = None
depends_on = None

ID = sa.String(length=64)


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not _has_table("library_assets"):
        op.create_table(
            "library_assets",
            sa.Column("id", ID, primary_key=True),
            sa.Column("campaign_id", ID, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
            sa.Column("owner_user_id", ID, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("folder_id", ID, nullable=True),
            sa.Column("filename", sa.Text(), nullable=False),
            sa.Column("content_type", sa.String(length=191), nullable=False),
            sa.Column("byte_size", sa.Integer(), nullable=False),
            sa.Column("width", sa.Integer(), nullable=True),
            sa.Column("height", sa.Integer(), nullable=True),
            sa.Column("storage_path", sa.Text(), nullable=False),
            sa.Column("hash", sa.String(length=191), nullable=False),
            sa.Column("created_at", sa.Integer(), nullable=False),
        )
        op.create_index("idx_library_assets_campaign", "library_assets", ["campaign_id", "created_at"])
        op.create_index("idx_library_assets_folder", "library_assets", ["campaign_id", "folder_id"])

    # Migrate existing scene-image library assets out of the journal asset table,
    # preserving ids so scene_image_placements.asset_id keeps resolving.
    if _has_table("journal_assets"):
        op.execute(
            sa.text(
                """
                INSERT INTO library_assets
                    (id, campaign_id, owner_user_id, folder_id, filename, content_type,
                     byte_size, width, height, storage_path, hash, created_at)
                SELECT id, campaign_id, owner_user_id, folder_id, filename, content_type,
                       byte_size, width, height, storage_path, hash, created_at
                FROM journal_assets
                WHERE purpose = 'scene_image'
                """
            )
        )
        op.execute(sa.text("DELETE FROM journal_assets WHERE purpose = 'scene_image'"))


def downgrade() -> None:
    # Move library assets back into the journal asset table before dropping it.
    if _has_table("journal_assets") and _has_table("library_assets"):
        op.execute(
            sa.text(
                """
                INSERT INTO journal_assets
                    (id, campaign_id, journal_id, folder_id, owner_user_id, purpose, filename,
                     content_type, byte_size, width, height, storage_path, hash, created_at)
                SELECT id, campaign_id, NULL, folder_id, owner_user_id, 'scene_image', filename,
                       content_type, byte_size, width, height, storage_path, hash, created_at
                FROM library_assets
                """
            )
        )
    if _has_table("library_assets"):
        op.drop_table("library_assets")
