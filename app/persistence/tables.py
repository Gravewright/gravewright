"""Portable schema as SQLAlchemy Core ``MetaData``.

The base CREATE TABLE shape plus every applied migration, expressed in a dialect
agnostic way so the same definitions create the database on SQLite, PostgreSQL
and MySQL.

Type policy (important for MySQL portability):
- ``String(n)`` (→ VARCHAR) for every identifier, hash, key, status and other
  short value, because MySQL cannot index/PK a TEXT/BLOB column without a length.
- ``Text`` only for large, never-indexed payloads (JSON blobs, markdown, paths).
- ``LargeBinary`` for BLOBs, ``BigInteger`` for the autoincrement event sequence.

The one construct that is genuinely not portable: the partial UNIQUE index
``scenes(campaign_id) WHERE active = 1``: is created out of band by the schema
bootstrap / migration for SQLite/PostgreSQL only (see ``app.persistence.schema``).
"""

from __future__ import annotations

from sqlalchemy import BigInteger
from sqlalchemy import CheckConstraint
from sqlalchemy import Column
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import MetaData
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy import text

from app.domain.campaigns import InvitationStatus
from app.domain.permissions.permissions import PermissionEffect
from app.domain.roles import PlayerRole

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_N_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


def enum_check(column: str, enum, name: str) -> CheckConstraint:
    """A portable ``column IN (...)`` check whose allowed set is the domain enum.

    Centralizing the value set on the enum keeps the database constraint and the
    application's validation from drifting apart (maintenance plan, Etapa 6).
    """
    allowed = ", ".join(f"'{member.value}'" for member in enum)
    return CheckConstraint(f"{column} IN ({allowed})", name=name)


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


    Column("vision_mode", _STR, nullable=False, server_default=text("'cinematic'")),
    Column("ping_color", _STR, nullable=False, server_default=text("'#f2c679'")),
    Column("package_onboarding_seen", Integer, nullable=False, server_default=text("0")),
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

campaign_lobby_states = Table(
    "campaign_lobby_states",
    metadata,
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("is_ready", Integer, nullable=False, server_default=text("0")),
    Column("selected_actor_id", _ID, ForeignKey("actors_core.id", ondelete="SET NULL"), nullable=True),
    Column("assets_state", _STR, nullable=False, server_default=text("'unknown'")),
    Column("updated_at", Integer, nullable=False),
    Index("idx_campaign_lobby_states_campaign_ready", "campaign_id", "is_ready"),
)

campaign_gm_onboarding = Table(
    "campaign_gm_onboarding",
    metadata,
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("dismissed_at", Integer, nullable=True),
    Column("updated_at", Integer, nullable=False),
    Index("idx_campaign_gm_onboarding_user", "user_id", "updated_at"),
)

campaign_player_onboarding = Table(
    "campaign_player_onboarding",
    metadata,
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("shown_at", Integer, nullable=False),
    Index("idx_campaign_player_onboarding_user", "user_id", "shown_at"),
)

