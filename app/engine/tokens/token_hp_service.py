from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from app.domain.roles import PlayerRole
from app.domain.tokens import TokenActorLinkMode
from app.engine.actors.actor_permissions import can_edit_actor
from app.engine.combat.combat_config import CombatConfigService
from app.engine.effects.active_effects import apply_resource_delta
from app.engine.effects.active_effects import resolve_resource_target
from app.engine.sheets.sheet_validation import sanitize_write
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.tokens.actor_token_projector import ActorTokenProjector
from app.engine.tokens.token_instance_sheet_service import INSTANCE_KEY
from app.engine.tokens.token_instance_sheet_service import TokenInstanceSheetService
from app.engine.tokens.token_view_service import TokenViewService
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.sheets.schema_service import SchemaService
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.token_condition_repository import TokenConditionRepository
from app.persistence.repositories.token_repository import TokenRepository


@dataclass(frozen=True)
class TokenHpResult:
    success: bool
    token_id: str | None = None
    actor_id: str | None = None
    campaign_id: str | None = None
    scene_id: str | None = None
    system_id: str | None = None
    operation: str | None = None
    amount: int | None = None
    value_before: int | None = None
    value_after: int | None = None
    max_value: int | None = None
    value_path: str | None = None
    max_path: str | None = None
    version: int | None = None
    token_version: int | None = None
    token_view: dict = field(default_factory=dict)
    changed_paths: list[str] = field(default_factory=list)
    linked_actor: bool = False
    error_key: str | None = None


