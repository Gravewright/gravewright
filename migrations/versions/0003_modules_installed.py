"""Add modules_installed for Module API v1.

Revision ID: 0003_modules_installed
Revises: 0002_board_version
Create Date: 2026-06-06
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

from app.persistence.tables import modules_installed

revision = "0003_modules_installed"
down_revision = "0002_board_version"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _has_table("modules_installed"):
        modules_installed.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    if _has_table("modules_installed"):
        modules_installed.drop(op.get_bind(), checkfirst=True)
