"""Actor Item Instance operations for Sheet SDK v1.

An item dropped on a sheet is stored as a snapshot inside Sheet Data. This
service finds that embedded instance, executes item-scoped actions with
``@item`` available to formulas, and mutates/removes only the actor-local copy.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from app.engine.actors.actor_permissions import can_edit_actor
from app.engine.rules.derived_field_service import apply_derived
from app.engine.effects.active_effects import apply_stat_modifiers
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.rules.token_mapping_resolver import resolve_token_view
from app.engine.sheets.sheet_action_service import ActionResult, SheetActionService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.systems.system_install_service import SystemInstallService
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository


@dataclass(frozen=True)
class SheetItemResult:
    success: bool
    actor_id: str | None = None
    campaign_id: str | None = None
    system_id: str | None = None
    version: int | None = None
    changed_paths: list[str] = field(default_factory=list)
    token_view: dict | None = None
    error_key: str | None = None


@dataclass
class _ItemRef:
    list_path: list[str]
    index: int
    item: dict


class SheetItemService:
    def __init__(self) -> None:
        self.actors = ActorRepository()
        self.campaigns = CampaignRepository()
        self.storage = ScopedJsonStorage()
        self.systems = SystemInstallService()
        self.rules = SystemRulesService()
        self.actions = SheetActionService()

    def execute_action(
        self,
        *,
        actor_id: str,
        user_id: str,
        item_instance_id: str,
        action_id: str,
        inputs: dict | None = None,
        roll_options: dict | None = None,
        target_actor_id: str | None = None,
        target_token_id: str | None = None,
    ) -> ActionResult:
        loaded = self._load_editable(actor_id=actor_id, user_id=user_id)
        if isinstance(loaded, SheetItemResult):
            return ActionResult(success=False, error_key=loaded.error_key)
        actor, _, data = loaded
        ref = _find_item_instance(data, item_instance_id)
        if ref is None:
            return ActionResult(success=False, error_key="game.sheet_items.errors.item_not_found")
        return self.actions.execute(
            actor_id=actor_id,
            action_id=action_id,
            user_id=user_id,
            inputs=inputs if isinstance(inputs, dict) else {},
            item=deepcopy(ref.item),
            roll_options=roll_options if isinstance(roll_options, dict) else None,
            target_actor_id=target_actor_id,
            target_token_id=target_token_id,
        )

    def patch_item(
        self,
        *,
        actor_id: str,
        user_id: str,
        item_instance_id: str,
        patch: dict,
    ) -> SheetItemResult:
        loaded = self._load_editable(actor_id=actor_id, user_id=user_id)
        if isinstance(loaded, SheetItemResult):
            return loaded
        actor, envelope, data = loaded
        ref = _find_item_instance(data, item_instance_id)
        if ref is None:
            return SheetItemResult(success=False, error_key="game.sheet_items.errors.item_not_found")
        if not isinstance(patch, dict) or not patch:
            return SheetItemResult(success=False, error_key="game.sheet_items.errors.invalid_patch")
        for path, value in patch.items():
            if not isinstance(path, str) or not path:
                continue
            _set_item_path(ref.item, path, value)
        return self._write(actor, envelope, data, _changed_path(ref))

    def remove_item(self, *, actor_id: str, user_id: str, item_instance_id: str) -> SheetItemResult:
        loaded = self._load_editable(actor_id=actor_id, user_id=user_id)
        if isinstance(loaded, SheetItemResult):
            return loaded
        actor, envelope, data = loaded
        ref = _find_item_instance(data, item_instance_id)
        if ref is None:
            return SheetItemResult(success=False, error_key="game.sheet_items.errors.item_not_found")
        parent = _get_path(data, ref.list_path)
        if not isinstance(parent, list):
            return SheetItemResult(success=False, error_key="game.sheet_items.errors.item_not_found")
        del parent[ref.index]
        return self._write(actor, envelope, data, _changed_path(ref))

    def _load_editable(self, *, actor_id: str, user_id: str) -> tuple[dict, dict, dict] | SheetItemResult:
        actor = self.actors.get(actor_id)
        if actor is None or actor["status"] != "active":
            return SheetItemResult(success=False, error_key="game.actors.errors.not_found")
        campaign = self.campaigns.get_for_user(campaign_id=actor["campaign_id"], user_id=user_id)
        if campaign is None:
            return SheetItemResult(success=False, error_key="game.actors.errors.not_found")
        campaign_dict = dict(campaign)
        if self.systems.get_active_manifest(actor["system_id"]) is None:
            return SheetItemResult(success=False, error_key="game.actors.errors.system_not_enabled")
        if not can_edit_actor(actor=actor, campaign=campaign_dict, user_id=user_id):
            return SheetItemResult(success=False, error_key="game.actors.errors.not_allowed")
        envelope = self.storage.read_actor(
            system_id=actor["system_id"], campaign_id=actor["campaign_id"], actor_id=actor_id
        ) or {"version": 1, "data": {}}
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        return actor, envelope, data

    def _write(self, actor: dict, envelope: dict, data: dict, changed_path: str) -> SheetItemResult:
        version = int(envelope.get("version", 1)) + 1
        self.storage.write_actor(
            system_id=actor["system_id"], campaign_id=actor["campaign_id"], actor_id=actor["id"],
            version=version, data=data,
        )
        return SheetItemResult(
            success=True,
            actor_id=actor["id"],
            campaign_id=actor["campaign_id"],
            system_id=actor["system_id"],
            version=version,
            changed_paths=[changed_path],
            token_view=self._token_view(actor, data),
        )

    def _token_view(self, actor: dict, data: dict) -> dict:
        mappings = self.rules.get_token_mappings(actor["system_id"])
        if not mappings:
            return {}
        helpers = self.rules.get_helpers(actor["system_id"])
        derived = self.rules.get_derived(actor["system_id"])
        core = {"name": actor["name"]}
        derived_data = apply_derived(
            actor_type=actor["type"], data=data, derived_rules=derived, helpers=helpers, core=core
        )
        effective_data = apply_stat_modifiers(derived_data)
        return resolve_token_view(
            actor_type=actor["type"], sheet_data=effective_data, core=core, token_mappings=mappings
        )


def _find_item_instance(data: dict, item_id: str) -> _ItemRef | None:
    if not item_id:
        return None

    def visit(node: Any, path: list[str]) -> _ItemRef | None:
        if isinstance(node, dict):
            for key, value in node.items():
                result = visit(value, [*path, key])
                if result is not None:
                    return result
        if isinstance(node, list):
            for index, value in enumerate(node):
                if isinstance(value, dict) and value.get("id") == item_id:
                    return _ItemRef(list_path=path, index=index, item=value)
                result = visit(value, path)
                if result is not None:
                    return result
        return None

    return visit(data, [])


def _changed_path(ref: _ItemRef) -> str:
    dotted = ".".join(ref.list_path)
    return f"sheet.{dotted}"


def _get_path(data: dict, path: list[str]) -> Any:
    cursor: Any = data
    for segment in path:
        if isinstance(cursor, dict):
            cursor = cursor.get(segment)
        else:
            return None
    return cursor


def _set_item_path(item: dict, dotted: str, value: Any) -> None:
    segments = [segment for segment in dotted.split(".") if segment]
    if not segments:
        return
    cursor: Any = item
    for segment in segments[:-1]:
        if not isinstance(cursor, dict):
            return
        nxt = cursor.get(segment)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[segment] = nxt
        cursor = nxt
    if isinstance(cursor, dict):
        cursor[segments[-1]] = value
