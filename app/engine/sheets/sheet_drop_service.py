"""``sheet.drop``: drop content onto an actor sheet (§11.3, Canonical Drop Entry API).

Validates every step server-side (can the user edit the actor? does the dropZone
exist? is the entry accepted? does the onDrop action exist?) then runs the zone's
``onDrop`` append action with the resolved entry as ``@drop.entry.*``. The client
sends only an opaque ``source`` (a content pack entry *or* a campaign Item); the
:class:`DropEntryResolver` projects either origin to one canonical ``DropEntry``.
The heavy lifting (the append action + template resolution) lives in
:class:`SheetActionService`.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass, field
from uuid import uuid4

from app.engine.actors.actor_permissions import can_edit_actor
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.sheets.drop_entry_resolver import DropEntryResolver
from app.engine.sheets.sheet_action_service import SheetActionService
from app.engine.sheets.system_layout_service import SystemLayoutService
from app.engine.sheets.sheet_ir_validator import (
    accepts_entry,
    find_drop_zone,
    find_matching_drop_zone,
)
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository



HTML_DROP_LIST = "items"
HTML_EFFECT_LIST = "effects"




_LIST_KEY_RE = re.compile(r"[^A-Za-z0-9_]")


def html_list_path(drop_zone: str) -> str:
    key = _LIST_KEY_RE.sub("", str(drop_zone or ""))
    return key or HTML_DROP_LIST


def html_drop_list(sheet: dict | None, entry_type: str, drop_zone: str = "") -> str:
    """Resolve an HTML-sheet drop to the collection declared by the manifest."""
    for zone in (sheet or {}).get("dropZones") or []:
        if accepts_entry(zone.get("accepts") or [], entry_type):
            return html_list_path(zone.get("list", ""))
    return html_list_path(drop_zone)


def embedded_item_copy(entry) -> dict:
    snapshot = deepcopy(entry.as_dict())
    snapshot["id"] = uuid4().hex
    return snapshot


@dataclass(frozen=True)
class DropResult:
    success: bool
    actor_id: str | None = None
    campaign_id: str | None = None
    system_id: str | None = None
    version: int | None = None
    changed_paths: list[str] = field(default_factory=list)
    token_view: dict | None = None
    error_key: str | None = None


class SheetDropService:
    def __init__(self) -> None:
        self.actors = ActorRepository()
        self.campaigns = CampaignRepository()
        self.systems = PackageInstallService()
        self.resolver = DropEntryResolver()
        self.layouts = SystemLayoutService()
        self.rules = SystemRulesService()
        self.actions = SheetActionService()
        self.storage = ScopedJsonStorage()

    def drop(
        self,
        *,
        actor_id: str,
        user_id: str,
        source: dict,
        drop_zone: str,
    ) -> DropResult:
        actor = self.actors.get(actor_id)
        if actor is None or actor["status"] != "active":
            return DropResult(success=False, error_key="game.actors.errors.not_found")
        campaign = self.campaigns.get_for_user(campaign_id=actor["campaign_id"], user_id=user_id)
        if campaign is None:
            return DropResult(success=False, error_key="game.actors.errors.not_found")
        campaign_dict = dict(campaign)
        if not can_edit_actor(actor=actor, campaign=campaign_dict, user_id=user_id):
            return DropResult(success=False, error_key="game.actors.errors.not_allowed")

        system_id = actor["system_id"]
        if self.systems.get_active_manifest(system_id) is None:
            return DropResult(success=False, error_key="game.actors.errors.system_not_enabled")

        entry, entry_error = self.resolver.resolve(
            system_id=system_id,
            campaign_id=actor["campaign_id"],
            campaign=campaign_dict,
            user_id=user_id,
            source=source if isinstance(source, dict) else {},
        )
        if entry is None:
            return DropResult(success=False, error_key=entry_error)





        html_list = self._html_list_for(system_id, actor["type"], entry.drop_type, drop_zone)
        if html_list is not None:
            return self._append_to_html_list(actor, entry, list_path=html_list)

        layout = self.layouts.get_actor_sheet(system_id=system_id, actor_type=actor["type"])
        if drop_zone:
            zone = find_drop_zone(layout, drop_zone) if layout else None
            if zone is None:
                return DropResult(success=False, error_key="game.drop.errors.zone_not_found")
            if not accepts_entry(zone["accepts"], entry.drop_type):
                return DropResult(success=False, error_key="game.drop.errors.not_accepted")
        else:
            zone = find_matching_drop_zone(layout, entry.drop_type) if layout else None
            if zone is None:
                return DropResult(success=False, error_key="game.drop.errors.not_accepted")

        action_id = zone.get("onDrop")
        if not action_id or self.rules.get_action(system_id, action_id) is None:
            return DropResult(success=False, error_key="game.drop.errors.action_not_found")

        drop_context = {"entry": entry.as_dict(), "source": entry.source}
        result = self.actions.execute(
            actor_id=actor_id, action_id=action_id, user_id=user_id, drop=drop_context
        )
        if not result.success:
            return DropResult(success=False, error_key=result.error_key)
        return DropResult(
            success=True,
            actor_id=actor_id,
            campaign_id=result.campaign_id,
            system_id=system_id,
            version=result.version,
            changed_paths=result.changed_paths,
            token_view=result.token_view,
        )

    def _html_list_for(
        self, system_id: str, actor_type: str, entry_type: str, drop_zone: str
    ) -> str | None:
        """The sheet-data list a dropped entry belongs to, for an HTML sheet.

        ``None`` when this actor's sheet is not HTML-mode, so the declarative
        path stays exactly as it was.
        """
        sheet = self._html_sheet(system_id, actor_type)
        if sheet is None:
            return None


        return html_drop_list(sheet, entry_type, drop_zone)

    def _html_sheet(self, system_id: str, actor_type: str) -> dict | None:
        manifest = self.systems.get_active_manifest(system_id)
        if manifest is None:
            return None
        for type_def in manifest.actor_types:
            if type_def.id == actor_type:
                return type_def.html_sheet
        return None

    def _is_html_sheet(self, system_id: str, actor_type: str) -> bool:
        manifest = self.systems.get_active_manifest(system_id)
        if manifest is None:
            return False
        for type_def in manifest.actor_types:
            if type_def.id == actor_type:
                return type_def.html_sheet is not None
        return False

    def _append_to_html_list(
        self, actor: dict, entry, *, list_path: str = HTML_DROP_LIST
    ) -> DropResult:
        envelope = self.storage.read_actor(
            system_id=actor["system_id"], campaign_id=actor["campaign_id"], actor_id=actor["id"]
        ) or {"version": 1, "data": {}}
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        items = data.get(list_path)
        if not isinstance(items, list):
            items = []
            data[list_path] = items
        items.append(embedded_item_copy(entry))
        version = int(envelope.get("version", 1)) + 1
        self.storage.write_actor(
            system_id=actor["system_id"],
            campaign_id=actor["campaign_id"],
            actor_id=actor["id"],
            version=version,
            data=data,
        )
        return DropResult(
            success=True,
            actor_id=actor["id"],
            campaign_id=actor["campaign_id"],
            system_id=actor["system_id"],
            version=version,
            changed_paths=[list_path],
        )
