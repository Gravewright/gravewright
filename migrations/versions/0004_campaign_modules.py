"""Enable modules per campaign.

Revision ID: 0004_campaign_modules
Revises: 0003_modules_installed
Create Date: 2026-06-06
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

from app.persistence.tables import campaign_modules

revision = "0004_campaign_modules"
down_revision = "0003_modules_installed"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    if not _has_table("campaign_modules"):
        campaign_modules.create(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    if _has_table("campaign_modules"):
        campaign_modules.drop(op.get_bind(), checkfirst=True)
