"""Remove persisted quest-board status filters.

Revision ID: 0048_remove_quest_board_filters
Revises: 0047_remove_quest_board_desc
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa

revision = "0048_remove_quest_board_filters"
down_revision = "0047_remove_quest_board_desc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "journals" not in inspector.get_table_names():
        return

    rows = bind.execute(
        sa.text("SELECT id, data_json FROM journals WHERE type = :type"),
        {"type": "quest_board"},
    ).mappings()
    for row in rows:
        try:
            data = json.loads(row["data_json"] or "{}")
        except (TypeError, ValueError):
            data = {}
        if not isinstance(data, dict) or "filters" not in data:
            continue
        data.pop("filters")
        bind.execute(
            sa.text("UPDATE journals SET data_json = :data WHERE id = :id"),
            {"id": row["id"], "data": json.dumps(data, separators=(",", ":"))},
        )


def downgrade() -> None:
    pass
