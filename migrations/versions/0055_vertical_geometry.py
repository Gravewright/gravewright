"""Add semantic 2.5D elevation.

Revision ID: 0055_vertical_geometry
Revises: 0054_automation_jobs
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op
revision="0055_vertical_geometry";down_revision="0054_automation_jobs";branch_labels=None;depends_on=None
def _columns(table): return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}
def upgrade():
    if "elevation" not in _columns("tokens"): op.add_column("tokens",sa.Column("elevation",sa.Float(),nullable=False,server_default="0.0"))
    if "elevation" not in _columns("scene_lights"): op.add_column("scene_lights",sa.Column("elevation",sa.Float(),nullable=False,server_default="0.0"))
    columns=_columns("scene_walls")
    if "vertical_bottom" not in columns: op.add_column("scene_walls",sa.Column("vertical_bottom",sa.Float(),nullable=True))
    if "vertical_top" not in columns: op.add_column("scene_walls",sa.Column("vertical_top",sa.Float(),nullable=True))
def downgrade():
    for table,names in (("scene_walls",("vertical_top","vertical_bottom")),("scene_lights",("elevation",)),("tokens",("elevation",))):
        columns=_columns(table)
        for name in names:
            if name in columns: op.drop_column(table,name)
