"""add module settings values

Revision ID: 0006_module_settings
Revises: 0005_module_package_sha256
Create Date: 2026-06-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0006_module_settings"
down_revision = "0005_module_package_sha256"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "module_settings",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("module_id", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("subject_id", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("setting_key", sa.String(length=128), nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("updated_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["module_id"], ["modules_installed.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("module_id", "scope", "subject_id", "setting_key"),
    )
    op.create_index("idx_module_settings_module_scope", "module_settings", ["module_id", "scope"])
    op.create_index("idx_module_settings_subject", "module_settings", ["scope", "subject_id"])


def downgrade() -> None:
    op.drop_index("idx_module_settings_subject", table_name="module_settings")
    op.drop_index("idx_module_settings_module_scope", table_name="module_settings")
    op.drop_table("module_settings")