campaign_snapshots = Table(
    "campaign_snapshots",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("created_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("name", _STR, nullable=False),
    Column("description", Text, nullable=False, default=""),
    Column("kind", _STR, nullable=False, server_default=text("'manual'")),
    Column("format_version", Integer, nullable=False),
    Column("manifest_json", Text, nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("checksum", String(64), nullable=False),
    Column("created_at", Integer, nullable=False),
    Index("idx_campaign_snapshots_campaign_created", "campaign_id", "created_at"),
)

audit_events = Table(
    "audit_events",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("actor_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("catalog_version", Integer, nullable=False),
    Column("event_type", _STR, nullable=False),
    Column("subject_type", _STR, nullable=True),
    Column("subject_id", _ID, nullable=True),
    Column("action", _STR, nullable=False),
    Column("result", _STR, nullable=False),
    Column("metadata_json", Text, nullable=False),
    Column("created_at", Integer, nullable=False),
    Index("idx_audit_events_campaign_created", "campaign_id", "created_at"),
    Index("idx_audit_events_campaign_type_created", "campaign_id", "event_type", "created_at"),
)

handout_grants = Table(
    "handout_grants",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("resource_type", _STR, nullable=False),
    Column("resource_id", _ID, nullable=False),
    Column("subject_type", _STR, nullable=False),
    Column("subject_id", _ID, nullable=False, server_default=text("''")),
    Column("created_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("revoked_at", Integer, nullable=True),
    UniqueConstraint("campaign_id", "resource_type", "resource_id", "subject_type", "subject_id"),
    Index("idx_handout_grants_resource", "campaign_id", "resource_type", "resource_id"),
    Index("idx_handout_grants_subject", "campaign_id", "subject_type", "subject_id", "revoked_at"),
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
    enum_check("role", PlayerRole, "role"),
    Index("idx_campaign_members_campaign_id", "campaign_id"),
    Index("idx_campaign_members_user_id", "user_id"),
)

combat_encounters = Table(
    "combat_encounters",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("scene_id", _ID, nullable=True),
    Column("status", _STR, nullable=False, server_default=text("'active'")),
    Column("round_number", Integer, nullable=False, server_default=text("1")),
    Column("turn_index", Integer, nullable=False, server_default=text("0")),
    Column("created_by_user_id", _ID, nullable=False),
    Column("started_at", Integer, nullable=True),
    Column("ended_at", Integer, nullable=True),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_combat_encounters_campaign_status", "campaign_id", "status"),
)






combat_combatants = Table(
    "combat_combatants",
    metadata,
    Column("id", _ID, primary_key=True),
    Column(
        "combat_id", _ID, ForeignKey("combat_encounters.id", ondelete="CASCADE"), nullable=False
    ),
    Column("actor_id", _ID, ForeignKey("actors_core.id", ondelete="SET NULL"), nullable=True),
    Column("token_id", _ID, nullable=True),
    Column("name", _STR, nullable=False),
    Column("initiative", _STR, nullable=True),
    Column("sort_value", Float, nullable=True),
    Column("tie_break", Float, nullable=False, server_default=text("0")),
    Column("hidden", Integer, nullable=False, server_default=text("0")),
    Column("defeated", Integer, nullable=False, server_default=text("0")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_combat_combatants_combat", "combat_id", "created_at"),
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
    enum_check("effect", PermissionEffect, "effect"),
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
    enum_check("role", PlayerRole, "role"),
    enum_check("status", InvitationStatus, "status"),
    Index(
        "idx_campaign_invitations_invited_user_status", "invited_user_id", "status", "created_at"
    ),
    Index("idx_campaign_invitations_campaign_status", "campaign_id", "status", "created_at"),
    Index("idx_campaign_invitations_invited_by", "invited_by_user_id"),
)


campaign_join_codes = Table(
    "campaign_join_codes",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("code_hash", String(64), nullable=False, unique=True),
    Column("created_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("role", _STR, nullable=False, server_default=text("'player'")),
    Column("max_uses", Integer, nullable=True),
    Column("use_count", Integer, nullable=False, server_default=text("0")),
    Column("expires_at", Integer, nullable=False),
    Column("revoked_at", Integer, nullable=True),
    Column("last_used_at", Integer, nullable=True),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    CheckConstraint("role = 'player'", name="role_player"),
    CheckConstraint("use_count >= 0", name="use_count_nonnegative"),
    CheckConstraint("max_uses IS NULL OR max_uses > 0", name="max_uses_positive"),
    Index(
        "idx_campaign_join_codes_campaign_state",
        "campaign_id",
        "revoked_at",
        "expires_at",
    ),
    Index(
        "uq_campaign_join_codes_active_campaign",
        "campaign_id",
        unique=True,
        sqlite_where=text("revoked_at IS NULL"),
        postgresql_where=text("revoked_at IS NULL"),
    ),
)


campaign_join_code_redemptions = Table(
    "campaign_join_code_redemptions",
    metadata,
    Column("id", _ID, primary_key=True),
    Column(
        "join_code_id",
        _ID,
        ForeignKey("campaign_join_codes.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("redeemed_at", Integer, nullable=False),
    UniqueConstraint("join_code_id", "user_id"),
    Index(
        "idx_campaign_join_code_redemptions_campaign_user",
        "campaign_id",
        "user_id",
    ),
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







installed_packages = Table(
    "installed_packages",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("kind", _STR, nullable=False),
    Column("name", _STR, nullable=False, server_default=text("''")),
    Column("version", _STR, nullable=False, server_default=text("''")),
    Column("status", _STR, nullable=False, server_default=text("'installed'")),
    Column("package_dir", Text, nullable=False),
    Column("manifest_json", Text, nullable=False),
    Column("compatibility_status", _STR, nullable=False, server_default=text("'unverified'")),
    Column("validation_errors_json", Text, nullable=False, default="[]"),
    Column("package_sha256", String(64), nullable=True),



    Column("manifest_hash", String(64), nullable=True),
    Column("last_validated_at", Integer, nullable=True),
    Column("last_validation_status", _STR, nullable=True),
    Column("installed_by_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("installed_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Column("enabled_at", Integer, nullable=True),
    Column("disabled_at", Integer, nullable=True),
    Index("idx_installed_packages_kind", "kind"),
)


campaign_packages = Table(
    "campaign_packages",
    metadata,
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column(
        "package_id", _ID, ForeignKey("installed_packages.id", ondelete="CASCADE"), nullable=False
    ),
    Column("activation_role", _STR, nullable=False),
    Column("status", _STR, nullable=False, server_default=text("'active'")),
    Column("load_order", Integer, nullable=False, server_default=text("0")),
    Column("enabled_by_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("enabled_at", Integer, nullable=False),
    Column("disabled_at", Integer, nullable=True),
    PrimaryKeyConstraint("campaign_id", "package_id"),
    Index("idx_campaign_packages_campaign", "campaign_id"),
    Index("idx_campaign_packages_role", "campaign_id", "activation_role"),
)


package_settings = Table(
    "package_settings",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("package_id", _ID, nullable=False),


    Column("campaign_id", _ID, nullable=False, server_default=text("''")),
    Column("user_id", _ID, nullable=False, server_default=text("''")),
    Column("setting_key", String(128), nullable=False),
    Column("value_json", Text, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    UniqueConstraint("package_id", "campaign_id", "user_id", "setting_key"),
    Index("idx_package_settings_package", "package_id"),
    Index("idx_package_settings_campaign", "campaign_id"),
)


package_content_imports = Table(
    "package_content_imports",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("package_id", _ID, nullable=False),
    Column("content_pack_id", _STR, nullable=False),
    Column("content_pack_type", _STR, nullable=False),
    Column("imported_by_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("imported_at", Integer, nullable=False),
    Index("idx_package_content_imports_campaign", "campaign_id"),
    Index("idx_package_content_imports_package", "package_id"),
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
    Column("folder_id", _ID, nullable=True),
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
    Index("idx_journal_assets_folder", "campaign_id", "folder_id"),
)


asset_folders = Table(
    "asset_folders",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("parent_id", _ID, nullable=True),
    Column("name", _STR, nullable=False),
    Column("sort_order", Integer, nullable=False, server_default=text("0")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_asset_folders_campaign_parent", "campaign_id", "parent_id", "sort_order", "name"),
)




library_assets = Table(
    "library_assets",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("owner_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("folder_id", _ID, nullable=True),
    Column("filename", Text, nullable=False),
    Column("content_type", _STR, nullable=False),
    Column("byte_size", Integer, nullable=False),
    Column("width", Integer, nullable=True),
    Column("height", Integer, nullable=True),
    Column("storage_path", Text, nullable=False),
    Column("hash", _STR, nullable=False),
    Column("created_at", Integer, nullable=False),
    Index("idx_library_assets_campaign", "campaign_id", "created_at"),
    Index("idx_library_assets_folder", "campaign_id", "folder_id"),
)


pdf_annotations = Table(
    "pdf_annotations",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("document_id", _ID, ForeignKey("library_assets.id", ondelete="CASCADE"), nullable=False),
    Column("author_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("page", Integer, nullable=False),
    Column("region_json", Text, nullable=False),
    Column("text", Text, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_pdf_annotations_document_page", "campaign_id", "document_id", "page", "created_at"),
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
    Column("grid_size", Float, nullable=False, server_default=text("70")),
    Column("scene_format_version", Integer, nullable=False, server_default=text("1")),
    Column("raster_selection_mode", _STR, nullable=False, server_default=text("'legacy'")),
    Column("raster_policy_version", Integer, nullable=False, server_default=text("0")),
    Column("chunk_size", Integer, nullable=False),
    Column("grid_visible", Integer, nullable=False, server_default=text("1")),
    Column("grid_color", _STR, nullable=False, server_default=text("'#6fddb4'")),
    Column("grid_opacity", Float, nullable=False, server_default=text("0.4")),
    Column("grid_offset_x", Float, nullable=False, server_default=text("0.0")),
    Column("grid_offset_y", Float, nullable=False, server_default=text("0.0")),
    Column("darkness", Float, nullable=False, server_default=text("0.0")),
    # Regime de luz da cena: "none" (mapa aberto), "dynamic" (escuridao + focos)
    # ou "manual" (nevoa pintada a mao). `darkness` guarda so a intensidade
    # configurada; `lights_out` diz se ela esta valendo agora.
    Column("lighting_mode", _STR, nullable=False, server_default=text("'none'")),
    Column("lights_out", Integer, nullable=False, server_default=text("1")),
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
    Column("soundscape_id", _ID, nullable=True),
    Column("sound_version", Integer, nullable=False, server_default=text("1")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_scenes_campaign_id", "campaign_id", "created_at"),
    Index("idx_scenes_group_id", "group_id"),
)

scene_walls = Table(
    "scene_walls", metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column("kind", _STR, nullable=False, server_default=text("'wall'")),
    Column("door_state", _STR, nullable=False, server_default=text("'closed'")),
    Column("movement_behavior", _STR, nullable=False, server_default=text("'block'")),
    Column("vision_behavior", _STR, nullable=False, server_default=text("'block'")),
    Column("light_behavior", _STR, nullable=False, server_default=text("'block'")),
    Column("sound_behavior", _STR, nullable=False, server_default=text("'block'")),
    Column("presentation", _STR, nullable=False, server_default=text("'normal'")),
    Column("discovered", Integer, nullable=False, server_default=text("0")),
    Column("x1", Float, nullable=False), Column("y1", Float, nullable=False),
    Column("x2", Float, nullable=False), Column("y2", Float, nullable=False),
    Column("vertical_bottom", Float, nullable=True),
    Column("vertical_top", Float, nullable=True),
    Column("created_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False),
    CheckConstraint("kind IN ('wall','door')", name="kind"),
    CheckConstraint("door_state IN ('closed','open','locked')", name="door_state"),
    CheckConstraint("movement_behavior IN ('block','pass')", name="movement_behavior"),
    CheckConstraint("vision_behavior IN ('block','pass')", name="vision_behavior"),
    CheckConstraint("light_behavior IN ('block','pass')", name="light_behavior"),
    CheckConstraint("sound_behavior IN ('block','attenuate','pass')", name="sound_behavior"),
    CheckConstraint("presentation IN ('normal','window','bars','invisible','secret')", name="presentation"),
    Index("idx_scene_walls_scene", "scene_id", "created_at"),
)

scene_lights = Table(
    "scene_lights", metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column("x", Float, nullable=False), Column("y", Float, nullable=False),
    Column("elevation", Float, nullable=False, server_default=text("0.0")),

    Column("bright_radius", Float, nullable=False, server_default=text("2.0")),
    Column("dim_radius", Float, nullable=False, server_default=text("4.0")),
    Column("color", _STR, nullable=False, server_default=text("'#ffd8a8'")),
    Column("intensity", Float, nullable=False, server_default=text("1.0")),
    Column("animation", _STR, nullable=False, server_default=text("'none'")),


    Column("angle", Float, nullable=False, server_default=text("360.0")),
    Column("rotation", Float, nullable=False, server_default=text("0.0")),
    Column("enabled", Integer, nullable=False, server_default=text("1")),
    Column("created_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False),




    CheckConstraint("animation IN ('none','torch','pulse')", name="animation"),
    Index("idx_scene_lights_scene", "scene_id", "created_at"),
)




scene_particles = Table(
    "scene_particles", metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column("x", Float, nullable=False), Column("y", Float, nullable=False),
    Column("kind", _STR, nullable=False, server_default=text("'smoke'")),


    Column("scale", Float, nullable=False, server_default=text("3.0")),


    Column("density", Float, nullable=False, server_default=text("0.6")),
    Column("color", _STR, nullable=False, server_default=text("'#9aa3ad'")),
    Column("enabled", Integer, nullable=False, server_default=text("1")),
    Column("created_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False),
    CheckConstraint("kind IN ('smoke','ember','dust','arcane','rain','snow','firefly','leaves','bubbles','ash','blood','runes')", name="kind"),
    Index("idx_scene_particles_scene", "scene_id", "created_at"),
)





scene_shaders = Table(
    "scene_shaders", metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column("name", _STR, nullable=False, server_default=text("''")),
    Column("source", Text, nullable=False, server_default=text("''")),
    Column("preset_id", _STR, nullable=True),
    Column("preset_schema_version", Integer, nullable=True),
    Column("version", Integer, nullable=False, server_default=text("1")),




    Column("x", Float, nullable=False, server_default=text("0.0")),
    Column("y", Float, nullable=False, server_default=text("0.0")),


    Column("radius", Float, nullable=False, server_default=text("0.0")),


    Column("rotation", Float, nullable=False, server_default=text("0.0")),

    Column("blend_mode", _STR, nullable=False, server_default=text("'normal'")),
    Column("opacity", Float, nullable=False, server_default=text("1.0")),


    Column("intensity", Float, nullable=False, server_default=text("0.6")),
    Column("scale", Float, nullable=False, server_default=text("1.0")),
    Column("speed", Float, nullable=False, server_default=text("1.0")),
    Column("color", _STR, nullable=False, server_default=text("'#8fb6ff'")),
    Column("enabled", Integer, nullable=False, server_default=text("1")),
    Column("created_by_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False),
    Index("idx_scene_shaders_scene", "scene_id", "created_at"),
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
    Column("max_lod", Integer, nullable=False, server_default=text("0")),
    Column("tile_index_version", Integer, nullable=False, server_default=text("1")),
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
    Column("lod", Integer, nullable=False, server_default=text("0")),
    Column("asset_id", _ID, ForeignKey("scene_assets.id", ondelete="CASCADE"), nullable=False),
    Column("tx", Integer, nullable=False),
    Column("ty", Integer, nullable=False),
    Column("width", Integer, nullable=False),
    Column("height", Integer, nullable=False),
    Column("hash", _STR, nullable=False),
    Column("byte_size", Integer, nullable=False),
    Column("created_at", Integer, nullable=False),
    Index("idx_scene_tiles_layer_lod_coord", "layer_id", "lod", "tx", "ty"),
)

scene_chunks = Table(
    "scene_chunks",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column("layer_id", _ID, ForeignKey("scene_layers.id", ondelete="CASCADE"), nullable=False),
    Column("cx", Integer, nullable=False),
    Column("cy", Integer, nullable=False),
    Column("lod", Integer, nullable=False, server_default=text("0")),
    Column("version", Integer, nullable=False),
    Column("hash", _STR, nullable=False),
    Column("byte_size", Integer, nullable=False),
    Column("encoding", _STR, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    UniqueConstraint("layer_id", "lod", "cx", "cy"),
    Index("idx_scene_chunks_scene_layer_lod_coord", "scene_id", "layer_id", "lod", "cx", "cy"),
)


tokens = Table(
    "tokens",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column("actor_id", _ID, ForeignKey("actors_core.id", ondelete="SET NULL"), nullable=True),
    Column("grid_x", Float, nullable=False, server_default=text("0")),
    Column("grid_y", Float, nullable=False, server_default=text("0")),
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
    Column("vision_enabled", Integer, nullable=False, server_default=text("1")),

    Column("vision_range", Float, nullable=False, server_default=text("0.0")),
    Column("elevation", Float, nullable=False, server_default=text("0.0")),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_tokens_scene_id", "scene_id", "created_at"),
    Index("idx_tokens_actor_id", "actor_id"),
    Index("idx_tokens_scene_grid", "scene_id", "grid_x", "grid_y"),
)

scene_zones = Table(
    "scene_zones",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column("zone_type", _STR, nullable=False, server_default=text("'standard'")),
    Column("geometry_json", Text, nullable=False),
    Column("vertical_bottom", Float, nullable=True),
    Column("vertical_top", Float, nullable=True),
    Column("audience_json", Text, nullable=False),
    Column("enabled", Integer, nullable=False, server_default=text("1")),
    Column("tags_json", Text, nullable=False, server_default=text("'[]'")),
    Column("package_id", _STR, nullable=False),
    Column("provider_id", _STR, nullable=True),
    Column("min_x", Float, nullable=False),
    Column("min_y", Float, nullable=False),
    Column("max_x", Float, nullable=False),
    Column("max_y", Float, nullable=False),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_scene_zones_scene_bounds", "scene_id", "enabled", "min_x", "max_x", "min_y", "max_y"),
    Index("idx_scene_zones_package", "package_id"),
)

scene_object_types = Table(
    "scene_object_types", metadata,
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("package_id", _STR, primary_key=True),
    Column("type_id", _STR, primary_key=True),
    Column("definition_json", Text, nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("active", Integer, nullable=False, server_default=text("1")),
    Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False),
    Index("idx_scene_object_types_type", "campaign_id", "type_id", "active"),
)

scene_objects = Table(
    "scene_objects", metadata,
    Column("id", _ID, primary_key=True),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column("type_id", _STR, nullable=False), Column("provider_package_id", _STR, nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("geometry_json", Text, nullable=False), Column("transform_json", Text, nullable=False),
    Column("presentation_json", Text, nullable=False), Column("data_json", Text, nullable=False),
    Column("audience_json", Text, nullable=False), Column("enabled", Integer, nullable=False, server_default=text("1")),
    Column("min_x", Float, nullable=False), Column("min_y", Float, nullable=False),
    Column("max_x", Float, nullable=False), Column("max_y", Float, nullable=False),
    Column("search_text", Text, nullable=False, server_default=text("''")),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False),
    Index("idx_scene_objects_scene_bounds", "scene_id", "enabled", "min_x", "max_x", "min_y", "max_y"),
    Index("idx_scene_objects_provider", "provider_package_id", "type_id"),
)

sdk_semantic_registrations = Table(
    "sdk_semantic_registrations", metadata,
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("package_id", _STR, primary_key=True), Column("registry", _STR, primary_key=True), Column("entry_id", _STR, primary_key=True),
    Column("definition_json", Text, nullable=False), Column("active", Integer, nullable=False, server_default=text("1")),
    Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False),
    Index("idx_sdk_semantic_registry", "campaign_id", "registry", "active"),
)

audio_playbacks = Table(
    "audio_playbacks", metadata, Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False), Column("package_id", _STR, nullable=False),
    Column("owner_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False), Column("asset_json", Text, nullable=False),
    Column("channel", _STR, nullable=False), Column("state", _STR, nullable=False), Column("loop", Integer, nullable=False), Column("gain", Float, nullable=False),
    Column("audience_json", Text, nullable=False), Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=True), Column("anchor_json", Text, nullable=True),
    Column("idempotency_key", _STR, nullable=True), Column("started_at", Integer, nullable=False), Column("expires_at", Integer, nullable=True),
    Column("fade_json", Text, nullable=True), Column("version", Integer, nullable=False, server_default=text("1")), Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False),
    UniqueConstraint("campaign_id", "package_id", "idempotency_key"), Index("idx_audio_projection", "campaign_id", "scene_id", "state"),
)

sounds = Table(
    "sounds", metadata, Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("name", _STR, nullable=False), Column("asset_id", _ID, ForeignKey("library_assets.id", ondelete="RESTRICT"), nullable=False),
    Column("kind", _STR, nullable=False), Column("tags_json", Text, nullable=False, server_default=text("'[]'")),
    Column("default_gain", Float, nullable=False, server_default=text("1")), Column("default_loop", Integer, nullable=False, server_default=text("0")),
    Column("metadata_json", Text, nullable=False, server_default=text("'{}'")), Column("version", Integer, nullable=False, server_default=text("1")),
    Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False), Index("idx_sounds_campaign_kind_name", "campaign_id", "kind", "name"),
)

sound_playlists = Table(
    "sound_playlists", metadata, Column("id", _ID, primary_key=True), Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("name", _STR, nullable=False), Column("entries_json", Text, nullable=False), Column("playback_mode", _STR, nullable=False),
    Column("default_gain", Float, nullable=True), Column("crossfade_ms", Integer, nullable=False, server_default=text("0")),
    Column("version", Integer, nullable=False, server_default=text("1")), Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False),
    Index("idx_sound_playlists_campaign_name", "campaign_id", "name"),
)

soundscapes = Table(
    "soundscapes", metadata, Column("id", _ID, primary_key=True), Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("name", _STR, nullable=False), Column("layers_json", Text, nullable=False), Column("random_pools_json", Text, nullable=False, server_default=text("'[]'")),
    Column("fade_in_ms", Integer, nullable=False, server_default=text("0")), Column("fade_out_ms", Integer, nullable=False, server_default=text("0")),
    Column("version", Integer, nullable=False, server_default=text("1")), Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False),
    Index("idx_soundscapes_campaign_name", "campaign_id", "name"),
)

scene_spatial_sounds = Table(
    "scene_spatial_sounds", metadata, Column("id", _ID, primary_key=True), Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column("sound_id", _ID, ForeignKey("sounds.id", ondelete="RESTRICT"), nullable=False), Column("x", Float, nullable=False), Column("y", Float, nullable=False),
    Column("radius", Float, nullable=False), Column("gain", Float, nullable=False), Column("falloff", _STR, nullable=False), Column("loop", Integer, nullable=False),
    Column("audience_json", Text, nullable=False), Column("constrained_by_walls", Integer, nullable=False, server_default=text("1")),
    Column("enabled", Integer, nullable=False, server_default=text("1")),
    Column("version", Integer, nullable=False, server_default=text("1")), Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False),
    Index("idx_spatial_sounds_scene", "scene_id", "enabled"),
)

user_scene_navigation = Table(
    "user_scene_navigation", metadata,
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True), Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False), Column("reason", Text, nullable=False, server_default=text("''")),
    Column("idempotency_key", _STR, nullable=True), Column("version", Integer, nullable=False, server_default=text("1")), Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False),
)

input_bindings = Table(
    "input_bindings", metadata, Column("user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("package_id", _STR, primary_key=True), Column("command_id", _STR, primary_key=True), Column("binding", _STR, nullable=False),
    Column("version", Integer, nullable=False, server_default=text("1")), Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False),
    UniqueConstraint("user_id", "binding"),
)

# Durable, core-owned SDK semantic instances: workflows, gameplay flows and
# timelines. Definitions remain in sdk_semantic_registrations; this table holds only
# the suspension and recovery state core must own, and never stores executable
# callbacks or source code — a package describes intent, it does not ship behaviour.
sdk_semantic_instances = Table(
    "sdk_semantic_instances", metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("package_id", _STR, nullable=False),
    Column("domain", _STR, nullable=False),
    Column("definition_id", _STR, nullable=False),
    Column("schema_version", Integer, nullable=False),
    Column("owner_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True),
    Column("status", _STR, nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("waiting_on", _STR, nullable=True),
    Column("wake_at", Integer, nullable=True),
    Column("idempotency_key", _STR, nullable=True),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    UniqueConstraint("campaign_id", "package_id", "domain", "idempotency_key"),
    Index("idx_sdk_semantic_instances_campaign_domain", "campaign_id", "domain", "status"),
    Index("idx_sdk_semantic_instances_due", "domain", "status", "wake_at"),
)

declarative_operation_receipts = Table(
    "declarative_operation_receipts", metadata,
    Column("identity", _STR, primary_key=True), Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("package_id", _STR, nullable=False), Column("payload_hash", _STR, nullable=False), Column("result_json", Text, nullable=False),
    Column("created_at", Integer, nullable=False), Index("idx_declarative_receipts_campaign", "campaign_id", "package_id"),
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




card_deck_definitions = Table(
    "card_deck_definitions",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True),
    Column("package_id", _ID, nullable=True),
    Column("owner_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("scope", _STR, nullable=False),
    Column("name", _STR, nullable=False),
    Column("description", Text, nullable=True),
    Column("default_back_asset_id", _ID, nullable=True),
    Column("editable", Integer, nullable=False, server_default=text("1")),
    Column("metadata_json", Text, nullable=False, default="{}"),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_card_deck_definitions_campaign", "campaign_id"),
    Index("idx_card_deck_definitions_package", "package_id"),
    Index("idx_card_deck_definitions_owner", "owner_user_id"),
    Index("idx_card_deck_definitions_scope", "scope"),
)

card_definitions = Table(
    "card_definitions",
    metadata,
    Column("id", _ID, primary_key=True),
    Column(
        "deck_definition_id",
        _ID,
        ForeignKey("card_deck_definitions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("name", _STR, nullable=False),
    Column("subtitle", _STR, nullable=True),
    Column("description", Text, nullable=True),
    Column("front_asset_id", _ID, nullable=False),
    Column("back_asset_id", _ID, nullable=True),
    Column("tags_json", Text, nullable=False, default="[]"),
    Column("metadata_json", Text, nullable=False, default="{}"),
    Column("sort_key", _STR, nullable=True),
    Column("quantity", Integer, nullable=False, server_default=text("1")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_card_definitions_deck", "deck_definition_id"),
)

card_deck_instances = Table(
    "card_deck_instances",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("room_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True),
    Column(
        "deck_definition_id",
        _ID,
        ForeignKey("card_deck_definitions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("owner_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("name", _STR, nullable=False),
    Column("active", Integer, nullable=False, server_default=text("1")),
    Column("metadata_json", Text, nullable=False, default="{}"),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_card_deck_instances_campaign", "campaign_id"),
    Index("idx_card_deck_instances_definition", "deck_definition_id"),
)

card_piles = Table(
    "card_piles",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column(
        "deck_instance_id",
        _ID,
        ForeignKey("card_deck_instances.id", ondelete="CASCADE"),
        nullable=True,
    ),
    Column("owner_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("kind", _STR, nullable=False),
    Column("name", _STR, nullable=False),
    Column("visibility", _STR, nullable=False),
    Column("ordered", Integer, nullable=False, server_default=text("1")),
    Column("metadata_json", Text, nullable=False, default="{}"),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_card_piles_campaign", "campaign_id"),
    Index("idx_card_piles_deck", "deck_instance_id", "kind"),
    Index("idx_card_piles_owner", "owner_user_id"),
)

card_instances = Table(
    "card_instances",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column(
        "deck_instance_id",
        _ID,
        ForeignKey("card_deck_instances.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "card_definition_id",
        _ID,
        ForeignKey("card_definitions.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("current_pile_id", _ID, ForeignKey("card_piles.id", ondelete="SET NULL"), nullable=True),
    Column("current_scene_id", _ID, ForeignKey("scenes.id", ondelete="SET NULL"), nullable=True),
    Column("owner_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("face_state", _STR, nullable=False),
    Column("visibility", _STR, nullable=False),
    Column("locked", Integer, nullable=False, server_default=text("0")),
    Column("metadata_json", Text, nullable=False, default="{}"),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_card_instances_campaign", "campaign_id"),
    Index("idx_card_instances_deck", "deck_instance_id"),
    Index("idx_card_instances_pile", "current_pile_id"),
)

card_pile_entries = Table(
    "card_pile_entries",
    metadata,
    Column("pile_id", _ID, ForeignKey("card_piles.id", ondelete="CASCADE"), nullable=False),
    Column(
        "card_instance_id", _ID, ForeignKey("card_instances.id", ondelete="CASCADE"), nullable=False
    ),
    Column("position", Integer, nullable=False),
    Column("inserted_at", Integer, nullable=False),
    PrimaryKeyConstraint("pile_id", "card_instance_id"),
    UniqueConstraint("pile_id", "position"),
    UniqueConstraint("card_instance_id"),
    Index("idx_card_pile_entries_pile_order", "pile_id", "position"),
)

scene_card_placements = Table(
    "scene_card_placements",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column(
        "card_instance_id", _ID, ForeignKey("card_instances.id", ondelete="CASCADE"), nullable=False
    ),
    Column("owner_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("x", Float, nullable=False),
    Column("y", Float, nullable=False),
    Column("rotation", Float, nullable=False, server_default=text("0")),
    Column("scale", Float, nullable=False, server_default=text("1")),
    Column("z_index", Integer, nullable=False, server_default=text("0")),
    Column("face_state", _STR, nullable=False),
    Column("visibility", _STR, nullable=False),
    Column("locked", Integer, nullable=False, server_default=text("0")),
    Column("metadata_json", Text, nullable=False, default="{}"),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    UniqueConstraint("card_instance_id"),
    Index("idx_scene_card_placements_scene", "scene_id", "z_index"),
    Index("idx_scene_card_placements_card", "card_instance_id"),
)

scene_image_placements = Table(
    "scene_image_placements",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("scene_id", _ID, ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False),
    Column("asset_id", _ID, nullable=False),
    Column("owner_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("x", Float, nullable=False),
    Column("y", Float, nullable=False),
    Column("rotation", Float, nullable=False, server_default=text("0")),
    Column("scale", Float, nullable=False, server_default=text("1")),
    Column("z_index", Integer, nullable=False, server_default=text("0")),
    Column("natural_width", Integer, nullable=False, server_default=text("0")),
    Column("natural_height", Integer, nullable=False, server_default=text("0")),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("locked", Integer, nullable=False, server_default=text("0")),
    Column("gm_only", Integer, nullable=False, server_default=text("0")),


    Column("layer", _STR, nullable=False, server_default=text("'game'")),
    Column("metadata_json", Text, nullable=False, default="{}"),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Index("idx_scene_image_placements_scene", "scene_id", "z_index"),
    Index("idx_scene_image_placements_campaign", "campaign_id"),
)

card_events = Table(
    "card_events",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("room_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True),
    Column("actor_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("event_type", _STR, nullable=False),
    Column("payload_json", Text, nullable=False, default="{}"),
    Column("visibility", _STR, nullable=False),
    Column("created_at", Integer, nullable=False),
    Index("idx_card_events_campaign", "campaign_id", "created_at"),
    Index("idx_card_events_type", "event_type"),
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
    Column(
        "seq", BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    ),
    Column("id", _ID, nullable=False, unique=True),
    Column("room_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("event", _STR, nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("created_at", Integer, nullable=False),
    Column("expires_at", Integer, nullable=False),
    Index("idx_room_event_log_room_seq", "room_id", "seq"),
    Index("idx_room_event_log_expires_at", "expires_at"),
)

# Internal coordination primitive. Rows are mandatory-TTL operational state,
# never campaign content and never exposed as a generic package KV surface.
core_ephemeral_states = Table(
    "core_ephemeral_states", metadata,
    Column("id", _ID, primary_key=True),
    Column("namespace", _STR, nullable=False),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("scope_id", _ID, nullable=False),
    Column("owner_user_id", _ID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("entry_key", _STR, nullable=False),
    Column("audience_json", Text, nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("version", Integer, nullable=False, server_default=text("1")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    Column("expires_at", Integer, nullable=False),
    UniqueConstraint("namespace", "campaign_id", "scope_id", "owner_user_id", "entry_key"),
    Index("idx_core_ephemeral_scope", "namespace", "campaign_id", "scope_id", "expires_at"),
    Index("idx_core_ephemeral_expiry", "expires_at"),
)

automation_jobs = Table(
    "automation_jobs", metadata,
    Column("id", _ID, primary_key=True), Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("package_id", _ID, nullable=False), Column("action_id", _STR, nullable=False), Column("action_version", Integer, nullable=False),
    Column("input_json", Text, nullable=False), Column("principal_user_id", _ID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("run_at_utc", Integer, nullable=False), Column("idempotency_key", _STR, nullable=False), Column("status", _STR, nullable=False),
    Column("attempts", Integer, nullable=False, server_default=text("0")), Column("lease_owner", _STR, nullable=True), Column("lease_expires_at", Integer, nullable=True),
    Column("error_code", _STR, nullable=True), Column("origin_execution_id", _ID, nullable=True), Column("origin_job_id", _ID, nullable=True),
    Column("causal_depth", Integer, nullable=False, server_default=text("0")), Column("created_at", Integer, nullable=False), Column("updated_at", Integer, nullable=False),
    CheckConstraint("status IN ('pending','running','succeeded','failed','rejected','cancelled')", name="status"),
    UniqueConstraint("campaign_id", "package_id", "idempotency_key"), Index("idx_automation_jobs_due", "status", "run_at_utc", "lease_expires_at"),
)


# Acesso ao compendio, pack a pack. A identidade e o PAR (package_id, pack_id):
# um pack_id so e unico dentro do seu pacote. Linha ausente = "none".
content_pack_ownership = Table(
    "content_pack_ownership",
    metadata,
    Column("id", _ID, primary_key=True),
    Column("campaign_id", _ID, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
    Column("package_id", _STR, nullable=False),
    Column("pack_id", _STR, nullable=False),
    Column("role", _STR, nullable=False),
    Column("level", _STR, nullable=False, server_default=text("'none'")),
    Column("created_at", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False),
    UniqueConstraint("campaign_id", "package_id", "pack_id", "role", name="uq_content_pack_ownership"),
    Index("idx_content_pack_ownership_campaign", "campaign_id", "package_id", "pack_id"),
)


schema_migrations = Table(
    "schema_migrations",
    metadata,
    Column("id", _STR, primary_key=True),
    Column("applied_at", _STR, nullable=False),
)
