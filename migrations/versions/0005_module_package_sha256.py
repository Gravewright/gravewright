"""Track uploaded module package checksums.

Revision ID: 0005_module_package_sha256
Revises: 0004_campaign_modules
Create Date: 2026-06-06
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import Column, String, inspect

revision = "0005_module_package_sha256"
down_revision = "0004_campaign_modules"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return table_name in inspect(bind).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    return column_name in {column["name"] for column in inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    if _has_table("modules_installed") and not _has_column("modules_installed", "package_sha256"):
        op.add_column("modules_installed", Column("package_sha256", String(64), nullable=True))


def downgrade() -> None:
    if _has_table("modules_installed") and _has_column("modules_installed", "package_sha256"):
        op.drop_column("modules_installed", "package_sha256")
