"""Allow tokens to move freely when grid snapping is disabled.

Revision ID: 0067_free_token_position
Revises: 0066_content_pack_ownership
"""
from alembic import op
import sqlalchemy as sa


revision = "0067_free_token_position"
down_revision = "0066_content_pack_ownership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tokens") as batch:
        batch.alter_column(
            "grid_x", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=False
        )
        batch.alter_column(
            "grid_y", existing_type=sa.Integer(), type_=sa.Float(), existing_nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table("tokens") as batch:
        batch.alter_column(
            "grid_x", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=False
        )
        batch.alter_column(
            "grid_y", existing_type=sa.Float(), type_=sa.Integer(), existing_nullable=False
        )
