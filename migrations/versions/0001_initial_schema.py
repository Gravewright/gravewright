"""Initial portable SQLAlchemy Core schema.

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-06-06
"""
from __future__ import annotations

from alembic import op

from app.persistence.tables import metadata

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def _create_active_scene_index(dialect_name: str) -> None:
    if dialect_name in {"sqlite", "postgresql"}:
        op.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_scenes_active_campaign "
            "ON scenes (campaign_id) WHERE active = 1"
        )


def _drop_active_scene_index(dialect_name: str) -> None:
    if dialect_name == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_scenes_active_campaign")
    elif dialect_name == "sqlite":
        op.execute("DROP INDEX IF EXISTS idx_scenes_active_campaign")


def upgrade() -> None:
    bind = op.get_bind()
    metadata.create_all(bind=bind, checkfirst=True)
    _create_active_scene_index(bind.dialect.name)


def downgrade() -> None:
    bind = op.get_bind()
    _drop_active_scene_index(bind.dialect.name)
    metadata.drop_all(bind=bind, checkfirst=True)
