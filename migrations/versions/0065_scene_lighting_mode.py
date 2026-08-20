"""Give each scene an explicit lighting regime instead of inferring one.

Until now "no lighting" and "dynamic lighting with the lights on" were the same
row: darkness == 0 and fog off. The GM could not keep a darkness value around
while the lights were lit, so flipping them back meant dialling the slider again.
`lighting_mode` records the choice and `lights_out` carries the switch, leaving
`darkness` free to mean only "how dark, when it is dark".

Revision ID: 0065_scene_lighting_mode
Revises: 0064_wave4_semantic_instances
"""
from alembic import op
import sqlalchemy as sa

revision = "0065_scene_lighting_mode"
down_revision = "0064_wave4_semantic_instances"
branch_labels = None
depends_on = None


def _has_column(table: str, name: str) -> bool:
    return any(column["name"] == name for column in sa.inspect(op.get_bind()).get_columns(table))


def upgrade() -> None:
    with op.batch_alter_table("scenes") as batch:
        if not _has_column("scenes", "lighting_mode"):
            batch.add_column(
                sa.Column("lighting_mode", sa.String(191), nullable=False, server_default="none")
            )
        if not _has_column("scenes", "lights_out"):
            batch.add_column(
                sa.Column("lights_out", sa.Integer, nullable=False, server_default="1")
            )

    # Backfill from the state the scene was already in, so nothing changes on
    # screen for a campaign that upgrades mid-session.
    op.execute("UPDATE scenes SET lighting_mode = 'manual' WHERE fog_enabled = 1")
    op.execute("UPDATE scenes SET lighting_mode = 'dynamic' WHERE fog_enabled = 0 AND darkness > 0")


def downgrade() -> None:
    with op.batch_alter_table("scenes") as batch:
        if _has_column("scenes", "lights_out"):
            batch.drop_column("lights_out")
        if _has_column("scenes", "lighting_mode"):
            batch.drop_column("lighting_mode")
