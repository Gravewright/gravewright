"""Persist adaptive raster policy decisions.

Revision ID: 0045_adaptive_raster_policy
Revises: 0044_virtual_raster_v2
"""

from alembic import op
import sqlalchemy as sa

revision = "0045_adaptive_raster_policy"
down_revision = "0044_virtual_raster_v2"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table in inspector.get_table_names() and column in {
        item["name"] for item in inspector.get_columns(table)
    }


def upgrade() -> None:
    if _has_column("scenes", "raster_policy_version"):
        return
    with op.batch_alter_table("scenes") as batch:
        batch.add_column(sa.Column("raster_selection_mode", sa.String(191), nullable=False, server_default="legacy"))
        batch.add_column(sa.Column("raster_policy_version", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("scenes") as batch:
        batch.drop_column("raster_policy_version")
        batch.drop_column("raster_selection_mode")
