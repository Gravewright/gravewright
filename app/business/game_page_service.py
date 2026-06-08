from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass

from app.business.campaigns.campaign_service import CampaignService
from app.business.permissions import PermissionService
from app.engine.actors.actor_permissions import can_edit_actor
from app.engine.actors.actor_service import ActorService
from app.engine.actors.folder_tree import build_actor_folder_tree
from app.engine.items.item_permissions import can_edit_item
from app.engine.items.item_service import ItemService
from app.engine.items.folder_tree import build_item_folder_tree
from app.engine.journals.folder_tree import build_journal_folder_tree
from app.engine.journals.journal_service import JournalService
from app.engine.systems.system_install_service import SystemInstallService
from app.domain.permissions.permissions import TablePermission
from app.domain.roles import PlayerRole
from app.domain.roles import has_full_view
from app.persistence.repositories.chat_message_repository import ChatMessageRepository
from app.persistence.repositories.scene_group_repository import SceneGroupRepository
from app.persistence.repositories.scene_layer_repository import SceneLayerRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.actor_folder_repository import ActorFolderRepository
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.item_folder_repository import ItemFolderRepository
from app.persistence.repositories.item_repository import ItemRepository
from app.persistence.repositories.journal_folder_repository import JournalFolderRepository
from app.persistence.repositories.journal_repository import JournalRepository


DEFAULT_MEASURE_FLASH_SECONDS = 6


@dataclass
class GamePageContext:
    rooms: list[dict]
    available_systems: list[dict]


