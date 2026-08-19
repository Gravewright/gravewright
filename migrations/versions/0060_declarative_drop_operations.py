"""Durable receipts for bounded declarative drop operations.

Revision ID: 0060_declarative_drop_operations
Revises: 0059_wave3_semantics
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision="0060_declarative_drop_operations"
down_revision="0059_wave3_semantics"
branch_labels=None
depends_on=None

def upgrade():
    if "declarative_operation_receipts" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table("declarative_operation_receipts",sa.Column("identity",sa.String(191),primary_key=True),sa.Column("campaign_id",sa.String(64),sa.ForeignKey("campaigns.id",ondelete="CASCADE"),nullable=False),sa.Column("package_id",sa.String(191),nullable=False),sa.Column("payload_hash",sa.String(191),nullable=False),sa.Column("result_json",sa.Text(),nullable=False),sa.Column("created_at",sa.Integer(),nullable=False))
        op.create_index("idx_declarative_receipts_campaign","declarative_operation_receipts",["campaign_id","package_id"])

def downgrade():
    if "declarative_operation_receipts" in sa.inspect(op.get_bind()).get_table_names():op.drop_table("declarative_operation_receipts")
