"""``sheet.drop`` — drop content onto an actor sheet (§11.3, Canonical Drop Entry API).

Validates every step server-side (can the user edit the actor? does the dropZone
exist? is the entry accepted? does the onDrop action exist?) then runs the zone's
``onDrop`` append action with the resolved entry as ``@drop.entry.*``. The client
sends only an opaque ``source`` (a content pack entry *or* a campaign Item); the
:class:`DropEntryResolver` projects either origin to one canonical ``DropEntry``.
The heavy lifting (the append action + template resolution) lives in
:class:`SheetActionService`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

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
from app.engine.systems.system_install_service import SystemInstallService
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository


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
        self.systems = SystemInstallService()
        self.resolver = DropEntryResolver()
        self.layouts = SystemLayoutService()
        self.rules = SystemRulesService()
        self.actions = SheetActionService()

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
