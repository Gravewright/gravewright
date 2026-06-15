"""destructive SDK package refactor

Drops the legacy System/Module API tables and creates the unified Gravewright
SDK package tables. This is a PRE-ALPHA breaking migration: System/Module data
is intentionally NOT backfilled.

Revision ID: 0007_sdk_packages
Revises: 0006_module_settings
Create Date: 2026-06-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007_sdk_packages"
down_revision = "0006_module_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- drop legacy System/Module API tables (destructive) ------------------
    for index, table in (
        ("idx_module_settings_subject", "module_settings"),
        ("idx_module_settings_module_scope", "module_settings"),
    ):
        op.drop_index(index, table_name=table, if_exists=True)
    op.drop_table("module_settings")

    for index in ("idx_campaign_modules_module", "idx_campaign_modules_campaign"):
        op.drop_index(index, table_name="campaign_modules", if_exists=True)
    op.drop_table("campaign_modules")

    op.drop_table("modules_installed")
    op.drop_table("systems_installed")

    # --- new Gravewright SDK package tables -----------------------------------
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
