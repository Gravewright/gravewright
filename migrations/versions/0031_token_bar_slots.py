"""rename the token's snapshotted hp bar to the bar_1 slot

Revision ID: 0031_token_bar_slots
Revises: 0030_combat_initiative_text

A token used to draw one bar, and the code that drew it looked for a key called
``hp``. That named the slot after one game's resource. A token now has two
slots: ``bar_1`` below it and ``bar_2`` above it, and the active system says
what each one reads.

Unlinked tokens keep their own copy of the bar values in ``overrides_json``, so
that snapshot has to move with the rename or those tokens lose their bar.
Linked tokens re-derive from the actor and need nothing.

Done in Python rather than SQL: ``overrides_json`` is a free-form document and
the JSON functions differ between SQLite and PostgreSQL.
"""
from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op

revision = "0031_token_bar_slots"
down_revision = "0030_combat_initiative_text"
branch_labels = None
depends_on = None

_TOKENS = sa.table(
    "tokens",
    sa.column("id", sa.String),
    sa.column("overrides_json", sa.Text),
)


def _rename_key(raw: str | None, source: str, target: str) -> str | None:
    """Return the rewritten document, or ``None`` when nothing needed moving."""
    if not raw:
        return None
    try:
        overrides = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(overrides, dict):
        return None
    bar = overrides.get(source)
    if not isinstance(bar, dict) or target in overrides:
        return None
    overrides[target] = bar
    overrides.pop(source, None)
    return json.dumps(overrides, ensure_ascii=False)


def _migrate(source: str, target: str) -> None:
    bind = op.get_bind()
    if "tokens" not in sa.inspect(bind).get_table_names():
        return
    rows = bind.execute(sa.select(_TOKENS.c.id, _TOKENS.c.overrides_json)).fetchall()
    for token_id, raw in rows:
        rewritten = _rename_key(raw, source, target)
        if rewritten is None:
            continue
        bind.execute(
            sa.update(_TOKENS).where(_TOKENS.c.id == token_id).values(overrides_json=rewritten)
        )


def upgrade() -> None:
    _migrate("hp", "bar_1")


def downgrade() -> None:
    _migrate("bar_1", "hp")
