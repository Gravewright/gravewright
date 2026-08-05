"""Gravewright SDK package tables

Creates the unified Gravewright SDK package tables.

Revision ID: 0007_sdk_packages
Revises: 0002_board_version
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007_sdk_packages"
down_revision = "0002_board_version"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    # Idempotent: skip if the SDK package tables already exist.
    if _has_table("installed_packages"):
        return

    op.create_table(
        "installed_packages",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=191), nullable=False),
        sa.Column("name", sa.String(length=191), nullable=False, server_default=""),
        sa.Column("version", sa.String(length=191), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=191), nullable=False, server_default="installed"),
        sa.Column("package_dir", sa.Text(), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("compatibility_status", sa.String(length=191), nullable=False, server_default="unverified"),
        sa.Column("validation_errors_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("package_sha256", sa.String(length=64), nullable=True),
        sa.Column("installed_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("installed_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.Column("enabled_at", sa.Integer(), nullable=True),
        sa.Column("disabled_at", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["installed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_installed_packages_kind", "installed_packages", ["kind"])

    op.create_table(
        "campaign_packages",
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("package_id", sa.String(length=64), nullable=False),
        sa.Column("activation_role", sa.String(length=191), nullable=False),
        sa.Column("status", sa.String(length=191), nullable=False, server_default="active"),
        sa.Column("load_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("enabled_at", sa.Integer(), nullable=False),
        sa.Column("disabled_at", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["package_id"], ["installed_packages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enabled_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("campaign_id", "package_id"),
    )
    op.create_index("idx_campaign_packages_campaign", "campaign_packages", ["campaign_id"])
    op.create_index("idx_campaign_packages_role", "campaign_packages", ["campaign_id", "activation_role"])

    op.create_table(
        "package_settings",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("package_id", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("user_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("setting_key", sa.String(length=128), nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("package_id", "campaign_id", "user_id", "setting_key"),
    )
    op.create_index("idx_package_settings_package", "package_settings", ["package_id"])
    op.create_index("idx_package_settings_campaign", "package_settings", ["campaign_id"])

    op.create_table(
        "package_content_imports",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("package_id", sa.String(length=64), nullable=False),
        sa.Column("content_pack_id", sa.String(length=191), nullable=False),
        sa.Column("content_pack_type", sa.String(length=191), nullable=False),
        sa.Column("imported_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("imported_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["imported_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_package_content_imports_campaign", "package_content_imports", ["campaign_id"])
    op.create_index("idx_package_content_imports_package", "package_content_imports", ["package_id"])


def downgrade() -> None:
    raise NotImplementedError(
        "0007_sdk_packages is a destructive PRE-ALPHA migration and cannot be reversed."
    )
