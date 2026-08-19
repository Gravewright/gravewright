"""Independent CAS clock for Scene Sound composition.

Revision ID: 0062_scene_sound_cas
Revises: 0061_native_sound_system
"""
from alembic import op
import sqlalchemy as sa
revision="0062_scene_sound_cas";down_revision="0061_native_sound_system";branch_labels=None;depends_on=None
def _has_column(table,name): return any(column["name"]==name for column in sa.inspect(op.get_bind()).get_columns(table))
def upgrade():
    if not _has_column("scenes","sound_version"):
        with op.batch_alter_table("scenes") as batch: batch.add_column(sa.Column("sound_version",sa.Integer,nullable=False,server_default="1"))
def downgrade():
    with op.batch_alter_table("scenes") as batch: batch.drop_column("sound_version")
