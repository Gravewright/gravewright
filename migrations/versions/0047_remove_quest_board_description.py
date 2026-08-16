"""Remove legacy quest-board description and cover data.

Revision ID: 0047_remove_quest_board_desc
Revises: 0046_pdf_annotations
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa

revision = "0047_remove_quest_board_desc"
down_revision = "0046_pdf_annotations"
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
        if not isinstance(data, dict):
            data = {}
        changed = False
        for key in ("description", "description_markdown", "image"):
            if key in data:
                data.pop(key)
                changed = True
        if changed:
            bind.execute(
                sa.text("UPDATE journals SET data_json = :data WHERE id = :id"),
                {"id": row["id"], "data": json.dumps(data, separators=(",", ":"))},
            )


def downgrade() -> None:
    # Removed authored content cannot be reconstructed. Older application
    # versions already tolerate these optional keys being absent.
    pass