class GamePageService:
    def __init__(self) -> None:
        self.campaigns = CampaignService()
        self.permissions = PermissionService()
        self.chat = ChatMessageRepository()
        self.scene_groups = SceneGroupRepository()
        self.scenes = SceneRepository()
        self.layers = SceneLayerRepository()
        self.journals = JournalRepository()
        self.journal_folders = JournalFolderRepository()
        self.journal_service = JournalService()
        self.actor_service = ActorService()
        self.actors = ActorRepository()
        self.actor_folders = ActorFolderRepository()
        self.item_service = ItemService()
        self.items = ItemRepository()
        self.item_folders = ItemFolderRepository()
        self.system_install = SystemInstallService()

    def build_context(self, *, user_id: str) -> GamePageContext:
        campaigns = self.campaigns.list_for_user(user_id)
        room_ids = [c["id"] for c in campaigns]

        members = self.campaigns.list_members_for_user_campaigns(user_id)
        online_user_ids_by_room: dict[str, set[str]] = {r: set() for r in room_ids}

        members_by_campaign_id: dict[str, list[dict]] = defaultdict(list)
        for member in members:
            campaign_id = member["campaign_id"]
            members_by_campaign_id[campaign_id].append(
                {
                    "user_id": member["user_id"],
                    "name": member["name"],
                    "email": member["email"],
                    "role": member["role"],
                    "is_online": member["user_id"]
                    in online_user_ids_by_room.get(campaign_id, set()),
                }
            )

                                                                                  
                                                                
        enabled_systems = [
            {
                "id": item["system_id"],
                "name": item["name"],
                "actor_types": item["actor_types"],
                "item_types": item.get("item_types", []),
                "area_markers": item.get("area_markers", []),
            }
            for item in self.system_install.list_for_tab()
            if item["status"] == "enabled"
        ]
        enabled_systems_by_id = {system["id"]: system for system in enabled_systems}
        available_systems = [
            {"id": s["id"], "name": s["name"], "version": ""} for s in enabled_systems
        ]

        rooms = []
        for campaign in campaigns:
            room = dict(campaign)
            room["is_streamer"] = room["member_role"] == PlayerRole.STREAMER.value
            room["is_readonly"] = room["is_streamer"]
            room["measure_flash_seconds"] = _measure_flash_seconds(
                campaign["persistent_state_json"]
            )
            room["members"] = members_by_campaign_id[campaign["id"]]
            room["permission_settings"] = self.permissions.build_settings_context(
                campaign_id=campaign["id"],
                user_id=user_id,
                member_role=campaign["member_role"],
            )
            room["can_invite"] = room["permission_settings"]["can_invite"]
            room["can_delete_chat_own"] = self.permissions.can(
                campaign_id=campaign["id"],
                user_id=user_id,
                permission=TablePermission.CHAT_DELETE_OWN,
            )
            room["can_delete_chat_any"] = self.permissions.can(
                campaign_id=campaign["id"],
                user_id=user_id,
                permission=TablePermission.CHAT_DELETE_ANY,
            )
            recent_messages = self.chat.list_for_campaign(campaign_id=campaign["id"])
            if room["is_streamer"]:
                                                                                  
                                                                               
                                                             
                recent_messages = [
                    m for m in recent_messages if m.get("visibility") == "public"
                ]
            room["recent_messages"] = recent_messages
            room["scene_groups"] = self.scene_groups.list_by_campaign(campaign["id"])
            room["scenes"] = self.scenes.list_by_campaign(campaign["id"])
            room["active_scene"] = self.scenes.get_active_scene(campaign["id"])
            if room["active_scene"]:
                scene_layers = self.layers.list_by_scene(room["active_scene"]["id"])
                ground = next(
                    (layer for layer in scene_layers if layer["kind"] == "raster_tile_refs"), None
                )
                room["ground_layer_id"] = ground["id"] if ground else None
            else:
                room["ground_layer_id"] = None
            scenes_by_group: dict[str, list] = defaultdict(list)
            ungrouped_scenes = []
            scene_group_ids = {group["id"] for group in room["scene_groups"]}
            for scene in room["scenes"]:
                group_id = scene["group_id"]
                if group_id and group_id in scene_group_ids:
                    scenes_by_group[group_id].append(scene)
                else:
                    ungrouped_scenes.append(scene)
            room["scene_groups_with_scenes"] = [
                {
                    "group": group,
                    "scenes": scenes_by_group[group["id"]],
                    "has_active": any(scene["active"] for scene in scenes_by_group[group["id"]]),
                }
                for group in room["scene_groups"]
            ]
            room["ungrouped_scenes"] = ungrouped_scenes
            room["ungrouped_scenes_has_active"] = any(scene["active"] for scene in ungrouped_scenes)

            sys_id = room.get("active_system_id")
                                                                               
            record = self.system_install.installed.get(sys_id) if sys_id else None
            active_system = enabled_systems_by_id.get(sys_id or "")
            room["active_system"] = (
                {
                    "id": sys_id,
                    "name": active_system["name"],
                    "actor_types": active_system.get("actor_types", []),
                    "item_types": active_system.get("item_types", []),
                    "area_markers": active_system.get("area_markers", []),
                }
                if record is not None and active_system is not None
                else None
            )
            room["area_marker_presets_json"] = json.dumps(
                room["active_system"]["area_markers"] if room["active_system"] else []
            )

            room["members_json"] = json.dumps(
                [
                    {"id": m["user_id"], "name": m["name"]}
                    for m in room["members"]
                    if m["role"] != "gm"
                ]
            )

            owners_by_journal = self.journals.list_owners_for_campaign_journals(
                campaign_id=campaign["id"]
            )
            all_journals = []
            for journal in self.journals.list_active_for_campaign(campaign_id=campaign["id"]):
                                                                              
                                                                                
                                                                       
                if not self.journal_service.can_view_journal_directly(
                    journal=journal,
                    campaign=room,
                    user_id=user_id,
                ):
                    continue
                owners = owners_by_journal.get(journal["id"], [])
                journal["owners"] = owners
                journal["owner_ids"] = {owner["id"] for owner in owners}
                journal["owner_name"] = (
                    ", ".join(owner["name"] for owner in owners) if owners else None
                )
                journal["type_label_key"] = f"game.journal.types.{journal['type']}"
                all_journals.append(journal)

            all_journal_folders_raw = self.journal_folders.list_for_campaign(
                campaign_id=campaign["id"]
            )
            if room["member_role"] != "gm":
                folder_lookup = {folder["id"]: folder for folder in all_journal_folders_raw}
                visible_journal_folder_ids = {
                    folder["id"]
                    for folder in all_journal_folders_raw
                    if folder["created_by_user_id"] == user_id
                }
                for journal in all_journals:
                    folder_id = journal.get("folder_id")
                    while folder_id and folder_id in folder_lookup:
                        if folder_id in visible_journal_folder_ids:
                            break
                        visible_journal_folder_ids.add(folder_id)
                        folder_id = folder_lookup[folder_id].get("parent_id")
                all_journal_folders_raw = [
                    folder
                    for folder in all_journal_folders_raw
                    if folder["id"] in visible_journal_folder_ids
                ]

            journal_folder_ids = {folder["id"] for folder in all_journal_folders_raw}
            journals_by_folder: dict[str, list] = defaultdict(list)
            unfoldered_journals = []
            for journal in all_journals:
                folder_id = journal.get("folder_id")
                if folder_id and folder_id in journal_folder_ids:
                    journals_by_folder[folder_id].append(journal)
                else:
                    unfoldered_journals.append(journal)

            room["journal_folder_tree"] = build_journal_folder_tree(
                all_journal_folders_raw,
                journals_by_folder,
            )
            room["journal_folders"] = all_journal_folders_raw
            room["journals"] = all_journals
            room["unfoldered_journals"] = unfoldered_journals

            is_gm_room = room["member_role"] == "gm"
                                                                                  
                                                     
            sees_all = has_full_view(room["member_role"])
            owners_by_actor = self.actors.list_owners_for_campaign_actors(
                campaign_id=campaign["id"]
            )
            all_actors = []
            for actor in self.actor_service.list_for_campaign(
                campaign_id=campaign["id"], user_id=user_id
            ):
                owners = owners_by_actor.get(actor["id"], [])
                all_actors.append(
                    {
                        "id": actor["id"],
                        "name": actor["name"],
                        "type": actor["type"],
                        "system_id": actor["system_id"],
                        "folder_id": actor.get("folder_id"),
                        "owners": owners,
                        "owners_json": json.dumps(owners),
                        "owner_name": ", ".join(o["name"] for o in owners) if owners else None,
                        "can_edit": can_edit_actor(actor=actor, campaign=room, user_id=user_id),
                    }
                )

            all_actor_folders = self.actor_folders.list_for_campaign(campaign_id=campaign["id"])
            if not sees_all:
                folder_lookup = {f["id"]: f for f in all_actor_folders}
                visible_folder_ids: set[str] = set()
                for actor in all_actors:
                    folder_id = actor.get("folder_id")
                    while folder_id and folder_id in folder_lookup:
                        if folder_id in visible_folder_ids:
                            break
                        visible_folder_ids.add(folder_id)
                        folder_id = folder_lookup[folder_id].get("parent_id")
                all_actor_folders = [f for f in all_actor_folders if f["id"] in visible_folder_ids]

            actor_folder_ids = {f["id"] for f in all_actor_folders}
            actors_by_folder: dict[str, list] = defaultdict(list)
            unfoldered_actors = []
            for actor in all_actors:
                folder_id = actor.get("folder_id")
                if folder_id and folder_id in actor_folder_ids:
                    actors_by_folder[folder_id].append(actor)
                else:
                    unfoldered_actors.append(actor)

            room["actors"] = all_actors
            room["actor_folder_tree"] = build_actor_folder_tree(all_actor_folders, actors_by_folder)
            room["unfoldered_actors"] = unfoldered_actors
            room["enabled_systems"] = enabled_systems if is_gm_room else []

                                                                              
            owners_by_item = self.items.list_owners_for_campaign_items(campaign_id=campaign["id"])
            all_items = []
            for item in self.item_service.list_for_campaign(
                campaign_id=campaign["id"], user_id=user_id
            ):
                owners = owners_by_item.get(item["id"], [])
                all_items.append(
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "type": item["type"],
                        "system_id": item["system_id"],
                        "folder_id": item.get("folder_id"),
                        "owners": owners,
                        "owners_json": json.dumps(owners),
                        "owner_name": ", ".join(o["name"] for o in owners) if owners else None,
                        "can_edit": can_edit_item(item=item, campaign=room, user_id=user_id),
                    }
                )

            all_item_folders = self.item_folders.list_for_campaign(campaign_id=campaign["id"])
            if not sees_all:
                item_folder_lookup = {f["id"]: f for f in all_item_folders}
                visible_item_folder_ids: set[str] = set()
                for item in all_items:
                    folder_id = item.get("folder_id")
                    while folder_id and folder_id in item_folder_lookup:
                        if folder_id in visible_item_folder_ids:
                            break
                        visible_item_folder_ids.add(folder_id)
                        folder_id = item_folder_lookup[folder_id].get("parent_id")
                all_item_folders = [
                    f for f in all_item_folders if f["id"] in visible_item_folder_ids
                ]

            item_folder_ids = {f["id"] for f in all_item_folders}
            items_by_folder: dict[str, list] = defaultdict(list)
            unfoldered_items = []
            for item in all_items:
                folder_id = item.get("folder_id")
                if folder_id and folder_id in item_folder_ids:
                    items_by_folder[folder_id].append(item)
                else:
                    unfoldered_items.append(item)

            room["items"] = all_items
            room["item_folder_tree"] = build_item_folder_tree(all_item_folders, items_by_folder)
            room["unfoldered_items"] = unfoldered_items

            rooms.append(room)

        return GamePageContext(rooms=rooms, available_systems=available_systems)


def _measure_flash_seconds(raw_state: str | None) -> int:
    if not raw_state:
        return DEFAULT_MEASURE_FLASH_SECONDS
    try:
        state = json.loads(raw_state)
    except Exception:
        return DEFAULT_MEASURE_FLASH_SECONDS
    if not isinstance(state, dict):
        return DEFAULT_MEASURE_FLASH_SECONDS
    table_settings = state.get("table_settings")
    if not isinstance(table_settings, dict):
        return DEFAULT_MEASURE_FLASH_SECONDS
    raw = table_settings.get("measure_flash_seconds")
    if not isinstance(raw, int | float):
        return DEFAULT_MEASURE_FLASH_SECONDS
    return max(1, min(60, int(raw)))
