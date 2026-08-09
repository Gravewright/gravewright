"""dynamic lighting walls and doors

Revision ID: 0024_scene_walls
Revises: 0023_campaign_gm_onboarding
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "0024_scene_walls"
down_revision = "0023_campaign_gm_onboarding"
branch_labels = None
depends_on = None
ID = sa.String(length=64)
STR = sa.String(length=191)

def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()

def upgrade() -> None:
    if _has_table("scene_walls"):
        return
    op.create_table("scene_walls",
        sa.Column("id", ID, nullable=False), sa.Column("campaign_id", ID, nullable=False),
        sa.Column("scene_id", ID, nullable=False), sa.Column("kind", STR, server_default=sa.text("'wall'"), nullable=False),
        sa.Column("door_state", STR, server_default=sa.text("'closed'"), nullable=False),
        sa.Column("x1", sa.Float(), nullable=False), sa.Column("y1", sa.Float(), nullable=False),
        sa.Column("x2", sa.Float(), nullable=False), sa.Column("y2", sa.Float(), nullable=False),
        sa.Column("created_by_user_id", ID, nullable=False), sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.CheckConstraint("kind IN ('wall','door')", name="kind"),
        sa.CheckConstraint("door_state IN ('closed','open')", name="door_state"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"))
    op.create_index("idx_scene_walls_scene", "scene_walls", ["scene_id", "created_at"])

def downgrade() -> None:
    if not _has_table("scene_walls"):
        return
    op.drop_index("idx_scene_walls_scene", table_name="scene_walls")
    op.drop_table("scene_walls")
