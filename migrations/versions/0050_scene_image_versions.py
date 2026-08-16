"""Add monotonic versions to scene image placements.

Revision ID: 0050_scene_image_versions
Revises: 0049_campaign_player_onboarding
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0050_scene_image_versions"
down_revision = "0049_campaign_player_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("scene_image_placements")}
    if "version" not in columns:
        op.add_column(
            "scene_image_placements",
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        )


def downgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("scene_image_placements")}
    if "version" in columns:
        op.drop_column("scene_image_placements", "version")
