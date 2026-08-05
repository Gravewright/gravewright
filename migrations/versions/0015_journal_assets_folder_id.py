"""reconcile journal_assets.folder_id for legacy databases

Revision ID: 0015_journal_assets_folder_id
Revises: 0014_scene_image_composition
Create Date: 2026-08-04

Versions the additive change that used to be applied by the startup
``_ensure_incremental_columns`` bridge in ``engine.py`` (removed in Etapa 2).
Databases created with the current baseline already have this column and index,
so this migration is a guarded no-op there; only truly legacy databases whose
``journal_assets`` table predates ``folder_id`` are reconciled here.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0015_journal_assets_folder_id"
down_revision = "0014_scene_image_composition"
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    return any(
        column["name"] == column_name
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    )


def _has_index(table_name: str, index_name: str) -> bool:
    return any(
        index["name"] == index_name for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    )


def upgrade() -> None:
    if not _has_table("journal_assets"):
        return
    if not _has_column("journal_assets", "folder_id"):
        op.add_column(
            "journal_assets",
            sa.Column("folder_id", sa.String(length=64), nullable=True),
        )
    if not _has_index("journal_assets", "idx_journal_assets_folder"):
        op.create_index(
            "idx_journal_assets_folder",
            "journal_assets",
            ["campaign_id", "folder_id"],
        )


def downgrade() -> None:
    # Additive-only reconciliation; the column/index belong to the baseline
    # schema, so there is nothing safe to drop here without data loss.
    pass
