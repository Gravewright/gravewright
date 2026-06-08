"""Portable schema as SQLAlchemy Core ``MetaData``.

This mirrors the *final* shape of the legacy ``schema/*.py`` install scripts
(base CREATE TABLE plus every applied migration) but expressed in a dialect
agnostic way so the same definitions create the database on SQLite, PostgreSQL
and MySQL.

Type policy (important for MySQL portability):
- ``String(n)`` (→ VARCHAR) for every identifier, hash, key, status and other
  short value, because MySQL cannot index/PK a TEXT/BLOB column without a length.
- ``Text`` only for large, never-indexed payloads (JSON blobs, markdown, paths).
- ``LargeBinary`` for BLOBs, ``BigInteger`` for the autoincrement event sequence.

The one construct that is genuinely not portable — the partial UNIQUE index
``scenes(campaign_id) WHERE active = 1`` — is created out of band in
``engine.create_schema`` for SQLite/PostgreSQL only.
"""

from __future__ import annotations

from sqlalchemy import BigInteger
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import MetaData
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import text

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_N_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

                                                                                
                                                                        
                                                                               
_ID = String(64)
_STR = String(191)


                                                                              

users = Table(
    "users",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("name", _STR, nullable=False),
    Column("email", _STR, nullable=False, unique=True),
    Column("password_hash", _STR, nullable=False),
    Column("system_role", _STR, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
)

session_store = Table(
    "session_store",
    metadata,
    Column("key", _STR, primary_key=True),
    Column("value", LargeBinary, nullable=False),
    Column("expires_at", Integer, nullable=True),
    Column("user_id", _ID, nullable=True),
    Index("idx_session_store_user_id", "user_id"),
)

user_presence = Table(
    "user_presence",
    metadata,
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("last_seen_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_user_presence_last_seen_at", "last_seen_at"),
)

user_preferences = Table(
    "user_preferences",
    metadata,
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("game_layout_mode", _STR, nullable=False, server_default=text("'gravewright'")),
    Column("updated_at", Integer, nullable=False),
)

campaign_presence = Table(
    "campaign_presence",
    metadata,
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("is_online", Integer, nullable=False),
    Column("last_seen_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_campaign_presence_campaign_online", "campaign_id", "is_online", "last_seen_at"),
    Index("idx_campaign_presence_user", "user_id"),
)

password_reset_tokens = Table(
    "password_reset_tokens",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("token_hash", _STR, nullable=False, unique=True),
    Column("created_at", Integer, nullable=False),
    Column("expires_at", Integer, nullable=False),
    Column("used_at", Integer, nullable=True),
    Index("idx_password_reset_tokens_user_id", "user_id"),
    Index("idx_password_reset_tokens_expires_at", "expires_at"),
)

auth_attempts = Table(
    "auth_attempts",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("action", _STR, nullable=False),
    Column("attempt_key", _STR, nullable=False),
    Column("success", Integer, nullable=False),
    Column("created_at", Integer, nullable=False),
    Index("idx_auth_attempts_action_key_created", "action", "attempt_key", "created_at"),
)


                                                                              

campaigns = Table(
    "campaigns",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("owner_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("title", _STR, nullable=False),
    Column("description", Text, nullable=False, default=""),
    Column("active_system_id", _STR, nullable=True),
    Column("initial_state_json", Text, nullable=False),
    Column("persistent_state_json", Text, nullable=False),
    Column("state_version", Integer, nullable=False, server_default=text("1")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_campaigns_owner_user_id", "owner_user_id"),
)

campaign_members = Table(
    "campaign_members",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("role", _STR, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    UniqueConstraint("campaign_id", "user_id"),
    Index("idx_campaign_members_campaign_id", "campaign_id"),
    Index("idx_campaign_members_user_id", "user_id"),
)

combat_states = Table(
    "combat_states",
    metadata,
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("is_active", Integer, nullable=False, server_default=text("0")),
    Column("round_number", Integer, nullable=False, server_default=text("0")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
)

combat_encounters = Table(
    "combat_encounters",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("scene_id", _ID, nullable=True),
    Column("status", _STR, nullable=False, server_default=text("'active'")),
    Column("mode", _STR, nullable=False, server_default=text("'manual'")),
    Column("strategy", _STR, nullable=False, server_default=text("'manual'")),
    Column("round_number", Integer, nullable=False, server_default=text("1")),
    Column("turn_index", Integer, nullable=False, server_default=text("0")),
    Column("phase", _STR, nullable=False, server_default=text("'combat.start'")),
    Column("settings_json", Text, nullable=False, default="{}"),
    Column("created_by_user_id", _ID, nullable=False),
    Column("started_at", Integer, nullable=True),
    Column("ended_at", Integer, nullable=True),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_combat_encounters_campaign_status", "campaign_id", "status"),
)

combat_participants = Table(
    "combat_participants",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("combat_id", _ID, ForeignKey("combat_encounters.id", ondelete="CASCADE"), nullable=False),
    Column("actor_id", _ID, ForeignKey("actors_core.id", ondelete="SET NULL"), nullable=True),
    Column("token_id", _ID, nullable=True),
    Column("name", _STR, nullable=False),
    Column("initiative_label", _STR, nullable=False, server_default=text("''")),
    Column("initiative_value", Float, nullable=True),
    Column("initiative_data_json", Text, nullable=False, default="{}"),
    Column("sort_key", Float, nullable=False, server_default=text("0")),
    Column("group_key", _STR, nullable=True),
    Column("visible_to_players", Integer, nullable=False, server_default=text("1")),
    Column("defeated", Integer, nullable=False, server_default=text("0")),
    Column("metadata_json", Text, nullable=False, default="{}"),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_combat_participants_combat", "combat_id", "sort_key"),
)

combat_events = Table(
    "combat_events",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("combat_id", _ID, ForeignKey("combat_encounters.id", ondelete="CASCADE"), nullable=False),
    Column("round_number", Integer, nullable=False, server_default=text("1")),
    Column("turn_index", Integer, nullable=False, server_default=text("0")),
    Column("participant_id", _ID, nullable=True),
    Column("actor_id", _ID, nullable=True),
    Column("event_type", _STR, nullable=False),
    Column("payload_json", Text, nullable=False, default="{}"),
    Column("created_at", Integer, nullable=False),
    Index("idx_combat_events_combat", "combat_id", "created_at"),
)

campaign_permission_overrides = Table(
    "campaign_permission_overrides",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("subject_type", _STR, nullable=False),
    Column("subject_id", _STR, nullable=False),
    Column("permission_key", _STR, nullable=False),
    Column("effect", _STR, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    UniqueConstraint("campaign_id", "subject_type", "subject_id", "permission_key"),
    Index(
        "idx_campaign_permission_overrides_campaign_subject",
        "campaign_id",
        "subject_type",
        "subject_id",
    ),
    Index("idx_campaign_permission_overrides_permission", "permission_key"),
)

campaign_invitations = Table(
    "campaign_invitations",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("invited_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("invited_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("role", _STR, nullable=False),
    Column("status", _STR, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Column("responded_at", Integer, nullable=True),
    Index("idx_campaign_invitations_invited_user_status", "invited_user_id", "status", "created_at"),
    Index("idx_campaign_invitations_campaign_status", "campaign_id", "status", "created_at"),
    Index("idx_campaign_invitations_invited_by", "invited_by_user_id"),
)

                                                                              
                                                                              
                                                                           
                                                                           
                                                              
streamer_links = Table(
    "streamer_links",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("token", _STR, nullable=False, unique=True),
    Column("guest_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("created_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("expires_at", Integer, nullable=False),
    Column("revoked_at", Integer, nullable=True),
    Index("idx_streamer_links_campaign", "campaign_id"),
    Index("idx_streamer_links_token", "token"),
)

campaign_delete_codes = Table(
    "campaign_delete_codes",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("requested_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("code_hash", _STR, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("expires_at", Integer, nullable=False),
    Column("used_at", Integer, nullable=True),
    Index("idx_campaign_delete_codes_campaign_id", "campaign_id"),
    Index("idx_campaign_delete_codes_expires_at", "expires_at"),
)

campaign_system_history = Table(
    "campaign_system_history",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("previous_system_id", _STR, nullable=True),
    Column("next_system_id", _STR, nullable=True),
    Column("changed_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", Integer, nullable=False),
    Index("idx_campaign_system_history_campaign_id", "campaign_id"),
)

systems_installed = Table(
    "systems_installed",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("package_id", _STR, nullable=False),
    Column("name", _STR, nullable=False),
    Column("version", _STR, nullable=False),
    Column("api_version", _STR, nullable=False),
    Column("package_dir", Text, nullable=False),
    Column("manifest_json", Text, nullable=False),
    Column("status", _STR, nullable=False, server_default=text("'installed'")),
    Column("validation_errors_json", Text, nullable=False, default="[]"),
    Column("installed_by_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("installed_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
)


modules_installed = Table(
    "modules_installed",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("package_id", _STR, nullable=False, unique=True),
    Column("name", _STR, nullable=False),
    Column("version", _STR, nullable=False),
    Column("api_version", _STR, nullable=False),
    Column("package_dir", Text, nullable=False),
    Column("manifest_json", Text, nullable=False),
    Column("status", _STR, nullable=False, server_default=text("'installed'")),
    Column("validation_errors_json", Text, nullable=False, default="[]"),
    Column("package_sha256", String(64), nullable=True),
    Column("installed_by_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("installed_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
)


campaign_modules = Table(
    "campaign_modules",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("module_id", _ID, ForeignKey("modules_installed.id", ondelete="CASCADE"), nullable=False),
    Column("enabled_by_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    UniqueConstraint("campaign_id", "module_id"),
    Index("idx_campaign_modules_campaign", "campaign_id"),
    Index("idx_campaign_modules_module", "module_id"),
)

module_settings = Table(
    "module_settings",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("module_id", _ID, ForeignKey("modules_installed.id", ondelete="CASCADE"), nullable=False),
    Column("scope", String(32), nullable=False),
                                                                                        
                                                                                      
    Column("subject_id", _ID, nullable=False, server_default=text("''")),
    Column("setting_key", String(128), nullable=False),
    Column("value_json", Text, nullable=False),
    Column("updated_by_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    UniqueConstraint("module_id", "scope", "subject_id", "setting_key"),
    Index("idx_module_settings_module_scope", "module_id", "scope"),
    Index("idx_module_settings_subject", "scope", "subject_id"),
)


                                                                              

actors_core = Table(
    "actors_core",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("system_id", _STR, nullable=False),
    Column("type", _STR, nullable=False),
    Column("name", _STR, nullable=False),
    Column("folder_id", _ID, nullable=True),
    Column("portrait_asset_id", _ID, nullable=True),
    Column("token_asset_id", _ID, nullable=True),
    Column("default_token_config_json", Text, nullable=True),
    Column("permissions_json", Text, nullable=False, default="{}"),
    Column("external_data_ref", Text, nullable=True),
    Column("status", _STR, nullable=False, server_default=text("'active'")),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("created_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_actors_core_campaign", "campaign_id", "status"),
    Index("idx_actors_core_campaign_system", "campaign_id", "system_id"),
)

actor_folders = Table(
    "actor_folders",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("created_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("name", _STR, nullable=False),
    Column("parent_id", _ID, nullable=True),
    Column("color", _STR, nullable=True),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_actor_folders_campaign_id", "campaign_id"),
)

actor_owners = Table(
    "actor_owners",
    metadata,
    Column("actor_id", _ID, ForeignKey("actors_core.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Index("idx_actor_owners_user_id", "user_id"),
)

actor_permissions = Table(
    "actor_permissions",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("actor_id", _ID, ForeignKey("actors_core.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("can_view", Integer, nullable=False),
    Column("can_edit", Integer, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    UniqueConstraint("actor_id", "user_id"),
    Index("idx_actor_permissions_actor_id", "actor_id"),
    Index("idx_actor_permissions_user_id", "user_id"),
)


                                                                              

items_core = Table(
    "items_core",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("system_id", _STR, nullable=False),
    Column("type", _STR, nullable=False),
    Column("name", _STR, nullable=False),
    Column("folder_id", _ID, nullable=True),
    Column("portrait_asset_id", _ID, nullable=True),
    Column("permissions_json", Text, nullable=False, default="{}"),
    Column("external_data_ref", Text, nullable=True),
    Column("status", _STR, nullable=False, server_default=text("'active'")),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("created_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_items_core_campaign", "campaign_id", "status"),
    Index("idx_items_core_campaign_system", "campaign_id", "system_id"),
)

item_folders = Table(
    "item_folders",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("created_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("name", _STR, nullable=False),
    Column("parent_id", _ID, nullable=True),
    Column("color", _STR, nullable=True),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_item_folders_campaign_id", "campaign_id"),
)

item_owners = Table(
    "item_owners",
    metadata,
    Column("item_id", _ID, ForeignKey("items_core.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Index("idx_item_owners_user_id", "user_id"),
)

item_permissions = Table(
    "item_permissions",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("item_id", _ID, ForeignKey("items_core.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("can_view", Integer, nullable=False),
    Column("can_edit", Integer, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    UniqueConstraint("item_id", "user_id"),
    Index("idx_item_permissions_item_id", "item_id"),
    Index("idx_item_permissions_user_id", "user_id"),
)


                                                                              

journal_folders = Table(
    "journal_folders",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("created_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("name", _STR, nullable=False),
    Column("parent_id", _ID, nullable=True),
    Column("color", _STR, nullable=True),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_journal_folders_campaign_id", "campaign_id"),
)

journals = Table(
    "journals",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("folder_id", _ID, ForeignKey("journal_folders.id", ondelete="SET NULL"), nullable=True),
    Column("created_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("type", _STR, nullable=False),
    Column("title", _STR, nullable=False),
    Column("visibility", _STR, nullable=False, server_default=text("'private'")),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("data_json", Text, nullable=False, default="{}"),
    Column("content_markdown", Text, nullable=False, default=""),
    Column("quest_provider", _STR, nullable=False, server_default=text("''")),
    Column("quest_reward", Text, nullable=False, default=""),
    Column("quest_progress_current", Integer, nullable=False, server_default=text("0")),
    Column("quest_progress_max", Integer, nullable=False, server_default=text("1")),
    Column("status", _STR, nullable=False, server_default=text("'active'")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_journals_campaign_status", "campaign_id", "status", "created_at"),
    Index("idx_journals_folder_id", "folder_id"),
)

journal_owners = Table(
    "journal_owners",
    metadata,
    Column("journal_id", _ID, ForeignKey("journals.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Index("idx_journal_owners_user_id", "user_id"),
)

journal_permissions = Table(
    "journal_permissions",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("journal_id", _ID, ForeignKey("journals.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("can_view", Integer, nullable=False),
    Column("can_edit", Integer, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    UniqueConstraint("journal_id", "user_id"),
    Index("idx_journal_permissions_journal_id", "journal_id"),
    Index("idx_journal_permissions_user_id", "user_id"),
)

quest_board_entries = Table(
    "quest_board_entries",
    metadata,
    Column("board_id", _ID, ForeignKey("journals.id", ondelete="CASCADE"), primary_key=True),
    Column("quest_id", _ID, ForeignKey("journals.id", ondelete="CASCADE"), primary_key=True),
    Column("sort_order", Integer, nullable=False, server_default=text("0")),
    Column("pinned", Integer, nullable=False, server_default=text("0")),
    Column("visibility", _STR, nullable=False, server_default=text("'public_card'")),
    Column("created_at", Integer, nullable=False),
    Index("idx_quest_board_entries_board", "board_id", "sort_order"),
    Index("idx_quest_board_entries_quest", "quest_id"),
)

journal_assets = Table(
    "journal_assets",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("journal_id", _ID, ForeignKey("journals.id", ondelete="SET NULL"), nullable=True),
    Column("owner_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("purpose", _STR, nullable=False, server_default=text("'journal_image'")),
    Column("filename", Text, nullable=False),
    Column("content_type", _STR, nullable=False),
    Column("byte_size", Integer, nullable=False),
    Column("width", Integer, nullable=True),
    Column("height", Integer, nullable=True),
    Column("storage_path", Text, nullable=False),
    Column("hash", _STR, nullable=False),
    Column("created_at", Integer, nullable=False),
    Index("idx_journal_assets_campaign", "campaign_id"),
    Index("idx_journal_assets_journal", "journal_id"),
)


                                                                              

scene_groups = Table(
    "scene_groups",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("name", _STR, nullable=False),
    Column("color", _STR, nullable=False, server_default=text("'#8ea8ff'")),
    Column("sort_order", Integer, nullable=False, server_default=text("0")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_scene_groups_campaign_order", "campaign_id", "sort_order", "created_at"),
)

scenes = Table(
    "scenes",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("group_id", _ID, ForeignKey("scene_groups.id", ondelete="SET NULL"), nullable=True),
    Column("name", _STR, nullable=False),
    Column("status", _STR, nullable=False),
    Column("visibility", _STR, nullable=False, server_default=text("'players'")),
    Column("active", Integer, nullable=False),
    Column("width", Integer, nullable=False),
    Column("height", Integer, nullable=False),
    Column("tile_size", Integer, nullable=False),
    Column("chunk_size", Integer, nullable=False),
    Column("grid_visible", Integer, nullable=False, server_default=text("1")),
    Column("grid_color", _STR, nullable=False, server_default=text("'#6fddb4'")),
    Column("grid_opacity", Float, nullable=False, server_default=text("0.4")),
    Column("image_scale", Float, nullable=False, server_default=text("1.0")),
    Column("start_world_x", Float, nullable=False, server_default=text("0.0")),
    Column("start_world_y", Float, nullable=False, server_default=text("0.0")),
    Column("start_zoom", Float, nullable=False, server_default=text("1.0")),
    Column("tile_table_version", Integer, nullable=False),
    Column("scene_epoch", Integer, nullable=False, server_default=text("1")),
    Column("fog_enabled", Integer, nullable=False, server_default=text("0")),
    Column("fog_mask", LargeBinary, nullable=True),
    Column("fog_baseline", _STR, nullable=False, server_default=text("'hide_all'")),
    Column("fog_ops_json", Text, nullable=False, default="[]"),
    Column("fog_version", Integer, nullable=False, server_default=text("0")),
    Column("board_area_markers_json", Text, nullable=False, default="[]"),
    Column("board_version", Integer, nullable=False, server_default=text("1")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_scenes_campaign_id", "campaign_id", "created_at"),
    Index("idx_scenes_group_id", "group_id"),
)

scene_layers = Table(
    "scene_layers",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column("name", _STR, nullable=False),
    Column("kind", _STR, nullable=False),
    Column("visibility", _STR, nullable=False),
    Column("display_order", Integer, nullable=False),
    Column("encoding", _STR, nullable=False),
    Column("tile_table_version", Integer, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_scene_layers_scene_order", "scene_id", "display_order"),
)

scene_assets = Table(
    "scene_assets",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column("kind", _STR, nullable=False),
    Column("storage_path", Text, nullable=False),
    Column("hash", _STR, nullable=False),
    Column("byte_size", Integer, nullable=False),
    Column("width", Integer, nullable=True),
    Column("height", Integer, nullable=True),
    Column("content_type", _STR, nullable=True),
    Column("created_at", Integer, nullable=False),
    Index("idx_scene_assets_scene_kind", "scene_id", "kind"),
)

scene_tiles = Table(
    "scene_tiles",
    metadata,
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), primary_key=True),
    Column("layer_id", _ID, ForeignKey("scene_layers.id", ondelete="CASCADE"), primary_key=True),
    Column("tile_ref", Integer, primary_key=True),
    Column("asset_id", _ID, ForeignKey("scene_assets.id", ondelete="CASCADE"), nullable=False),
    Column("tx", Integer, nullable=False),
    Column("ty", Integer, nullable=False),
    Column("width", Integer, nullable=False),
    Column("height", Integer, nullable=False),
    Column("hash", _STR, nullable=False),
    Column("byte_size", Integer, nullable=False),
    Column("created_at", Integer, nullable=False),
    Index("idx_scene_tiles_layer_coord", "layer_id", "tx", "ty"),
)

scene_chunks = Table(
    "scene_chunks",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column("layer_id", _ID, ForeignKey("scene_layers.id", ondelete="CASCADE"), nullable=False),
    Column("cx", Integer, nullable=False),
    Column("cy", Integer, nullable=False),
    Column("version", Integer, nullable=False),
    Column("hash", _STR, nullable=False),
    Column("byte_size", Integer, nullable=False),
    Column("encoding", _STR, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    UniqueConstraint("layer_id", "cx", "cy"),
    Index("idx_scene_chunks_scene_layer_coord", "scene_id", "layer_id", "cx", "cy"),
)


                                                                              

tokens = Table(
    "tokens",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column("actor_id", _ID, ForeignKey("actors_core.id", ondelete="SET NULL"), nullable=True),
    Column("grid_x", Integer, nullable=False, server_default=text("0")),
    Column("grid_y", Integer, nullable=False, server_default=text("0")),
    Column("width_cells", Integer, nullable=False, server_default=text("1")),
    Column("height_cells", Integer, nullable=False, server_default=text("1")),
    Column("rotation", Float, nullable=False, server_default=text("0.0")),
    Column("name", _STR, nullable=True),
    Column("token_asset_url", Text, nullable=True),
    Column("visible", Integer, nullable=False, server_default=text("1")),
    Column("hidden", Integer, nullable=False, server_default=text("0")),
    Column("locked", Integer, nullable=False, server_default=text("0")),
    Column("disposition", _STR, nullable=False, server_default=text("'neutral'")),
    Column("actor_link_mode", _STR, nullable=False, server_default=text("'unlinked'")),
    Column("overrides_json", Text, nullable=False, default="{}"),
    Column("controlled_by_user_ids_json", Text, nullable=False, default="[]"),
    Column("controlled_by_role", _STR, nullable=False, server_default=text("'gm'")),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_tokens_scene_id", "scene_id", "created_at"),
    Index("idx_tokens_actor_id", "actor_id"),
    Index("idx_tokens_scene_grid", "scene_id", "grid_x", "grid_y"),
)

token_conditions = Table(
    "token_conditions",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("token_id", _ID, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False),
    Column("condition_id", _STR, nullable=False),
    Column("label", _STR, nullable=False),
    Column("icon", _STR, nullable=True),
    Column("duration", Integer, nullable=True),
    Column("source", _STR, nullable=True),
    Column("kind", _STR, nullable=False, server_default=text("'neutral'")),
    Column("visible_to", _STR, nullable=False, server_default=text("'everyone'")),
    Column("created_at", Integer, nullable=False),
    UniqueConstraint("token_id", "condition_id"),
    Index("idx_token_conditions_token_id", "token_id"),
)


                                                                              

chat_messages = Table(
    "chat_messages",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("author_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("author_name", _STR, nullable=False),
    Column("author_role", _STR, nullable=False),
    Column("kind", _STR, nullable=False),
    Column("content", Text, nullable=True),
    Column("expression", Text, nullable=True),
    Column("groups_json", Text, nullable=True),
    Column("modifier", Integer, nullable=True),
    Column("total", Integer, nullable=True),
    Column("visibility", _STR, nullable=False),
    Column("metadata_json", Text, nullable=False, default="{}"),
    Column("created_at", Integer, nullable=False),
    Index("idx_chat_messages_campaign_created", "campaign_id", "created_at"),
)

transport_messages = Table(
    "transport_messages",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("target_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("room_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True),
    Column("event", _STR, nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("expires_at", Integer, nullable=False),
    Column("consumed_at", Integer, nullable=True),
    Index(
        "idx_transport_messages_target_user_pending",
        "target_user_id",
        "consumed_at",
        "expires_at",
        "created_at",
    ),
    Index("idx_transport_messages_room_id", "room_id"),
    Index("idx_transport_messages_event", "event"),
    Index("idx_transport_messages_expires_at", "expires_at"),
)

room_event_log = Table(
    "room_event_log",
    metadata,
    Column("seq", BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True),
    Column("id", _ID, nullable=False, unique=True),
    Column("room_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("event", _STR, nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("expires_at", Integer, nullable=False),
    Index("idx_room_event_log_room_seq", "room_id", "seq"),
    Index("idx_room_event_log_expires_at", "expires_at"),
)


                                                                                

schema_migrations = Table(
    "schema_migrations",
    metadata,
    Column("id", _STR, primary_key=True),
    Column("applied_at", _STR, nullable=False),
)
