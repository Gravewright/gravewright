"""Builds the render bundle for an actor sheet (System API v0, §8 + §19).

    bundle = { actor core summary, derived-applied data, Sheet IR layout,
               can_edit, version }

The frontend renderer (game-actor-sheets.js) interprets the layout, binds
fields to ``sheet.data.patch`` and buttons to ``sheet.action.execute``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.actors.actor_asset_urls import actor_image_url
from app.engine.actors.actor_permissions import can_edit_actor, can_view_actor
from app.engine.rules.derived_field_service import apply_derived
from app.engine.effects.active_effects import apply_stat_modifiers
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.sheets.sheet_ir_validator import validate_sheet_ir
from app.engine.sheets.system_layout_service import SystemLayoutService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.systems.system_install_service import SystemInstallService
from app.engine.tokens.actor_token_projector import ActorTokenProjector
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository


@dataclass(frozen=True)
class ActorSheetBundle:
    actor_id: str
    campaign_id: str
    system_id: str
    name: str
    type: str
    version: int
    can_edit: bool
    layout: dict | None
    data: dict
    portrait_url: str | None
    token_url: str | None
    summary: dict
    token_id: str | None = None
    source_actor_id: str | None = None
    token_link_mode: str | None = None


class ActorSheetService:
    def __init__(self) -> None:
        self.actors = ActorRepository()
        self.campaigns = CampaignRepository()
        self.storage = ScopedJsonStorage()
        self.systems = SystemInstallService()
        self.rules = SystemRulesService()
        self.layouts = SystemLayoutService()
        self.projector = ActorTokenProjector()

    def build_bundle(self, *, actor_id: str, user_id: str, locale: str | None = None) -> ActorSheetBundle | None:
        actor = self.actors.get(actor_id)
        if actor is None or actor["status"] != "active":
            return None
        campaign = self.campaigns.get_for_user(campaign_id=actor["campaign_id"], user_id=user_id)
        if campaign is None:
            return None
        campaign_dict = dict(campaign)
        if not can_view_actor(actor=actor, campaign=campaign_dict, user_id=user_id):
            return None

        system_id = actor["system_id"]
        envelope = self.storage.read_actor(
            system_id=system_id, campaign_id=actor["campaign_id"], actor_id=actor_id
        ) or {"version": 1, "data": {}}
        raw_data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}

        layout: dict | None = None
        data = raw_data
        if self.systems.get_active_manifest(system_id) is not None:
            candidate = self.layouts.get_actor_sheet(
                system_id=system_id,
                actor_type=actor["type"],
                locale=locale,
            )
            if candidate is not None and not validate_sheet_ir(candidate):
                layout = candidate
            helpers = self.rules.get_helpers(system_id)
            derived = self.rules.get_derived(system_id)
            data = apply_derived(
                actor_type=actor["type"],
                data=raw_data,
                derived_rules=derived,
                helpers=helpers,
                core={"name": actor["name"]},
            )
            data = apply_stat_modifiers(data)

        return ActorSheetBundle(
            actor_id=actor_id,
            campaign_id=actor["campaign_id"],
            system_id=system_id,
            name=actor["name"],
            type=actor["type"],
            version=int(envelope.get("version", 1)),
            can_edit=can_edit_actor(actor=actor, campaign=campaign_dict, user_id=user_id),
            layout=layout,
            data=data,
            portrait_url=actor_image_url(actor, "portrait"),
            token_url=actor_image_url(actor, "token"),
            summary=self.projector.project(actor),
            source_actor_id=actor_id,
        )

    def to_dict(self, bundle: ActorSheetBundle) -> dict:
        return {
            "actor": {
                "id": bundle.actor_id,
                "name": bundle.name,
                "type": bundle.type,
                "system_id": bundle.system_id,
                "token_id": bundle.token_id,
                "source_actor_id": bundle.source_actor_id,
                "token_link_mode": bundle.token_link_mode,
            },
            "version": bundle.version,
            "can_edit": bundle.can_edit,
            "layout": bundle.layout,
            "data": bundle.data,
            "portrait_url": bundle.portrait_url,
            "token_url": bundle.token_url,
            "summary": bundle.summary,
        }

    def get_member_role(self, *, campaign_id: str, user_id: str) -> str | None:
        return self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
