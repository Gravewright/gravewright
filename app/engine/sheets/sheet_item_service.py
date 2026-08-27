"""Actor Item Instance operations for Sheet SDK v1.

An item dropped on a sheet is stored as a snapshot inside Sheet Data. This
service finds that embedded instance, executes item-scoped actions with
``@item`` available to formulas, and mutates/removes only the actor-local copy.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import Any

from app.engine.actors.actor_permissions import can_edit_actor
from app.engine.rules.derived_field_service import apply_derived
from app.engine.effects.active_effects import apply_stat_modifiers
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.rules.token_mapping_resolver import resolve_token_view
from app.engine.sheets.sheet_action_service import ActionResult, SheetActionService
from app.engine.sheets.system_layout_service import SystemLayoutService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.sdk.package_install_service import PackageInstallService
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
        self.systems = PackageInstallService()
        self.rules = SystemRulesService()
        self.actions = SheetActionService()
        self.layouts = SystemLayoutService()

    def build_embedded_bundle(
        self, *, actor_id: str, user_id: str, item_instance_id: str, locale: str | None = None
    ) -> dict | None:
        loaded = self._load_editable(actor_id=actor_id, user_id=user_id)
        if isinstance(loaded, SheetItemResult):
            return None
        actor, _, data = loaded
        ref = _find_item_instance(data, item_instance_id)
        if ref is None:
            return None
        item = deepcopy(ref.item)
        item_type = str(item.get("type") or "")
        return {
            "item": {
                "id": str(item.get("id") or item_instance_id),
                "name": str(item.get("name") or ""),
                "type": item_type,
                "system_id": actor["system_id"],
            },
            "can_edit": True,
            "layout": self.layouts.get_item_sheet(
                system_id=actor["system_id"], item_type=item_type, locale=locale
            ),
            "sheet": self.layouts.get_item_html_sheet(
                system_id=actor["system_id"], item_type=item_type
            ),
            "data": deepcopy(item.get("data") if isinstance(item.get("data"), dict) else {}),
        }

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
        actor, envelope, data = loaded
        ref = _find_item_instance(data, item_instance_id)
        if ref is None:
            return ActionResult(success=False, error_key="game.sheet_items.errors.item_not_found")
        action = self.rules.get_action(actor["system_id"], action_id)
        if not isinstance(action, dict):
            return ActionResult(success=False, error_key="game.actions.errors.action_not_found")
        if action.get("type") == "itemPatch":
            return self._execute_item_patch(actor, envelope, data, ref, action)
        action_item = deepcopy(ref.item)
        linked_skill = _find_linked_skill(data, action_item)
        if linked_skill is not None:
            linked_data = (
                linked_skill.get("data") if isinstance(linked_skill.get("data"), dict) else {}
            )
            linked_die = linked_data.get("die")
            item_data = (
                action_item.get("data") if isinstance(action_item.get("data"), dict) else {}
            )
            action_item["data"] = item_data
            if isinstance(linked_die, dict):
                item_data["die"] = deepcopy(linked_die)
        elif action_id.startswith("roll.attack"):


            item_data = (
                action_item.get("data") if isinstance(action_item.get("data"), dict) else {}
            )
            action_item["data"] = item_data
            item_data.setdefault("die", {"sides": 4, "modifier": -2})
        resource = action.get("itemResource") if isinstance(action.get("itemResource"), dict) else None
        if resource and not _item_resource_selection_valid(action_item, resource, roll_options):
            return ActionResult(success=False, error_key="game.sheet_items.errors.invalid_resource_amount")
        resource_cost = _item_resource_cost(resource, roll_options)
        if resource and not _item_resource_enabled(action_item, resource):
            resource_cost = 0
        if resource_cost and not _item_has_resource(action_item, resource, resource_cost):
            return ActionResult(success=False, error_key="game.sheet_items.errors.insufficient_resource")
        actor_resource = action.get("actorResource") if isinstance(action.get("actorResource"), dict) else None
        actor_resource_cost = _actor_resource_cost(action_item, actor_resource, roll_options)
        if actor_resource_cost and not _actor_has_resource(data, actor_resource, actor_resource_cost):
            return ActionResult(success=False, error_key="game.sheet_items.errors.insufficient_actor_resource")
        result = self.actions.execute(
            actor_id=actor_id,
            action_id=action_id,
            user_id=user_id,
            inputs=inputs if isinstance(inputs, dict) else {},
            item=action_item,
            roll_options=roll_options if isinstance(roll_options, dict) else None,
            target_actor_id=target_actor_id,
            target_token_id=target_token_id,
        )
        if result.success and resource_cost:
            mutation = self._consume_item_resource(
                actor=actor,
                item_instance_id=item_instance_id,
                resource=resource,
                amount=resource_cost,
            )
            if not mutation.success:
                return ActionResult(success=False, error_key=mutation.error_key)
            result = replace(
                result,
                version=mutation.version,
                changed_paths=mutation.changed_paths,
                token_view=mutation.token_view,
                metadata={**result.metadata, "itemResource": {"consumed": resource_cost}},
            )
        if result.success and actor_resource_cost:
            mutation = self._consume_actor_resource(
                actor=actor, resource=actor_resource, amount=actor_resource_cost,
            )
            if not mutation.success:
                return ActionResult(success=False, error_key=mutation.error_key)
            result = replace(
                result,
                version=mutation.version,
                changed_paths=[*result.changed_paths, *mutation.changed_paths],
                token_view=mutation.token_view,
                metadata={
                    **result.metadata,
                    "actorResource": {"consumed": actor_resource_cost, "path": actor_resource.get("path")},
                },
            )
        return result

    def _execute_item_patch(self, actor, envelope, data, ref, action) -> ActionResult:
        patch = action.get("patch") if isinstance(action.get("patch"), dict) else {}
        changed = False
        for path, value in patch.items():
            if isinstance(value, dict) and isinstance(value.get("from"), str):
                value = _get_item_path(ref.item, value["from"])
            if value is None:
                continue
            _set_item_path(ref.item, path, value)
            changed = True
        if not changed:
            return ActionResult(success=False, error_key="game.sheet_items.errors.invalid_patch")
        mutation = self._write(actor, envelope, data, _changed_path(ref))
        return ActionResult(
            success=True, actor_id=mutation.actor_id, campaign_id=mutation.campaign_id,
            system_id=mutation.system_id, action_type="itemPatch", version=mutation.version,
            changed_paths=mutation.changed_paths, token_view=mutation.token_view,
        )

    def _consume_item_resource(self, *, actor, item_instance_id, resource, amount):
        with self.storage.lock_entity(
            kind="actor", system_id=actor["system_id"],
            campaign_id=actor["campaign_id"], entity_id=actor["id"],
        ):
            envelope = self.storage.read_actor(
                system_id=actor["system_id"], campaign_id=actor["campaign_id"], actor_id=actor["id"]
            ) or {"version": 1, "data": {}}
            data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
            ref = _find_item_instance(data, item_instance_id)
            if ref is None:
                return SheetItemResult(success=False, error_key="game.sheet_items.errors.item_not_found")
            path = str(resource.get("path") or "")
            current = _get_item_path(ref.item, path)
            try:
                current = int(current)
            except (TypeError, ValueError):
                current = 0
            if current < amount:
                return SheetItemResult(success=False, error_key="game.sheet_items.errors.insufficient_resource")
            _set_item_path(ref.item, path, current - amount)
            return self._write(actor, envelope, data, _changed_path(ref))

    def _consume_actor_resource(self, *, actor, resource, amount):
        with self.storage.lock_entity(
            kind="actor", system_id=actor["system_id"],
            campaign_id=actor["campaign_id"], entity_id=actor["id"],
        ):
            envelope = self.storage.read_actor(
                system_id=actor["system_id"], campaign_id=actor["campaign_id"], actor_id=actor["id"]
            ) or {"version": 1, "data": {}}
            data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
            path = str(resource.get("path") or "")
            current = _get_data_path(data, path)
            try:
                current = int(current)
            except (TypeError, ValueError):
                current = 0
            if current < amount:
                return SheetItemResult(success=False, error_key="game.sheet_items.errors.insufficient_actor_resource")
            _set_data_path(data, path, current - amount)
            version = int(envelope.get("version", 1)) + 1
            self.storage.write_actor(
                system_id=actor["system_id"], campaign_id=actor["campaign_id"],
                actor_id=actor["id"], version=version, data=data,
            )
            return SheetItemResult(
                success=True, actor_id=actor["id"], campaign_id=actor["campaign_id"],
                system_id=actor["system_id"], version=version,
                changed_paths=[path], token_view=self._token_view(actor, data),
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
            return SheetItemResult(
                success=False, error_key="game.sheet_items.errors.item_not_found"
            )
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
            return SheetItemResult(
                success=False, error_key="game.sheet_items.errors.item_not_found"
            )
        parent = _get_path(data, ref.list_path)
        if not isinstance(parent, list):
            return SheetItemResult(
                success=False, error_key="game.sheet_items.errors.item_not_found"
            )
        del parent[ref.index]
        return self._write(actor, envelope, data, _changed_path(ref))

    def _load_editable(
        self, *, actor_id: str, user_id: str
    ) -> tuple[dict, dict, dict] | SheetItemResult:
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
            system_id=actor["system_id"],
            campaign_id=actor["campaign_id"],
            actor_id=actor["id"],
            version=version,
            data=data,
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


def _find_linked_skill(data: dict, item: dict) -> dict | None:
    """Resolve the skill named by an embedded item for item-scoped actions."""
    item_data = item.get("data") if isinstance(item.get("data"), dict) else {}
    wanted_name = item_data.get("skill")
    if not wanted_name and str(item.get("type") or "") == "power":
        power = data.get("power") if isinstance(data.get("power"), dict) else {}
        wanted_name = power.get("skill")
    wanted = str(wanted_name or "").strip().casefold()
    if not wanted:
        return None
    skills = data.get("skills") if isinstance(data.get("skills"), list) else []
    for skill in skills:
        if not isinstance(skill, dict) or str(skill.get("type") or "") != "skill":
            continue
        if str(skill.get("name") or "").strip().casefold() == wanted:
            return skill
    return None


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


def _get_item_path(item: dict, dotted: str) -> Any:
    cursor: Any = item
    for segment in (part for part in str(dotted).split(".") if part):
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(segment)
    return cursor


def _item_resource_cost(resource: dict | None, roll_options: dict | None) -> int:
    if not resource:
        return 0
    options = roll_options if isinstance(roll_options, dict) else {}
    selected = str(options.get(resource.get("input", "")) or resource.get("default", 1))
    table = resource.get("costs") if isinstance(resource.get("costs"), dict) else {}
    try:
        return max(0, int(table.get(selected, selected)))
    except (TypeError, ValueError):
        return 0


def _item_has_resource(item: dict, resource: dict | None, amount: int) -> bool:
    if not resource or amount < 1:
        return True
    capacity = _get_item_path(item, str(resource.get("capacityPath") or ""))
    try:
        capacity = int(capacity)
    except (TypeError, ValueError):
        capacity = 0
    if capacity < 1:  # Capacidade zero representa uma arma sem controle de munição.
        return True
    current = _get_item_path(item, str(resource.get("path") or ""))
    try:
        return int(current) >= amount
    except (TypeError, ValueError):
        return False


def _item_resource_enabled(item: dict, resource: dict) -> bool:
    try:
        return int(_get_item_path(item, str(resource.get("capacityPath") or ""))) > 0
    except (TypeError, ValueError):
        return False


def _item_resource_selection_valid(item: dict, resource: dict, roll_options: dict | None) -> bool:
    limit_path = str(resource.get("limitPath") or "")
    if not limit_path:
        return True
    options = roll_options if isinstance(roll_options, dict) else {}
    try:
        selected = int(options.get(str(resource.get("input") or ""), resource.get("default", 1)))
        limit = int(_get_item_path(item, limit_path))
    except (TypeError, ValueError):
        return False
    return 1 <= selected <= max(1, limit)


def _actor_resource_cost(item: dict, resource: dict | None, roll_options: dict | None = None) -> int:
    if not resource:
        return 0
    try:
        base = max(0, int(_get_item_path(item, str(resource.get("costPath") or ""))))
    except (TypeError, ValueError):
        base = 0
    options = roll_options if isinstance(roll_options, dict) else {}
    try:
        extra = max(0, int(options.get(str(resource.get("extraCostInput") or ""), 0)))
    except (TypeError, ValueError):
        extra = 0
    return base + extra


def _actor_has_resource(data: dict, resource: dict | None, amount: int) -> bool:
    if not resource or amount < 1:
        return True
    try:
        return int(_get_data_path(data, str(resource.get("path") or ""))) >= amount
    except (TypeError, ValueError):
        return False


def _get_data_path(data: dict, dotted: str) -> Any:
    cursor: Any = data
    for segment in (part for part in str(dotted).split(".") if part):
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(segment)
    return cursor


def _set_data_path(data: dict, dotted: str, value: Any) -> None:
    segments = [part for part in str(dotted).split(".") if part]
    if not segments:
        return
    cursor: Any = data
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
