"""Builds the render bundle for an item sheet (Gravewright SDK — mirrors ActorSheetService).

Items have no canvas/token projection, so the bundle is just:

    { item core summary, derived-applied data, Sheet IR layout, can_edit, version }

The frontend renderer (shared with actors) binds fields to ``sheet.data.patch``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.items.item_permissions import can_edit_item, can_view_item
from app.engine.rules.derived_field_service import apply_derived
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.sheets.sheet_ir_validator import validate_sheet_ir
from app.engine.sheets.system_layout_service import SystemLayoutService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.sdk.package_install_service import PackageInstallService
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.item_repository import ItemRepository


@dataclass(frozen=True)
class ItemSheetBundle:
    item_id: str
    campaign_id: str
    system_id: str
    name: str
    type: str
    version: int
    can_edit: bool
    layout: dict | None
    sheet: dict | None
    data: dict


class ItemSheetService:
    def __init__(self) -> None:
        self.items = ItemRepository()
        self.campaigns = CampaignRepository()
        self.storage = ScopedJsonStorage()
        self.systems = PackageInstallService()
        self.rules = SystemRulesService()
        self.layouts = SystemLayoutService()

    def build_bundle(self, *, item_id: str, user_id: str, locale: str | None = None) -> ItemSheetBundle | None:
        item = self.items.get(item_id)
        if item is None or item["status"] != "active":
            return None
        campaign = self.campaigns.get_for_user(campaign_id=item["campaign_id"], user_id=user_id)
        if campaign is None:
            return None
        campaign_dict = dict(campaign)
        if not can_view_item(item=item, campaign=campaign_dict, user_id=user_id):
            return None

        system_id = item["system_id"]
        envelope = self.storage.read_item(
            system_id=system_id, campaign_id=item["campaign_id"], item_id=item_id
        ) or {"version": 1, "data": {}}
        raw_data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}

        layout: dict | None = None
        sheet: dict | None = None
        data = raw_data
        if self.systems.get_active_manifest(system_id) is not None:
            sheet = self.layouts.get_item_html_sheet(
                system_id=system_id, item_type=item["type"]
            )
            if sheet is None:
                candidate = self.layouts.get_item_sheet(
                    system_id=system_id,
                    item_type=item["type"],
                    locale=locale,
                )
                if candidate is not None and not validate_sheet_ir(candidate):
                    layout = candidate
            helpers = self.rules.get_helpers(system_id)
            derived = self.rules.get_derived(system_id)
            data = apply_derived(
                actor_type=item["type"],
                data=raw_data,
                derived_rules=derived,
                helpers=helpers,
                core={"name": item["name"]},
            )

        return ItemSheetBundle(
            item_id=item_id,
            campaign_id=item["campaign_id"],
            system_id=system_id,
            name=item["name"],
            type=item["type"],
            version=int(envelope.get("version", 1)),
            can_edit=can_edit_item(item=item, campaign=campaign_dict, user_id=user_id),
            layout=layout,
            sheet=sheet,
            data=data,
        )

    def to_dict(self, bundle: ItemSheetBundle) -> dict:
        return {
            "item": {
                "id": bundle.item_id,
                "name": bundle.name,
                "type": bundle.type,
                "system_id": bundle.system_id,
            },
            "version": bundle.version,
            "can_edit": bundle.can_edit,
            "layout": bundle.layout,
            "sheet": bundle.sheet,
            "data": bundle.data,
        }

    def get_member_role(self, *, campaign_id: str, user_id: str) -> str | None:
        return self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
