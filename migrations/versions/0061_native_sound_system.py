"""Native first-class Sound resources and spatial emitters."""
from alembic import op
import sqlalchemy as sa
revision="0061_native_sound_system";down_revision="0060_declarative_drop_operations";branch_labels=None;depends_on=None
ID=sa.String(64);STR=sa.String(191)
def _has_table(name): return name in sa.inspect(op.get_bind()).get_table_names()
def _has_column(table,name): return any(column["name"]==name for column in sa.inspect(op.get_bind()).get_columns(table))
def upgrade():
    if not _has_table("sounds"):
        op.create_table("sounds",sa.Column("id",ID,primary_key=True),sa.Column("campaign_id",ID,sa.ForeignKey("campaigns.id",ondelete="CASCADE"),nullable=False),sa.Column("name",STR,nullable=False),sa.Column("asset_id",ID,sa.ForeignKey("library_assets.id",ondelete="RESTRICT"),nullable=False),sa.Column("kind",STR,nullable=False),sa.Column("tags_json",sa.Text,nullable=False,server_default="[]"),sa.Column("default_gain",sa.Float,nullable=False,server_default="1"),sa.Column("default_loop",sa.Integer,nullable=False,server_default="0"),sa.Column("metadata_json",sa.Text,nullable=False,server_default="{}"),sa.Column("version",sa.Integer,nullable=False,server_default="1"),sa.Column("created_at",sa.Integer,nullable=False),sa.Column("updated_at",sa.Integer,nullable=False));op.create_index("idx_sounds_campaign_kind_name","sounds",["campaign_id","kind","name"])
    if not _has_table("sound_playlists"):
        op.create_table("sound_playlists",sa.Column("id",ID,primary_key=True),sa.Column("campaign_id",ID,sa.ForeignKey("campaigns.id",ondelete="CASCADE"),nullable=False),sa.Column("name",STR,nullable=False),sa.Column("entries_json",sa.Text,nullable=False),sa.Column("playback_mode",STR,nullable=False),sa.Column("default_gain",sa.Float),sa.Column("crossfade_ms",sa.Integer,nullable=False,server_default="0"),sa.Column("version",sa.Integer,nullable=False,server_default="1"),sa.Column("created_at",sa.Integer,nullable=False),sa.Column("updated_at",sa.Integer,nullable=False));op.create_index("idx_sound_playlists_campaign_name","sound_playlists",["campaign_id","name"])
    if not _has_table("soundscapes"):
        op.create_table("soundscapes",sa.Column("id",ID,primary_key=True),sa.Column("campaign_id",ID,sa.ForeignKey("campaigns.id",ondelete="CASCADE"),nullable=False),sa.Column("name",STR,nullable=False),sa.Column("layers_json",sa.Text,nullable=False),sa.Column("random_pools_json",sa.Text,nullable=False,server_default="[]"),sa.Column("fade_in_ms",sa.Integer,nullable=False,server_default="0"),sa.Column("fade_out_ms",sa.Integer,nullable=False,server_default="0"),sa.Column("version",sa.Integer,nullable=False,server_default="1"),sa.Column("created_at",sa.Integer,nullable=False),sa.Column("updated_at",sa.Integer,nullable=False));op.create_index("idx_soundscapes_campaign_name","soundscapes",["campaign_id","name"])
    if not _has_table("scene_spatial_sounds"):
        op.create_table("scene_spatial_sounds",sa.Column("id",ID,primary_key=True),sa.Column("scene_id",ID,sa.ForeignKey("scenes.id",ondelete="CASCADE"),nullable=False),sa.Column("sound_id",ID,sa.ForeignKey("sounds.id",ondelete="RESTRICT"),nullable=False),sa.Column("x",sa.Float,nullable=False),sa.Column("y",sa.Float,nullable=False),sa.Column("radius",sa.Float,nullable=False),sa.Column("gain",sa.Float,nullable=False),sa.Column("falloff",STR,nullable=False),sa.Column("loop",sa.Integer,nullable=False),sa.Column("audience_json",sa.Text,nullable=False),sa.Column("enabled",sa.Integer,nullable=False,server_default="1"),sa.Column("version",sa.Integer,nullable=False,server_default="1"),sa.Column("created_at",sa.Integer,nullable=False),sa.Column("updated_at",sa.Integer,nullable=False));op.create_index("idx_spatial_sounds_scene","scene_spatial_sounds",["scene_id","enabled"])
    if not _has_column("scenes","soundscape_id"):
        with op.batch_alter_table("scenes") as batch:batch.add_column(sa.Column("soundscape_id",ID,nullable=True))
    if not _has_column("scene_walls","sound_behavior"):
        with op.batch_alter_table("scene_walls") as batch:batch.add_column(sa.Column("sound_behavior",STR,nullable=False,server_default="block"));batch.create_check_constraint("sound_behavior","sound_behavior IN ('block','attenuate','pass')")
def downgrade():
    with op.batch_alter_table("scene_walls") as batch:batch.drop_constraint("sound_behavior",type_="check");batch.drop_column("sound_behavior")
    with op.batch_alter_table("scenes") as batch:batch.drop_column("soundscape_id")
    for name in ("scene_spatial_sounds","soundscapes","sound_playlists","sounds"):op.drop_table(name)
