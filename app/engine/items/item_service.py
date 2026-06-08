"""Item Core lifecycle (System API v0, commands ``item.*``).

Mirrors :class:`ActorService`: creates/updates the minimal Item Core row in
SQLite and initialises the matching Sheet Data file in scoped-json-v1 storage.
The item's ``type`` must be a registered itemType of the campaign's assigned
active system. Items are standalone, permissioned, foldered entities — but never
placed on a scene.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.items.item_permissions import can_edit_item, can_view_item
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.systems.system_install_service import SystemInstallService
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.item_folder_repository import ItemFolderRepository
from app.persistence.repositories.item_permission_repository import ItemPermissionRepository
from app.persistence.repositories.item_repository import ItemRepository


def _is_gm(campaign: dict) -> bool:
    return campaign.get("member_role") == "gm"


@dataclass(frozen=True)
class ItemResult:
    success: bool
    item_id: str | None = None
    campaign_id: str | None = None
    system_id: str | None = None
    version: int | None = None
    folder_id: str | None = None
    is_owner: bool | None = None
    error_key: str | None = None


class ItemService:
    def __init__(self) -> None:
        self.items = ItemRepository()
        self.campaigns = CampaignRepository()
        self.systems = SystemInstallService()
        self.storage = ScopedJsonStorage()
        self.permissions = ItemPermissionRepository()
        self.folders = ItemFolderRepository()

    def create_item(
        self,
        *,
        campaign_id: str,
        user_id: str,
        system_id: str,
        item_type: str,
        name: str,
        folder_id: str = "",
        owner_user_ids: list[str] | None = None,
        data: dict | None = None,
    ) -> ItemResult:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return ItemResult(success=False, error_key="game.items.errors.campaign_not_found")
        campaign_dict = dict(campaign)
        if not _is_gm(campaign_dict):
            return ItemResult(success=False, error_key="game.items.errors.gm_required")

        active_system_id = str(campaign_dict.get("active_system_id") or "")
        if not active_system_id or system_id != active_system_id:
            return ItemResult(success=False, error_key="game.items.errors.system_not_assigned")

        manifest = self.systems.get_active_manifest(system_id)
        if manifest is None:
            return ItemResult(success=False, error_key="game.items.errors.system_not_enabled")

        valid_types = {t.id for t in manifest.item_types}
        if item_type not in valid_types:
            return ItemResult(success=False, error_key="game.items.errors.invalid_type")

        name = name.strip()[:120]
        if not name:
            return ItemResult(success=False, error_key="game.items.errors.name_required")

        resolved_folder = self._resolve_folder(campaign_id=campaign_id, folder_id=folder_id)
        if resolved_folder == "":
            return ItemResult(success=False, error_key="game.items.folders.errors.not_found")

        owner_ids = self._resolve_owner_ids(
            campaign_id=campaign_id, owner_user_ids=owner_user_ids or []
        )
        item_id = self.items.create(
            campaign_id=campaign_id,
            system_id=system_id,
            item_type=item_type,
            name=name,
            created_by_user_id=user_id,
            folder_id=resolved_folder,
            owner_user_ids=owner_ids,
        )
        self.storage.write_item(
            system_id=system_id,
            campaign_id=campaign_id,
            item_id=item_id,
            version=1,
            data=data or {},
        )
        return ItemResult(
            success=True,
            item_id=item_id,
            campaign_id=campaign_id,
            system_id=system_id,
            version=1,
        )

    def update_core(
        self,
        *,
        item_id: str,
        user_id: str,
        name: str,
        folder_id: str = "",
        portrait_asset_id: str = "",
    ) -> ItemResult:
        item, campaign, error = self._load_editable(item_id, user_id)
        if error is not None:
            return error

        name = name.strip()[:120]
        if not name:
            return ItemResult(success=False, error_key="game.items.errors.name_required")

        version = self.items.update_core(
            item_id=item_id,
            name=name,
            folder_id=folder_id or None,
            portrait_asset_id=portrait_asset_id or None,
        )
        return ItemResult(
            success=True,
            item_id=item_id,
            campaign_id=item["campaign_id"],
            system_id=item["system_id"],
            version=version,
        )

    def delete_item(self, *, item_id: str, user_id: str) -> ItemResult:
        item, campaign, error = self._load_editable(item_id, user_id)
        if error is not None:
            return error
        self.items.soft_delete(item_id=item_id)
        self.storage.delete_item(
            system_id=item["system_id"],
            campaign_id=item["campaign_id"],
            item_id=item_id,
        )
        return ItemResult(
            success=True,
            item_id=item_id,
            campaign_id=item["campaign_id"],
            system_id=item["system_id"],
        )

    def get_item(self, *, item_id: str, user_id: str) -> dict | None:
        item = self.items.get(item_id)
        if item is None or item["status"] != "active":
            return None
        campaign = self.campaigns.get_for_user(campaign_id=item["campaign_id"], user_id=user_id)
        if campaign is None:
            return None
        if not can_view_item(item=item, campaign=dict(campaign), user_id=user_id):
            return None
        return item

    def list_for_campaign(self, *, campaign_id: str, user_id: str) -> list[dict]:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return []
        campaign_dict = dict(campaign)
        visible = []
        for item in self.items.list_active_for_campaign(campaign_id=campaign_id):
            if can_view_item(item=item, campaign=campaign_dict, user_id=user_id):
                visible.append(item)
        return visible

    def _load_editable(
        self, item_id: str, user_id: str
    ) -> tuple[dict | None, dict | None, ItemResult | None]:
        item = self.items.get(item_id)
        if item is None or item["status"] != "active":
            return None, None, ItemResult(success=False, error_key="game.items.errors.not_found")
        campaign = self.campaigns.get_for_user(campaign_id=item["campaign_id"], user_id=user_id)
        if campaign is None:
            return None, None, ItemResult(success=False, error_key="game.items.errors.not_found")
        campaign_dict = dict(campaign)
        if not can_edit_item(item=item, campaign=campaign_dict, user_id=user_id):
            return None, None, ItemResult(success=False, error_key="game.items.errors.not_allowed")
        return item, campaign_dict, None

                                                                              

    def _load_gm_item(
        self, item_id: str, requester_user_id: str
    ) -> tuple[dict | None, ItemResult | None]:
        item = self.items.get(item_id)
        if item is None or item["status"] != "active":
            return None, ItemResult(success=False, error_key="game.items.errors.not_found")
        campaign = self.campaigns.get_for_user(
            campaign_id=item["campaign_id"], user_id=requester_user_id
        )
        if campaign is None or not _is_gm(dict(campaign)):
            return None, ItemResult(success=False, error_key="game.items.errors.gm_required")
        return item, None

    def toggle_owner(
        self, *, item_id: str, user_id_to_toggle: str, requester_user_id: str
    ) -> ItemResult:
        item, error = self._load_gm_item(item_id, requester_user_id)
        if error is not None:
            return error
        member = self.campaigns.get_member(
            campaign_id=item["campaign_id"], user_id=user_id_to_toggle
        )
        if member is None or member["role"] == "gm":
            return ItemResult(success=False, error_key="game.items.errors.not_found")

        is_owner = self.items.has_owner(item_id=item_id, user_id=user_id_to_toggle)
        if is_owner:
            self.items.remove_owner(item_id=item_id, user_id=user_id_to_toggle)
            self.permissions.upsert_for_user(
                item_id=item_id, user_id=user_id_to_toggle, can_view=False, can_edit=False
            )
        else:
            self.items.add_owner(item_id=item_id, user_id=user_id_to_toggle)
            self.permissions.upsert_for_user(
                item_id=item_id, user_id=user_id_to_toggle, can_view=True, can_edit=True
            )
        return ItemResult(
            success=True,
            item_id=item_id,
            campaign_id=item["campaign_id"],
            is_owner=not is_owner,
        )

    def list_owners(self, *, item_id: str) -> list[dict]:
        return self.items.list_owners_for_item(item_id=item_id)

    def set_member_access(
        self, *, item_id: str, target_user_id: str, access_level: str, requester_user_id: str
    ) -> ItemResult:
        item, error = self._load_gm_item(item_id, requester_user_id)
        if error is not None:
            return error
        member = self.campaigns.get_member(campaign_id=item["campaign_id"], user_id=target_user_id)
        if member is None or member["role"] == "gm":
            return ItemResult(success=False, error_key="game.items.errors.not_found")

        normalized = access_level if access_level in {"none", "read", "owner"} else "none"
        if normalized == "owner":
            self.items.add_owner(item_id=item_id, user_id=target_user_id)
            self.permissions.upsert_for_user(
                item_id=item_id, user_id=target_user_id, can_view=True, can_edit=True
            )
        elif normalized == "read":
            self.items.remove_owner(item_id=item_id, user_id=target_user_id)
            self.permissions.upsert_for_user(
                item_id=item_id, user_id=target_user_id, can_view=True, can_edit=False
            )
        else:
            self.items.remove_owner(item_id=item_id, user_id=target_user_id)
            self.permissions.upsert_for_user(
                item_id=item_id, user_id=target_user_id, can_view=False, can_edit=False
            )
        return ItemResult(success=True, item_id=item_id, campaign_id=item["campaign_id"])

                                                                              

    def create_folder(
        self, *, campaign_id: str, user_id: str, name: str, parent_id: str = "", color: str = ""
    ) -> ItemResult:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return ItemResult(success=False, error_key="game.items.errors.campaign_not_found")
        if not _is_gm(dict(campaign)):
            return ItemResult(success=False, error_key="game.items.errors.gm_required")
        name = name.strip()[:60]
        if not name:
            return ItemResult(success=False, error_key="game.items.folders.errors.name_required")
        resolved_parent: str | None = None
        if parent_id:
            parent = self.folders.get(folder_id=parent_id, campaign_id=campaign_id)
            if parent is None:
                return ItemResult(success=False, error_key="game.items.folders.errors.not_found")
            resolved_parent = parent_id
        folder_id = self.folders.create(
            campaign_id=campaign_id,
            created_by_user_id=user_id,
            name=name,
            parent_id=resolved_parent,
            color=color.strip()[:32] or None,
        )
        return ItemResult(success=True, folder_id=folder_id, campaign_id=campaign_id)

    def rename_folder(self, *, folder_id: str, name: str, user_id: str) -> ItemResult:
        folder, error = self._load_gm_folder(folder_id, user_id)
        if error is not None:
            return error
        name = name.strip()[:60]
        if not name:
            return ItemResult(success=False, error_key="game.items.folders.errors.name_required")
        self.folders.rename(folder_id=folder_id, name=name)
        return ItemResult(success=True, folder_id=folder_id, campaign_id=folder["campaign_id"])

    def set_folder_color(self, *, folder_id: str, color: str, user_id: str) -> ItemResult:
        folder, error = self._load_gm_folder(folder_id, user_id)
        if error is not None:
            return error
        self.folders.set_color(folder_id=folder_id, color=color.strip()[:32] or None)
        return ItemResult(success=True, folder_id=folder_id, campaign_id=folder["campaign_id"])

    def delete_folder(self, *, folder_id: str, user_id: str) -> ItemResult:
        folder, error = self._load_gm_folder(folder_id, user_id)
        if error is not None:
            return error
        self.items.clear_folder(folder_id=folder_id)
        self.folders.delete(folder_id=folder_id)
        return ItemResult(success=True, folder_id=folder_id, campaign_id=folder["campaign_id"])

    def move_folder(self, *, folder_id: str, target_parent_id: str, user_id: str) -> ItemResult:
        folder, error = self._load_gm_folder(folder_id, user_id)
        if error is not None:
            return error
        resolved_parent: str | None = None
        if target_parent_id:
            if target_parent_id == folder_id:
                return ItemResult(success=False, error_key="game.items.folders.errors.not_found")
            parent = self.folders.get(folder_id=target_parent_id, campaign_id=folder["campaign_id"])
            if parent is None or self._is_descendant(
                campaign_id=folder["campaign_id"], folder_id=target_parent_id, ancestor_id=folder_id
            ):
                return ItemResult(success=False, error_key="game.items.folders.errors.not_found")
            resolved_parent = target_parent_id
        self.folders.set_parent(folder_id=folder_id, parent_id=resolved_parent)
        return ItemResult(success=True, folder_id=folder_id, campaign_id=folder["campaign_id"])

    def move_item(self, *, item_id: str, target_folder_id: str, user_id: str) -> ItemResult:
        item, error = self._load_gm_item(item_id, user_id)
        if error is not None:
            return error
        resolved_folder: str | None = None
        if target_folder_id:
            folder = self.folders.get(folder_id=target_folder_id, campaign_id=item["campaign_id"])
            if folder is None:
                return ItemResult(success=False, error_key="game.items.folders.errors.not_found")
            resolved_folder = target_folder_id
        self.items.set_folder(item_id=item_id, folder_id=resolved_folder)
        return ItemResult(
            success=True,
            item_id=item_id,
            campaign_id=item["campaign_id"],
            folder_id=resolved_folder,
        )

    def _load_gm_folder(
        self, folder_id: str, user_id: str
    ) -> tuple[dict | None, ItemResult | None]:
        folder = self.folders.get_by_id(folder_id=folder_id)
        if folder is None:
            return None, ItemResult(success=False, error_key="game.items.folders.errors.not_found")
        campaign = self.campaigns.get_for_user(campaign_id=folder["campaign_id"], user_id=user_id)
        if campaign is None or not _is_gm(dict(campaign)):
            return None, ItemResult(success=False, error_key="game.items.errors.gm_required")
        return folder, None

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

    def _resolve_folder(self, *, campaign_id: str, folder_id: str) -> str | None:
        """Return the folder id (or None for root); '' signals an invalid folder."""
        if not folder_id:
            return None
        folder = self.folders.get(folder_id=folder_id, campaign_id=campaign_id)
        if folder is None:
            return ""
        return folder_id

    def _resolve_owner_ids(self, *, campaign_id: str, owner_user_ids: list[str]) -> list[str]:
        if not owner_user_ids:
            return []
        valid = {
            m["user_id"]
            for m in self.campaigns.list_members(campaign_id=campaign_id)
            if m["role"] != "gm"
        }
        return [uid for uid in owner_user_ids if uid in valid]
