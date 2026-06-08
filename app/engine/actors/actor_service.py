"""Actor Core lifecycle (System API v0, §2.2, commands ``actor.*``).

Creates/updates the minimal Actor Core row in SQLite and initialises the
matching Sheet Data file in scoped-json-v1 storage. The actor's ``type`` must
be a registered actorType of an *enabled* system.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.actors.actor_permissions import can_edit_actor, can_view_actor
from app.engine.sheets.schema_service import SchemaService
from app.engine.sheets.sheet_validation import apply_schema_defaults
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.systems.system_install_service import SystemInstallService
from app.persistence.repositories.actor_folder_repository import ActorFolderRepository
from app.persistence.repositories.actor_permission_repository import ActorPermissionRepository
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository


def _is_gm(campaign: dict) -> bool:
    return campaign.get("member_role") == "gm"


@dataclass(frozen=True)
class ActorResult:
    success: bool
    actor_id: str | None = None
    campaign_id: str | None = None
    system_id: str | None = None
    version: int | None = None
    folder_id: str | None = None
    is_owner: bool | None = None
    error_key: str | None = None


class ActorService:
    def __init__(self) -> None:
        self.actors = ActorRepository()
        self.campaigns = CampaignRepository()
        self.systems = SystemInstallService()
        self.schemas = SchemaService()
        self.storage = ScopedJsonStorage()
        self.permissions = ActorPermissionRepository()
        self.folders = ActorFolderRepository()

    def create_actor(
        self,
        *,
        campaign_id: str,
        user_id: str,
        system_id: str,
        actor_type: str,
        name: str,
        folder_id: str = "",
        owner_user_ids: list[str] | None = None,
    ) -> ActorResult:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return ActorResult(success=False, error_key="game.actors.errors.campaign_not_found")
        if not _is_gm(dict(campaign)):
            return ActorResult(success=False, error_key="game.actors.errors.gm_required")

        manifest = self.systems.get_active_manifest(system_id)
        if manifest is None:
            return ActorResult(success=False, error_key="game.actors.errors.system_not_enabled")

        valid_types = {t.id for t in manifest.actor_types}
        if actor_type not in valid_types:
            return ActorResult(success=False, error_key="game.actors.errors.invalid_type")

        name = name.strip()[:120]
        if not name:
            return ActorResult(success=False, error_key="game.actors.errors.name_required")

        resolved_folder = self._resolve_folder(
            campaign_id=campaign_id, folder_id=folder_id, campaign=dict(campaign), user_id=user_id
        )
        if resolved_folder == "":
            return ActorResult(success=False, error_key="game.actors.folders.errors.not_found")

        owner_ids = self._resolve_owner_ids(
            campaign_id=campaign_id, user_id=user_id, owner_user_ids=owner_user_ids or []
        )
        actor_id = self.actors.create(
            campaign_id=campaign_id,
            system_id=system_id,
            actor_type=actor_type,
            name=name,
            created_by_user_id=user_id,
            folder_id=resolved_folder,
            owner_user_ids=owner_ids,
        )
        schema = self.schemas.get_actor_schema(system_id=system_id, actor_type=actor_type)
        self.storage.write_actor(
            system_id=system_id,
            campaign_id=campaign_id,
            actor_id=actor_id,
            version=1,
            data=apply_schema_defaults(schema),
        )
        return ActorResult(
            success=True,
            actor_id=actor_id,
            campaign_id=campaign_id,
            system_id=system_id,
            version=1,
        )

    def update_core(
        self,
        *,
        actor_id: str,
        user_id: str,
        name: str,
        folder_id: str = "",
        portrait_asset_id: str = "",
        token_asset_id: str = "",
    ) -> ActorResult:
        actor, campaign, error = self._load_editable(actor_id, user_id)
        if error is not None:
            return error

        name = name.strip()[:120]
        if not name:
            return ActorResult(success=False, error_key="game.actors.errors.name_required")

        version = self.actors.update_core(
            actor_id=actor_id,
            name=name,
            folder_id=folder_id or None,
            portrait_asset_id=portrait_asset_id or None,
            token_asset_id=token_asset_id or None,
        )
        return ActorResult(
            success=True,
            actor_id=actor_id,
            campaign_id=actor["campaign_id"],
            system_id=actor["system_id"],
            version=version,
        )

    def delete_actor(self, *, actor_id: str, user_id: str) -> ActorResult:
        actor, campaign, error = self._load_editable(actor_id, user_id)
        if error is not None:
            return error
        self.actors.soft_delete(actor_id=actor_id)
        self.storage.delete_actor(
            system_id=actor["system_id"],
            campaign_id=actor["campaign_id"],
            actor_id=actor_id,
        )
        return ActorResult(
            success=True,
            actor_id=actor_id,
            campaign_id=actor["campaign_id"],
            system_id=actor["system_id"],
        )

    def get_actor(self, *, actor_id: str, user_id: str) -> dict | None:
        actor = self.actors.get(actor_id)
        if actor is None or actor["status"] != "active":
            return None
        campaign = self.campaigns.get_for_user(campaign_id=actor["campaign_id"], user_id=user_id)
        if campaign is None:
            return None
        if not can_view_actor(actor=actor, campaign=dict(campaign), user_id=user_id):
            return None
        return actor

    def list_for_campaign(self, *, campaign_id: str, user_id: str) -> list[dict]:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return []
        campaign_dict = dict(campaign)
        visible = []
        for actor in self.actors.list_active_for_campaign(campaign_id=campaign_id):
            if can_view_actor(actor=actor, campaign=campaign_dict, user_id=user_id):
                visible.append(actor)
        return visible

    def _load_editable(
        self, actor_id: str, user_id: str
    ) -> tuple[dict | None, dict | None, ActorResult | None]:
        actor = self.actors.get(actor_id)
        if actor is None or actor["status"] != "active":
            return None, None, ActorResult(success=False, error_key="game.actors.errors.not_found")
        campaign = self.campaigns.get_for_user(campaign_id=actor["campaign_id"], user_id=user_id)
        if campaign is None:
            return None, None, ActorResult(success=False, error_key="game.actors.errors.not_found")
        campaign_dict = dict(campaign)
        if not can_edit_actor(actor=actor, campaign=campaign_dict, user_id=user_id):
            return None, None, ActorResult(success=False, error_key="game.actors.errors.not_allowed")
        return actor, campaign_dict, None

                                                                              

    def _load_gm_actor(self, actor_id: str, requester_user_id: str) -> tuple[dict | None, ActorResult | None]:
        actor = self.actors.get(actor_id)
        if actor is None or actor["status"] != "active":
            return None, ActorResult(success=False, error_key="game.actors.errors.not_found")
        campaign = self.campaigns.get_for_user(
            campaign_id=actor["campaign_id"], user_id=requester_user_id
        )
        if campaign is None or not _is_gm(dict(campaign)):
            return None, ActorResult(success=False, error_key="game.actors.errors.gm_required")
        return actor, None

    def toggle_owner(
        self, *, actor_id: str, user_id_to_toggle: str, requester_user_id: str
    ) -> ActorResult:
        actor, error = self._load_gm_actor(actor_id, requester_user_id)
        if error is not None:
            return error
        member = self.campaigns.get_member(
            campaign_id=actor["campaign_id"], user_id=user_id_to_toggle
        )
        if member is None or member["role"] == "gm":
            return ActorResult(success=False, error_key="game.actors.errors.not_found")

        is_owner = self.actors.has_owner(actor_id=actor_id, user_id=user_id_to_toggle)
        if is_owner:
            self.actors.remove_owner(actor_id=actor_id, user_id=user_id_to_toggle)
            self.permissions.upsert_for_user(
                actor_id=actor_id, user_id=user_id_to_toggle, can_view=False, can_edit=False
            )
        else:
            self.actors.add_owner(actor_id=actor_id, user_id=user_id_to_toggle)
            self.permissions.upsert_for_user(
                actor_id=actor_id, user_id=user_id_to_toggle, can_view=True, can_edit=True
            )
        return ActorResult(
            success=True,
            actor_id=actor_id,
            campaign_id=actor["campaign_id"],
            is_owner=not is_owner,
        )

    def list_owners(self, *, actor_id: str) -> list[dict]:
        return self.actors.list_owners_for_actor(actor_id=actor_id)

    def set_member_access(
        self, *, actor_id: str, target_user_id: str, access_level: str, requester_user_id: str
    ) -> ActorResult:
        actor, error = self._load_gm_actor(actor_id, requester_user_id)
        if error is not None:
            return error
        member = self.campaigns.get_member(
            campaign_id=actor["campaign_id"], user_id=target_user_id
        )
        if member is None or member["role"] == "gm":
            return ActorResult(success=False, error_key="game.actors.errors.not_found")

        normalized = access_level if access_level in {"none", "read", "owner"} else "none"
        if normalized == "owner":
            self.actors.add_owner(actor_id=actor_id, user_id=target_user_id)
            self.permissions.upsert_for_user(
                actor_id=actor_id, user_id=target_user_id, can_view=True, can_edit=True
            )
        elif normalized == "read":
            self.actors.remove_owner(actor_id=actor_id, user_id=target_user_id)
            self.permissions.upsert_for_user(
                actor_id=actor_id, user_id=target_user_id, can_view=True, can_edit=False
            )
        else:
            self.actors.remove_owner(actor_id=actor_id, user_id=target_user_id)
            self.permissions.upsert_for_user(
                actor_id=actor_id, user_id=target_user_id, can_view=False, can_edit=False
            )
        return ActorResult(success=True, actor_id=actor_id, campaign_id=actor["campaign_id"])

                                                                              

    def create_folder(
        self, *, campaign_id: str, user_id: str, name: str, parent_id: str = "", color: str = ""
    ) -> ActorResult:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return ActorResult(success=False, error_key="game.actors.errors.campaign_not_found")
        if not _is_gm(dict(campaign)):
            return ActorResult(success=False, error_key="game.actors.errors.gm_required")
        name = name.strip()[:60]
        if not name:
            return ActorResult(success=False, error_key="game.actors.folders.errors.name_required")
        resolved_parent: str | None = None
        if parent_id:
            parent = self.folders.get(folder_id=parent_id, campaign_id=campaign_id)
            if parent is None:
                return ActorResult(success=False, error_key="game.actors.folders.errors.not_found")
            resolved_parent = parent_id
        folder_id = self.folders.create(
            campaign_id=campaign_id, created_by_user_id=user_id, name=name,
            parent_id=resolved_parent, color=color.strip()[:32] or None,
        )
        return ActorResult(success=True, folder_id=folder_id, campaign_id=campaign_id)

    def rename_folder(self, *, folder_id: str, name: str, user_id: str) -> ActorResult:
        folder, error = self._load_gm_folder(folder_id, user_id)
        if error is not None:
            return error
        name = name.strip()[:60]
        if not name:
            return ActorResult(success=False, error_key="game.actors.folders.errors.name_required")
        self.folders.rename(folder_id=folder_id, name=name)
        return ActorResult(success=True, folder_id=folder_id, campaign_id=folder["campaign_id"])

    def set_folder_color(self, *, folder_id: str, color: str, user_id: str) -> ActorResult:
        folder, error = self._load_gm_folder(folder_id, user_id)
        if error is not None:
            return error
        self.folders.set_color(folder_id=folder_id, color=color.strip()[:32] or None)
        return ActorResult(success=True, folder_id=folder_id, campaign_id=folder["campaign_id"])

    def delete_folder(self, *, folder_id: str, user_id: str) -> ActorResult:
        folder, error = self._load_gm_folder(folder_id, user_id)
        if error is not None:
            return error
        self.actors.clear_folder(folder_id=folder_id)
        self.folders.delete(folder_id=folder_id)
        return ActorResult(success=True, folder_id=folder_id, campaign_id=folder["campaign_id"])

    def move_folder(self, *, folder_id: str, target_parent_id: str, user_id: str) -> ActorResult:
        folder, error = self._load_gm_folder(folder_id, user_id)
        if error is not None:
            return error
        resolved_parent: str | None = None
        if target_parent_id:
            if target_parent_id == folder_id:
                return ActorResult(success=False, error_key="game.actors.folders.errors.not_found")
            parent = self.folders.get(folder_id=target_parent_id, campaign_id=folder["campaign_id"])
            if parent is None or self._is_descendant(
                campaign_id=folder["campaign_id"], folder_id=target_parent_id, ancestor_id=folder_id
            ):
                return ActorResult(success=False, error_key="game.actors.folders.errors.not_found")
            resolved_parent = target_parent_id
        self.folders.set_parent(folder_id=folder_id, parent_id=resolved_parent)
        return ActorResult(success=True, folder_id=folder_id, campaign_id=folder["campaign_id"])

    def move_actor(self, *, actor_id: str, target_folder_id: str, user_id: str) -> ActorResult:
        actor, error = self._load_gm_actor(actor_id, user_id)
        if error is not None:
            return error
        resolved_folder: str | None = None
        if target_folder_id:
            folder = self.folders.get(folder_id=target_folder_id, campaign_id=actor["campaign_id"])
            if folder is None:
                return ActorResult(success=False, error_key="game.actors.folders.errors.not_found")
            resolved_folder = target_folder_id
        self.actors.set_folder(actor_id=actor_id, folder_id=resolved_folder)
        return ActorResult(
            success=True,
            actor_id=actor_id,
            campaign_id=actor["campaign_id"],
            folder_id=resolved_folder,
        )

    def _load_gm_folder(
        self, folder_id: str, user_id: str
    ) -> tuple[dict | None, ActorResult | None]:
        folder = self._find_folder(folder_id)
        if folder is None:
            return None, ActorResult(success=False, error_key="game.actors.folders.errors.not_found")
        campaign = self.campaigns.get_for_user(campaign_id=folder["campaign_id"], user_id=user_id)
        if campaign is None or not _is_gm(dict(campaign)):
            return None, ActorResult(success=False, error_key="game.actors.errors.gm_required")
        return folder, None

    def _find_folder(self, folder_id: str) -> dict | None:
        return self.folders.get_by_id(folder_id=folder_id)

    def _is_descendant(self, *, campaign_id: str, folder_id: str, ancestor_id: str) -> bool:
        """True if folder_id is ancestor_id or one of its descendants (cycle guard)."""
        folders = {f["id"]: f for f in self.folders.list_for_campaign(campaign_id=campaign_id)}
        cursor = folder_id
        seen: set[str] = set()
        while cursor and cursor not in seen:
            if cursor == ancestor_id:
                return True
            seen.add(cursor)
            cursor = folders.get(cursor, {}).get("parent_id")
        return False

    def _resolve_folder(
        self, *, campaign_id: str, folder_id: str, campaign: dict, user_id: str
    ) -> str | None:
        """Return the folder id (or None for root); '' signals an invalid folder."""
        if not folder_id:
            return None
        folder = self.folders.get(folder_id=folder_id, campaign_id=campaign_id)
        if folder is None:
            return ""
        return folder_id

    def _resolve_owner_ids(
        self, *, campaign_id: str, user_id: str, owner_user_ids: list[str]
    ) -> list[str]:
        if not owner_user_ids:
            return []
        valid = {
            m["user_id"]
            for m in self.campaigns.list_members(campaign_id=campaign_id)
            if m["role"] != "gm"
        }
        return [uid for uid in owner_user_ids if uid in valid]
