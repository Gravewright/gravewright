"""package manifest integrity fields

Adds manifest integrity columns to ``installed_packages``:
``manifest_hash``, ``last_validated_at`` and ``last_validation_status``. All are
nullable and added in place, so existing rows are preserved (back-filled lazily
on the next install/enable).

Revision ID: 0008_package_manifest_integrity
Revises: 0007_sdk_packages
Create Date: 2026-06-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0008_package_manifest_integrity"
down_revision = "0007_sdk_packages"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    return column_name in {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def upgrade() -> None:
    if not _has_column("installed_packages", "manifest_hash"):
        op.add_column(
            "installed_packages",
            sa.Column("manifest_hash", sa.String(length=64), nullable=True),
        )

    if not _has_column("installed_packages", "last_validated_at"):
        op.add_column(
            "installed_packages",
            sa.Column("last_validated_at", sa.Integer(), nullable=True),
        )

    if not _has_column("installed_packages", "last_validation_status"):
        op.add_column(
            "installed_packages",
            sa.Column("last_validation_status", sa.String(length=191), nullable=True),
        )


def downgrade() -> None:
    if _has_column("installed_packages", "last_validation_status"):
        op.drop_column("installed_packages", "last_validation_status")

    if _has_column("installed_packages", "last_validated_at"):
        op.drop_column("installed_packages", "last_validated_at")

    if _has_column("installed_packages", "manifest_hash"):
        op.drop_column("installed_packages", "manifest_hash")