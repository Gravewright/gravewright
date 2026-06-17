from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.domain.roles import has_full_view
from app.engine.journals import journal_data
from app.engine.journals import journal_doc
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.journal_folder_repository import JournalFolderRepository
from app.persistence.repositories.journal_permission_repository import JournalPermissionRepository
from app.persistence.repositories.journal_repository import JournalRepository


JOURNAL_TYPES = journal_data.JOURNAL_TYPES


def _is_gm(campaign: dict) -> bool:
    return campaign.get("member_role") == "gm"


def _decode_data(journal: dict) -> dict:
    raw = journal.get("data_json") or "{}"
    try:
        decoded = json.loads(raw)
    except (TypeError, ValueError):
        decoded = {}
    return decoded if isinstance(decoded, dict) else {}


@dataclass(frozen=True)
class JournalResult:
    success: bool
    journal_id: str | None = None
    folder_id: str | None = None
    campaign_id: str | None = None
    is_owner: bool = False
    version: int | None = None
    journal_type: str | None = None
    changed_paths: list[str] = field(default_factory=list)
    error_key: str | None = None


class JournalService:
    def __init__(self) -> None:
        self.campaigns = CampaignRepository()
        self.journals = JournalRepository()
        self.folders = JournalFolderRepository()
        self.journal_permissions = JournalPermissionRepository()

                                                                             

    def can_view_journal_directly(self, *, journal: dict, campaign: dict, user_id: str) -> bool:
        """Direct view access: GM, owner, shared/handout, or explicit permission.

        This is what the sidebar lists. It does NOT include access granted only
        by virtue of a quest being shown on a board (see ``can_view_journal``).
        """
                                                                            
        if has_full_view(campaign.get("member_role")):
            return True
        if self.journals.has_owner(journal_id=journal["id"], user_id=user_id):
            return True
                                                                               
        if journal.get("visibility") in {"shared", "handout"}:
            return True
        permission = self.journal_permissions.get_for_user(
            journal_id=journal["id"],
            user_id=user_id,
        )
        return bool(permission and permission["can_view"])

    def can_view_journal(self, *, journal: dict, campaign: dict, user_id: str) -> bool:
        """Whether the user may open this journal (read-only at least).

        Direct access, OR — for a quest — being shown on a board the user can
        view directly. The board acts as a hub: the quest opens read-only from
        the board without appearing in the sidebar on its own.
        """
        if self.can_view_journal_directly(journal=journal, campaign=campaign, user_id=user_id):
            return True
        if journal.get("type") == "quest":
            for board_id in self.journals.list_boards_for_quest(quest_id=journal["id"]):
                board = self.journals.get_by_id(board_id)
                if (
                    board is not None
                    and board["status"] == "active"
                    and self.can_view_journal_directly(
                        journal=dict(board), campaign=campaign, user_id=user_id
                    )
                ):
                    return True
        return False

    def can_edit_journal(self, *, journal: dict, campaign: dict, user_id: str) -> bool:
        if _is_gm(campaign):
            return True
        if self.journals.has_owner(journal_id=journal["id"], user_id=user_id):
            return True
        permission = self.journal_permissions.get_for_user(
            journal_id=journal["id"],
            user_id=user_id,
        )
        return bool(permission and permission["can_edit"])

                                                                             

    def create_folder(
        self,
        *,
        campaign_id: str,
        user_id: str,
        name: str,
        parent_id: str = "",
        color: str = "",
    ) -> JournalResult:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return JournalResult(success=False, error_key="game.journal.errors.campaign_not_found")

        name = name.strip()[:60]
        if not name:
            return JournalResult(success=False, error_key="game.journal.folders.errors.name_required")

        resolved_parent: str | None = None
        campaign_dict = dict(campaign)
        if parent_id:
            parent = self.folders.get(folder_id=parent_id, campaign_id=campaign_id)
            if parent is None:
                return JournalResult(success=False, error_key="game.journal.folders.errors.not_found")
            if not _is_gm(campaign_dict) and parent["created_by_user_id"] != user_id:
                return JournalResult(success=False, error_key="game.journal.errors.not_owner")
            resolved_parent = parent_id

        folder_id = self.folders.create(
            campaign_id=campaign_id,
            created_by_user_id=user_id,
            name=name,
            parent_id=resolved_parent,
            color=color.strip()[:32] or None,
        )
        return JournalResult(success=True, folder_id=folder_id, campaign_id=campaign_id)

                                                                             

    def create_journal(
        self,
        *,
        campaign_id: str,
        user_id: str,
        journal_type: str,
        title: str,
        folder_id: str = "",
        visibility: str = "private",
        content_markdown: str = "",
        data: dict | None = None,
        owner_user_ids: list[str] | None = None,
    ) -> JournalResult:
        campaign = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return JournalResult(success=False, error_key="game.journal.errors.campaign_not_found")

        journal_type = journal_type if journal_type in JOURNAL_TYPES else "diary"
        title = title.strip()[:120]
        if not title:
            return JournalResult(success=False, error_key="game.journal.errors.title_required")

        campaign_dict = dict(campaign)
        resolved_folder = self._resolve_folder(
            campaign_id=campaign_id,
            folder_id=folder_id,
            campaign=campaign_dict,
            user_id=user_id,
        )
        if resolved_folder == "":
            return JournalResult(success=False, error_key="game.journal.folders.errors.not_found")

        owner_ids = self._resolve_owner_ids(
            campaign_id=campaign_id,
            campaign=campaign_dict,
            user_id=user_id,
            owner_user_ids=owner_user_ids or [],
        )
        normalized_data = journal_data.normalize_data_for(journal_type, data or {})
        journal_id = self.journals.create(
            campaign_id=campaign_id,
            created_by_user_id=user_id,
            journal_type=journal_type,
            title=title,
            folder_id=resolved_folder,
            visibility=journal_data.normalize_visibility(visibility),
            content_markdown=content_markdown[: journal_data.RICHTEXT_LIMIT],
            data_json=json.dumps(normalized_data, separators=(",", ":")),
            owner_user_ids=owner_ids,
        )
        return JournalResult(
            success=True,
            journal_id=journal_id,
            campaign_id=campaign_id,
            journal_type=journal_type,
            version=1,
        )

    def update_journal(
        self,
        *,
        journal_id: str,
        user_id: str,
        title: str,
        folder_id: str = "",
        visibility: str = "private",
        content_markdown: str = "",
        data: dict | None = None,
        owner_user_ids: list[str] | None = None,
    ) -> JournalResult:
        journal = self.journals.get_by_id(journal_id)
        if journal is None or journal["status"] != "active":
            return JournalResult(success=False, error_key="game.journal.errors.not_found")

        campaign = self.campaigns.get_for_user(
            campaign_id=journal["campaign_id"],
            user_id=user_id,
        )
        if campaign is None:
            return JournalResult(success=False, error_key="game.journal.errors.not_found")

        campaign_dict = dict(campaign)
        if not self.can_edit_journal(journal=journal, campaign=campaign_dict, user_id=user_id):
            return JournalResult(success=False, error_key="game.journal.errors.not_owner")

        title = title.strip()[:120]
        if not title:
            return JournalResult(success=False, error_key="game.journal.errors.title_required")

                                                                                 
                                                                               
                                                                                     
        current_folder = journal.get("folder_id") or None
        if (folder_id or "") == (current_folder or ""):
            resolved_folder = current_folder
        else:
            resolved_folder = self._resolve_folder(
                campaign_id=journal["campaign_id"],
                folder_id=folder_id,
                campaign=campaign_dict,
                user_id=user_id,
            )
            if resolved_folder == "":
                return JournalResult(success=False, error_key="game.journal.folders.errors.not_found")

        journal_type = journal["type"]
        normalized_data = journal_data.normalize_data_for(journal_type, data or {})
                                                                              
                                                                              
        if not _is_gm(campaign_dict):
            stored = _decode_data(journal)
            if journal_type == "diary":
                existing = journal_data.normalize_diary_data(stored)
                normalized_data["gm"] = existing["gm"]
                normalized_data["content"] = journal_doc.merge_preserving_gm_blocks(
                    normalized_data["content"], existing["content"]
                )
            elif journal_type == "quest":
                existing = journal_data.normalize_quest_data(stored)
                normalized_data["gm"] = existing["gm"]
                normalized_data["public"]["description"] = journal_doc.merge_preserving_gm_blocks(
                    normalized_data["public"]["description"], existing["public"]["description"]
                )
            elif journal_type == "quest_board":
                existing = journal_data.normalize_board_data(stored)
                normalized_data["description"] = journal_doc.merge_preserving_gm_blocks(
                    normalized_data["description"], existing["description"]
                )

        version = self.journals.update(
            journal_id=journal_id,
            title=title,
            folder_id=resolved_folder,
            visibility=journal_data.normalize_visibility(visibility),
            content_markdown=content_markdown[: journal_data.RICHTEXT_LIMIT],
            data_json=json.dumps(normalized_data, separators=(",", ":")),
        )
        if _is_gm(campaign_dict) and owner_user_ids is not None:
            owner_ids = self._resolve_owner_ids(
                campaign_id=journal["campaign_id"],
                campaign=campaign_dict,
                user_id=user_id,
                owner_user_ids=owner_user_ids,
            )
            self.journals.set_owners(journal_id=journal_id, user_ids=owner_ids)

        return JournalResult(
            success=True,
            journal_id=journal_id,
            campaign_id=journal["campaign_id"],
            journal_type=journal_type,
            version=version,
        )

    def delete_journal(self, *, journal_id: str, requester_user_id: str) -> JournalResult:
        journal = self.journals.get_by_id(journal_id)
        if journal is None or journal["status"] != "active":
            return JournalResult(success=False, error_key="game.journal.errors.not_found")

        campaign = self.campaigns.get_for_user(
            campaign_id=journal["campaign_id"],
            user_id=requester_user_id,
        )
        if campaign is None:
            return JournalResult(success=False, error_key="game.journal.errors.not_found")

        campaign_dict = dict(campaign)
        is_owner = self.journals.has_owner(journal_id=journal_id, user_id=requester_user_id)
        if not _is_gm(campaign_dict) and not is_owner:
            return JournalResult(success=False, error_key="game.journal.errors.not_owner")

        self.journals.soft_delete(journal_id=journal_id)
        return JournalResult(
            success=True,
            journal_id=journal_id,
            campaign_id=journal["campaign_id"],
            journal_type=journal["type"],
        )

                                                                             

    def set_quest_status(
        self,
        *,
        quest_id: str,
        status: str,
        requester_user_id: str,
    ) -> JournalResult:
        journal, campaign, error = self._load_editable_quest(quest_id, requester_user_id)
        if error is not None:
            return error

        data = journal_data.normalize_quest_data(_decode_data(journal))
        data["status"] = journal_data.normalize_status(status)
        version = self.journals.update_data(
            journal_id=quest_id,
            data_json=json.dumps(data, separators=(",", ":")),
        )
        return JournalResult(
            success=True,
            journal_id=quest_id,
            campaign_id=journal["campaign_id"],
            journal_type="quest",
            version=version,
            changed_paths=["data.status"],
        )

    def toggle_objective(
        self,
        *,
        quest_id: str,
        objective_id: str,
        completed: bool,
        requester_user_id: str,
    ) -> JournalResult:
        journal, campaign, error = self._load_editable_quest(quest_id, requester_user_id)
        if error is not None:
            return error

        data = journal_data.normalize_quest_data(_decode_data(journal))
        found = False
        for objective in data["objectives"]:
            if objective["id"] == objective_id:
                objective["completed"] = bool(completed)
                found = True
                break
        if not found:
            return JournalResult(success=False, error_key="game.journal.errors.not_found")

        version = self.journals.update_data(
            journal_id=quest_id,
            data_json=json.dumps(data, separators=(",", ":")),
        )
        return JournalResult(
            success=True,
            journal_id=quest_id,
            campaign_id=journal["campaign_id"],
            journal_type="quest",
            version=version,
            changed_paths=["data.objectives"],
        )

                                                                             

    def add_quest_to_board(
        self,
        *,
        board_id: str,
        quest_id: str,
        requester_user_id: str,
        pinned: bool = False,
    ) -> JournalResult:
        board, campaign, error = self._load_editable_board(board_id, requester_user_id)
        if error is not None:
            return error

        quest = self.journals.get_by_id(quest_id)
        if (
            quest is None
            or quest["status"] != "active"
            or quest["type"] != "quest"
            or quest["campaign_id"] != board["campaign_id"]
        ):
            return JournalResult(success=False, error_key="game.journal.errors.not_found")

        sort_order = self.journals.next_board_sort_order(board_id=board_id)
        self.journals.add_board_entry(
            board_id=board_id,
            quest_id=quest_id,
            sort_order=sort_order,
            pinned=pinned,
        )
        return JournalResult(
            success=True,
            journal_id=board_id,
            campaign_id=board["campaign_id"],
            journal_type="quest_board",
        )

    def remove_quest_from_board(
        self,
        *,
        board_id: str,
        quest_id: str,
        requester_user_id: str,
    ) -> JournalResult:
        board, campaign, error = self._load_editable_board(board_id, requester_user_id)
        if error is not None:
            return error

        self.journals.remove_board_entry(board_id=board_id, quest_id=quest_id)
        return JournalResult(
            success=True,
            journal_id=board_id,
            campaign_id=board["campaign_id"],
            journal_type="quest_board",
        )

    def reorder_board(
        self,
        *,
        board_id: str,
        ordered_quest_ids: list[str],
        requester_user_id: str,
    ) -> JournalResult:
        board, campaign, error = self._load_editable_board(board_id, requester_user_id)
        if error is not None:
            return error

        existing = {entry["quest_id"] for entry in self.journals.list_board_entries(board_id=board_id)}
        filtered = [quest_id for quest_id in ordered_quest_ids if quest_id in existing]
        self.journals.set_board_entry_order(board_id=board_id, ordered_quest_ids=filtered)
        return JournalResult(
            success=True,
            journal_id=board_id,
            campaign_id=board["campaign_id"],
            journal_type="quest_board",
        )

    def set_board_quest_pinned(
        self,
        *,
        board_id: str,
        quest_id: str,
        pinned: bool,
        requester_user_id: str,
    ) -> JournalResult:
        board, campaign, error = self._load_editable_board(board_id, requester_user_id)
        if error is not None:
            return error

        if self.journals.get_board_entry(board_id=board_id, quest_id=quest_id) is None:
            return JournalResult(success=False, error_key="game.journal.errors.not_found")

        self.journals.set_board_entry_pinned(board_id=board_id, quest_id=quest_id, pinned=pinned)
        return JournalResult(
            success=True,
            journal_id=board_id,
            campaign_id=board["campaign_id"],
            journal_type="quest_board",
        )

                                                                             

    def build_view(self, *, journal: dict, campaign: dict, user_id: str) -> dict:
        """Return a role-appropriate projection of a journal.

        GMs (and edit-capable owners) get the full data; players only get the
        public projection. The structured payload never leaks GM-only fields.

        Read-only omniscient roles (GM, streamer) see all GM content; edit
        capability stays separate so a streamer never gets write affordances.
        """
        is_gm = has_full_view(campaign.get("member_role"))
        can_edit = self.can_edit_journal(journal=journal, campaign=campaign, user_id=user_id)
        full_access = is_gm or can_edit
        journal_type = journal["type"]
        view: dict = {
            "id": journal["id"],
            "type": journal_type,
            "title": journal["title"],
            "visibility": journal.get("visibility", "private"),
            "version": journal.get("version", 1),
            "folder_id": journal.get("folder_id"),
            "is_gm_view": full_access,
        }

        data = _decode_data(journal)
        if journal_type == "diary":
            from app.engine.journals import journal_doc

            diary = journal_data.normalize_diary_data(data)
                                                                              
                                                                     
            view["content_doc"] = journal_doc.filter_doc_for_role(
                diary["content"], is_gm=is_gm
            )
            view["cover_image"] = diary["cover"]
            if is_gm:
                view["diary"] = {"gm": diary["gm"]}
                                                                             
                                                                              
                                                                           
            view["content_markdown"] = (
                journal.get("content_markdown", "")
                if journal_doc.is_empty_document(view["content_doc"])
                else ""
            )
            return view

        if journal_type == "quest":
            from app.engine.journals import journal_doc

            if full_access:
                quest = journal_data.build_quest_gm_view(title=journal["title"], data=data)
            else:
                quest = journal_data.build_quest_player_view(title=journal["title"], data=data)
            if not is_gm:
                                                                              
                                                                         
                quest.pop("gm", None)
                quest["public"]["description"] = journal_doc.filter_doc_for_role(
                    quest["public"]["description"], is_gm=False
                )
            view["quest"] = quest
            view["content_markdown"] = journal.get("content_markdown", "")
            return view

        if journal_type == "quest_board":
            from app.engine.journals import journal_doc

            board = journal_data.normalize_board_data(data)
            view["board"] = {
                "description": journal_doc.filter_doc_for_role(
                    board["description"], is_gm=is_gm
                ),
                "description_markdown": board["description_markdown"],
                "image": board["image"],
                "filters": board["filters"],
            }
            view["board_entries"] = self._build_board_entries(
                board_id=journal["id"],
                campaign=campaign,
                user_id=user_id,
                filters=board["filters"],
                full_access=full_access,
            )
            return view

        return view

    def _build_board_entries(
        self,
        *,
        board_id: str,
        campaign: dict,
        user_id: str,
        filters: dict,
        full_access: bool,
    ) -> list[dict]:
        entries = self.journals.list_board_entries(board_id=board_id)
        result: list[dict] = []
        for entry in entries:
            quest = self.journals.get_by_id(entry["quest_id"])
            if quest is None or quest["status"] != "active" or quest["type"] != "quest":
                continue
            data = _decode_data(quest)
            card = journal_data.build_quest_card(title=quest["title"], data=data)
            status = card["status"]

            if not full_access:

                if status not in journal_data.PLAYER_VISIBLE_STATUSES:
                    continue
                if status == "available" and not filters.get("showAvailable", True):
                    continue
                if status == "active" and not filters.get("showActive", True):
                    continue
                if status == "completed" and not filters.get("showCompleted", True):
                    continue
                if status == "failed" and not filters.get("showFailed", True):
                    continue

            result.append(
                {
                    "quest_id": entry["quest_id"],
                    "pinned": bool(entry["pinned"]),
                    "sort_order": entry["sort_order"],
                    "card": card,
                }
            )
        return result

                                                                             

    def toggle_owner(
        self,
        *,
        journal_id: str,
        user_id_to_toggle: str,
        requester_user_id: str,
    ) -> JournalResult:
        journal = self.journals.get_by_id(journal_id)
        if journal is None or journal["status"] != "active":
            return JournalResult(success=False, error_key="game.journal.errors.not_found")

        campaign = self.campaigns.get_for_user(
            campaign_id=journal["campaign_id"],
            user_id=requester_user_id,
        )
        if campaign is None or not _is_gm(dict(campaign)):
            return JournalResult(success=False, error_key="game.journal.errors.not_owner")

        member = self.campaigns.get_member(
            campaign_id=journal["campaign_id"],
            user_id=user_id_to_toggle,
        )
        if member is None or member["role"] == "gm":
            return JournalResult(success=False, error_key="game.journal.errors.not_found")

        is_owner = self.journals.has_owner(journal_id=journal_id, user_id=user_id_to_toggle)
        if is_owner:
            self.journals.remove_owner(journal_id=journal_id, user_id=user_id_to_toggle)
            self.journal_permissions.upsert_for_user(
                journal_id=journal_id,
                user_id=user_id_to_toggle,
                can_view=False,
                can_edit=False,
            )
        else:
            self.journals.add_owner(journal_id=journal_id, user_id=user_id_to_toggle)
            self.journal_permissions.upsert_for_user(
                journal_id=journal_id,
                user_id=user_id_to_toggle,
                can_view=True,
                can_edit=True,
            )

        return JournalResult(
            success=True,
            journal_id=journal_id,
            campaign_id=journal["campaign_id"],
            is_owner=not is_owner,
        )

    def set_member_access(
        self,
        *,
        journal_id: str,
        target_user_id: str,
        access_level: str,
        requester_user_id: str,
    ) -> JournalResult:
        journal = self.journals.get_by_id(journal_id)
        if journal is None or journal["status"] != "active":
            return JournalResult(success=False, error_key="game.journal.errors.not_found")

        campaign = self.campaigns.get_for_user(
            campaign_id=journal["campaign_id"],
            user_id=requester_user_id,
        )
        if campaign is None or not _is_gm(dict(campaign)):
            return JournalResult(success=False, error_key="game.journal.errors.not_owner")

        member = self.campaigns.get_member(
            campaign_id=journal["campaign_id"],
            user_id=target_user_id,
        )
        if member is None or member["role"] == "gm":
            return JournalResult(success=False, error_key="game.journal.errors.not_found")

        normalized = access_level if access_level in {"none", "read", "owner"} else "none"
        if normalized == "owner":
            self.journals.add_owner(journal_id=journal_id, user_id=target_user_id)
            self.journal_permissions.upsert_for_user(
                journal_id=journal_id,
                user_id=target_user_id,
                can_view=True,
                can_edit=True,
            )
        elif normalized == "read":
            self.journals.remove_owner(journal_id=journal_id, user_id=target_user_id)
            self.journal_permissions.upsert_for_user(
                journal_id=journal_id,
                user_id=target_user_id,
                can_view=True,
                can_edit=False,
            )
        else:
            self.journals.remove_owner(journal_id=journal_id, user_id=target_user_id)
            self.journal_permissions.upsert_for_user(
                journal_id=journal_id,
                user_id=target_user_id,
                can_view=False,
                can_edit=False,
            )

        return JournalResult(success=True, journal_id=journal_id, campaign_id=journal["campaign_id"])

                                                                             

    def move_journal(
        self,
        *,
        journal_id: str,
        target_folder_id: str,
        requester_user_id: str,
    ) -> JournalResult:
        journal = self.journals.get_by_id(journal_id)
        if journal is None or journal["status"] != "active":
            return JournalResult(success=False, error_key="game.journal.errors.not_found")

        campaign = self.campaigns.get_for_user(
            campaign_id=journal["campaign_id"],
            user_id=requester_user_id,
        )
        if campaign is None:
            return JournalResult(success=False, error_key="game.journal.errors.not_found")

        campaign_dict = dict(campaign)
        if not _is_gm(campaign_dict):
            return JournalResult(success=False, error_key="game.journal.errors.not_owner")

        resolved: str | None
        if target_folder_id:
            folder = self.folders.get(
                folder_id=target_folder_id,
                campaign_id=journal["campaign_id"],
            )
            if folder is None:
                return JournalResult(success=False, error_key="game.journal.folders.errors.not_found")
            resolved = target_folder_id
        else:
            resolved = None

        self.journals.set_folder(journal_id=journal_id, folder_id=resolved)
        return JournalResult(
            success=True,
            journal_id=journal_id,
            campaign_id=journal["campaign_id"],
            folder_id=resolved,
        )

    def move_folder(
        self,
        *,
        folder_id: str,
        target_parent_id: str,
        requester_user_id: str,
    ) -> JournalResult:
        with_campaign_id: str | None = None
        for campaign in self.campaigns.list_for_user(user_id=requester_user_id):
            folder = self.folders.get(folder_id=folder_id, campaign_id=campaign["id"])
            if folder is not None:
                with_campaign_id = campaign["id"]
                break

        if with_campaign_id is None:
            return JournalResult(success=False, error_key="game.journal.folders.errors.not_found")

        campaign = self.campaigns.get_for_user(
            campaign_id=with_campaign_id,
            user_id=requester_user_id,
        )
        if campaign is None or not _is_gm(dict(campaign)):
            return JournalResult(success=False, error_key="game.journal.errors.not_owner")

        resolved_parent: str | None = None
        if target_parent_id:
            if target_parent_id == folder_id:
                return JournalResult(success=False, error_key="game.journal.folders.errors.not_found")
            parent = self.folders.get(
                folder_id=target_parent_id,
                campaign_id=with_campaign_id,
            )
            if parent is None:
                return JournalResult(success=False, error_key="game.journal.folders.errors.not_found")
            all_folders = self.folders.list_for_campaign(campaign_id=with_campaign_id)
            folder_by_id = {f["id"]: f for f in all_folders}
            cursor = parent
            seen: set[str] = set()
            while cursor is not None and cursor["id"] not in seen:
                if cursor["id"] == folder_id:
                    return JournalResult(success=False, error_key="game.journal.folders.errors.not_found")
                seen.add(cursor["id"])
                parent_id = cursor.get("parent_id")
                cursor = folder_by_id.get(parent_id) if parent_id else None
            resolved_parent = target_parent_id

        self.folders.set_parent(folder_id=folder_id, parent_id=resolved_parent)
        return JournalResult(
            success=True,
            folder_id=folder_id,
            campaign_id=with_campaign_id,
        )

                                                                             

    def _load_editable_quest(
        self, quest_id: str, requester_user_id: str
    ) -> tuple[dict | None, dict | None, JournalResult | None]:
        return self._load_editable(quest_id, requester_user_id, expected_type="quest")

    def _load_editable_board(
        self, board_id: str, requester_user_id: str
    ) -> tuple[dict | None, dict | None, JournalResult | None]:
        return self._load_editable(board_id, requester_user_id, expected_type="quest_board")

    def _load_editable(
        self, journal_id: str, requester_user_id: str, *, expected_type: str
    ) -> tuple[dict | None, dict | None, JournalResult | None]:
        journal = self.journals.get_by_id(journal_id)
        if (
            journal is None
            or journal["status"] != "active"
            or journal["type"] != expected_type
        ):
            return None, None, JournalResult(success=False, error_key="game.journal.errors.not_found")

        campaign = self.campaigns.get_for_user(
            campaign_id=journal["campaign_id"],
            user_id=requester_user_id,
        )
        if campaign is None:
            return None, None, JournalResult(success=False, error_key="game.journal.errors.not_found")

        campaign_dict = dict(campaign)
        if not self.can_edit_journal(journal=journal, campaign=campaign_dict, user_id=requester_user_id):
            return None, None, JournalResult(success=False, error_key="game.journal.errors.not_owner")

        return journal, campaign_dict, None

    def _resolve_folder(
        self,
        *,
        campaign_id: str,
        folder_id: str,
        campaign: dict,
        user_id: str,
    ) -> str | None:
        if not folder_id:
            return None

        folder = self.folders.get(folder_id=folder_id, campaign_id=campaign_id)
        if folder is None:
            return ""
        if not _is_gm(campaign) and folder["created_by_user_id"] != user_id:
            return ""
        return folder_id

    def _resolve_owner_ids(
        self,
        *,
        campaign_id: str,
        campaign: dict,
        user_id: str,
        owner_user_ids: list[str],
    ) -> list[str]:
        if not _is_gm(campaign):
            return [user_id]

        members = self.campaigns.list_members(campaign_id=campaign_id)
        allowed = {member["user_id"] for member in members if member["role"] != "gm"}
        return sorted({owner_id for owner_id in owner_user_ids if owner_id in allowed})
