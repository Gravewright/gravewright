"""Persist the one-time package onboarding per user account.

Revision ID: 0056_package_onboarding_seen
Revises: 0055_vertical_geometry
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0056_package_onboarding_seen"
down_revision = "0055_vertical_geometry"
branch_labels = None
depends_on = None


def _columns() -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("user_preferences")}


def upgrade() -> None:
    if "package_onboarding_seen" not in _columns():
        op.add_column(
            "user_preferences",
            sa.Column("package_onboarding_seen", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if "package_onboarding_seen" in _columns():
        op.drop_column("user_preferences", "package_onboarding_seen")
