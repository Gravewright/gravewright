"""Add scene board_version for optimistic board-state writes.

Revision ID: 0002_board_version
Revises: 0001_initial_schema
Create Date: 2026-06-06
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import inspect
from sqlalchemy import text

revision = "0002_board_version"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("scenes", "board_version"):
        op.add_column(
            "scenes",
            Column("board_version", Integer, nullable=False, server_default=text("1")),
        )


def downgrade() -> None:
    if _has_column("scenes", "board_version"):
        op.drop_column("scenes", "board_version")
