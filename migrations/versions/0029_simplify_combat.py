"""reduce the combat tracker to round, turn and one initiative value per combatant

Revision ID: 0029_simplify_combat
Revises: 0028_light_opacity

The encounter carried a mode, a strategy, a phase and a settings snapshot, and
each participant carried a label, a raw roll breakdown, a sort key, a group and
a metadata blob. All of it existed to support six competing initiative modes.
There is one value per combatant now, so the order is derived from it at read
time and everything that duplicated it is gone.

``combat_events`` is dropped: nothing ever read it back.

Existing encounters keep their round, turn and initiative values.

(``0030`` turns ``initiative`` into text and moves the ordering key to
``sort_value``; this revision is what ran before that was decided.)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0029_simplify_combat"
down_revision = "0028_light_opacity"
branch_labels = None
depends_on = None

_ENCOUNTER_DROPS = ("mode", "strategy", "phase", "settings_json")
_COMBATANT_DROPS = (
    "initiative_label",
    "initiative_data_json",
    "sort_key",
    "group_key",
    "metadata_json",
)


def _tables() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    tables = _tables()

    if "combat_events" in tables:
        op.drop_table("combat_events")

    if "combat_encounters" in tables:
        existing = _columns("combat_encounters")
        with op.batch_alter_table("combat_encounters") as batch:
            for column in _ENCOUNTER_DROPS:
                if column in existing:
                    batch.drop_column(column)

    # The index covers ``sort_key``, which is about to go: drop it before the
    # batch rebuild tries to recreate it against a column that no longer exists.
    op.execute(sa.text("DROP INDEX IF EXISTS idx_combat_participants_combat"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_combat_combatants_combat"))

    # The old name said "participant"; the thing is a combatant.
    if "combat_participants" in tables and "combat_combatants" not in tables:
        op.rename_table("combat_participants", "combat_combatants")
        tables = _tables()

    if "combat_combatants" not in tables:
        return

    existing = _columns("combat_combatants")
    with op.batch_alter_table("combat_combatants") as batch:
        if "initiative_value" in existing and "initiative" not in existing:
            batch.alter_column(
                "initiative_value", new_column_name="initiative", existing_type=sa.Float()
            )
        if "visible_to_players" in existing and "hidden" not in existing:
            batch.alter_column(
                "visible_to_players", new_column_name="hidden", existing_type=sa.Integer()
            )
        if "tie_break" not in existing:
            batch.add_column(
                sa.Column("tie_break", sa.Float(), server_default=sa.text("0"), nullable=False)
            )
        for column in _COMBATANT_DROPS:
            if column in existing:
                batch.drop_column(column)

    # ``visible_to_players`` was the inverse of ``hidden``.
    if "visible_to_players" in existing:
        op.execute(
            sa.text("UPDATE combat_combatants SET hidden = CASE WHEN hidden = 0 THEN 1 ELSE 0 END")
        )

    op.create_index(
        "idx_combat_combatants_combat", "combat_combatants", ["combat_id", "created_at"]
    )


def downgrade() -> None:
    """Restore the shape, not the data: the discarded columns had no source."""
    if "combat_combatants" not in _tables():
        return

    op.execute(sa.text("DROP INDEX IF EXISTS idx_combat_combatants_combat"))
    op.execute(sa.text("UPDATE combat_combatants SET hidden = CASE WHEN hidden = 0 THEN 1 ELSE 0 END"))
    with op.batch_alter_table("combat_combatants") as batch:
        batch.alter_column(
            "initiative", new_column_name="initiative_value", existing_type=sa.Float()
        )
        batch.alter_column(
            "hidden", new_column_name="visible_to_players", existing_type=sa.Integer()
        )
        batch.drop_column("tie_break")
        batch.add_column(
            sa.Column("initiative_label", sa.String(), server_default=sa.text("''"), nullable=False)
        )
        batch.add_column(
            sa.Column(
                "initiative_data_json", sa.Text(), server_default=sa.text("'{}'"), nullable=False
            )
        )
        batch.add_column(
            sa.Column("sort_key", sa.Float(), server_default=sa.text("0"), nullable=False)
        )
        batch.add_column(sa.Column("group_key", sa.String(), nullable=True))
        batch.add_column(
            sa.Column("metadata_json", sa.Text(), server_default=sa.text("'{}'"), nullable=False)
        )
    op.rename_table("combat_combatants", "combat_participants")
    op.create_index(
        "idx_combat_participants_combat", "combat_participants", ["combat_id", "sort_key"]
    )

    with op.batch_alter_table("combat_encounters") as batch:
        batch.add_column(
            sa.Column("mode", sa.String(), server_default=sa.text("'manual'"), nullable=False)
        )
        batch.add_column(
            sa.Column("strategy", sa.String(), server_default=sa.text("'manual'"), nullable=False)
        )
        batch.add_column(
            sa.Column(
                "phase", sa.String(), server_default=sa.text("'combat.start'"), nullable=False
            )
        )
        batch.add_column(
            sa.Column("settings_json", sa.Text(), server_default=sa.text("'{}'"), nullable=False)
        )

    op.create_table(
        "combat_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "combat_id",
            sa.String(),
            sa.ForeignKey("combat_encounters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("round_number", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("turn_index", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("participant_id", sa.String(), nullable=True),
        sa.Column("actor_id", sa.String(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload_json", sa.Text(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_index("idx_combat_events_combat", "combat_events", ["combat_id", "created_at"])