class TokenHpService:
    """Server-authoritative HP editing for scene tokens.

    The edited resource is system-defined: the service resolves ``resources.hp``
    from ``rules/combat.gw.json`` and falls back to ``hp.value``/``hp.max`` for
    simple systems. Linked tokens write to the source Actor sheet; unlinked
    tokens write only to the token-local ``_actor_instance`` snapshot.
    """

    def __init__(self) -> None:
        self.tokens = TokenRepository()
        self.conditions = TokenConditionRepository()
        self.actors = ActorRepository()
        self.scenes = SceneRepository()
        self.campaigns = CampaignRepository()
        self.storage = ScopedJsonStorage()
        self.rules = SystemRulesService()
        self.schemas = SchemaService()
        self.combat_config = CombatConfigService()
        self.projector = ActorTokenProjector()
        self.views = TokenViewService()
        self.token_instances = TokenInstanceSheetService()

    def update_hp(
        self,
        *,
        campaign_id: str,
        scene_id: str,
        token_id: str,
        user_id: str,
        operation: str,
        amount: int | None = None,
        value: int | None = None,
    ) -> TokenHpResult:
        scene = self.scenes.get_by_id(scene_id)
        if scene is None or scene["campaign_id"] != campaign_id:
            return TokenHpResult(success=False, error_key="tokens.errors.scene_not_found")

        token = self.tokens.get_by_scene_and_id(scene_id=scene_id, token_id=token_id)
        if token is None or not token.get("actor_id"):
            return TokenHpResult(success=False, error_key="tokens.errors.not_found")

        actor = self.actors.get(token["actor_id"])
        if actor is None or actor["status"] != "active" or actor["campaign_id"] != campaign_id:
            return TokenHpResult(success=False, error_key="tokens.errors.not_found")

        if not self._can_control_token(token=token, actor=actor, campaign_id=campaign_id, user_id=user_id):
            return TokenHpResult(success=False, error_key="tokens.errors.permission_denied")

        op = _normalize_operation(operation)
        if op is None:
            return TokenHpResult(success=False, error_key="tokens.errors.invalid_hp_operation")

        resource = self._hp_resource(actor["system_id"])
        if resource is None:
            return TokenHpResult(success=False, error_key="tokens.errors.hp_not_configured")
        value_path, max_path, floor = resource

        is_unlinked = token.get("actor_link_mode") == TokenActorLinkMode.UNLINKED
        envelope = None
        overrides = deepcopy(token.get("overrides") or {})

        if is_unlinked:
            instance = deepcopy(overrides.get(INSTANCE_KEY) or self.token_instances.make_instance_snapshot(actor=actor))
            data = instance.get("data") if isinstance(instance.get("data"), dict) else {}
        else:
            envelope = self.storage.read_actor(
                system_id=actor["system_id"],
                campaign_id=campaign_id,
                actor_id=actor["id"],
            ) or {"version": 1, "data": {}}
            data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}

        before = _coerce_int(_get_path(data, value_path), default=0)
        max_value = _resolve_max(data, value_path, max_path)
        delta_amount = _coerce_int(amount, default=0)
        set_value = _coerce_int(value, default=before)

        if op == "damage":
            delta = -abs(delta_amount)
            applied_amount = abs(delta_amount)
            after = apply_resource_delta(data, value_path, max_path, floor, delta)
        elif op == "heal":
            delta = abs(delta_amount)
            applied_amount = abs(delta_amount)
            after = apply_resource_delta(data, value_path, max_path, floor, delta)
        elif op == "adjust":
            delta = delta_amount
            applied_amount = delta_amount
            after = apply_resource_delta(data, value_path, max_path, floor, delta)
        else:       
            applied_amount = set_value
            after = _clamp_value(set_value, floor=floor, max_value=max_value)
            _set_path(data, value_path, after)

        if after is None:
            return TokenHpResult(success=False, error_key="tokens.errors.hp_not_configured")

        clean, _rejected = sanitize_write(
            self.schemas.get_actor_schema(system_id=actor["system_id"], actor_type=actor["type"]),
            self.rules.get_validation(actor["system_id"], actor["type"]),
            {value_path: after},
        )
        if value_path in clean and clean[value_path] != after:
            after = _coerce_int(clean[value_path], default=after)
            _set_path(data, value_path, after)

        if is_unlinked:
            instance["data"] = data
            instance["version"] = int(instance.get("version", 1)) + 1
            overrides[INSTANCE_KEY] = instance
            projection = self.projector.project(_actor_with_name(actor, instance.get("name") or actor["name"]), envelope={"version": instance["version"], "data": deepcopy(data)})
            bars = projection.get("bars")
            if isinstance(bars, dict):
                overrides.update(bars)
            effects = projection.get("effects")
            if isinstance(effects, list):
                overrides["effects"] = effects
            updated_token = self.tokens.update_overrides(token_id=token_id, overrides=overrides) or token
            version = int(instance["version"])
            token_version = int(updated_token.get("version") or token.get("version") or 0)
            token_for_view = updated_token
        else:
            assert envelope is not None
            version = int(envelope.get("version", 1)) + 1
            self.storage.write_actor(
                system_id=actor["system_id"],
                campaign_id=campaign_id,
                actor_id=actor["id"],
                version=version,
                data=data,
            )
            token_version = int(token.get("version") or 0)
            token_for_view = token
            projection = self.projector.project(actor, envelope={"version": version, "data": deepcopy(data)})

        conditions = self.conditions.list_by_token(token_id)
        token_view = self.views.build_view(token=token_for_view, projection=projection, actor=actor, conditions=conditions)
        return TokenHpResult(
            success=True,
            token_id=token_id,
            actor_id=actor["id"],
            campaign_id=campaign_id,
            scene_id=scene_id,
            system_id=actor["system_id"],
            operation=op,
            amount=applied_amount,
            value_before=before,
            value_after=after,
            max_value=_resolve_max(data, value_path, max_path),
            value_path=value_path,
            max_path=max_path,
            version=version,
            token_version=token_version,
            token_view=token_view,
            changed_paths=[value_path],
            linked_actor=not is_unlinked,
        )

    def _hp_resource(self, system_id: str) -> tuple[str, str, int] | None:
        config = self.combat_config.get_for_system(system_id)
        resources = config.resources if isinstance(config.resources, dict) else {}
        return resolve_resource_target("resource.hp", resources) or resolve_resource_target("damage.self", resources)

    def _can_control_token(self, *, token: dict, actor: dict, campaign_id: str, user_id: str) -> bool:
        member_role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        if member_role is None:
            return False
        if member_role == PlayerRole.GM.value:
            return True
        return can_edit_actor(actor=actor, campaign={"member_role": member_role}, user_id=user_id)


def _normalize_operation(raw: str) -> str | None:
    op = str(raw or "").strip().lower()
    aliases = {
        "dmg": "damage",
        "damage": "damage",
        "dam": "damage",
        "heal": "heal",
        "healing": "heal",
        "cura": "heal",
        "set": "set",
        "value": "set",
        "adjust": "adjust",
        "delta": "adjust",
    }
    return aliases.get(op)


def _actor_with_name(actor: dict, name: str) -> dict:
    out = dict(actor)
    out["name"] = name
    return out


def _get_path(data: dict, dotted: str) -> Any:
    cursor: Any = data
    for segment in [part for part in str(dotted or "").split(".") if part]:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(segment)
    return cursor


def _set_path(data: dict, dotted: str, value: Any) -> None:
    cursor = data
    segments = [part for part in str(dotted or "").split(".") if part]
    for segment in segments[:-1]:
        nxt = cursor.get(segment)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[segment] = nxt
        cursor = nxt
    if segments:
        cursor[segments[-1]] = value


def _coerce_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _resolve_max(data: dict, value_path: str, max_path: str) -> int | None:
    raw = _get_path(data, max_path) if max_path else None
    if raw is None and value_path.endswith(".value"):
        raw = _get_path(data, value_path[: -len(".value")] + ".max")
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    return None


def _clamp_value(value: int, *, floor: int, max_value: int | None) -> int:
    out = max(int(floor), int(value))
    if max_value is not None:
        out = min(out, int(max_value))
    return out
