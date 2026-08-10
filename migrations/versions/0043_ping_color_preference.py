"""add per-user board ping color

Revision ID: 0043_ping_color_preference
Revises: 0042_particle_kinds
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0043_ping_color_preference"
down_revision = "0042_particle_kinds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_preferences",
        sa.Column("ping_color", sa.String(length=191), nullable=False, server_default="#f2c679"),
    )


def downgrade() -> None:
    op.drop_column("user_preferences", "ping_color")
