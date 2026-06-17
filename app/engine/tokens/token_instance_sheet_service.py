from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from app.domain.roles import PlayerRole
from app.engine.actors.actor_asset_urls import actor_image_url
from app.engine.actors.actor_permissions import can_edit_actor, can_view_actor
from app.engine.effects.active_effects import apply_stat_modifiers
from app.engine.rules.derived_field_service import apply_derived
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.sheets.actor_sheet_service import ActorSheetBundle
from app.engine.sheets.schema_service import SchemaService
from app.engine.sheets.sheet_validation import sanitize_write
from app.engine.sheets.system_layout_service import SystemLayoutService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.sdk.package_install_service import PackageInstallService
from app.engine.tokens.actor_token_projector import ActorTokenProjector
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.token_repository import TokenRepository


INSTANCE_KEY = "_actor_instance"


@dataclass(frozen=True)
class TokenSheetDataResult:
    success: bool
    token_id: str | None = None
    actor_id: str | None = None
    campaign_id: str | None = None
    scene_id: str | None = None
    system_id: str | None = None
    version: int | None = None
    overrides: dict | None = None
    changed_paths: list[str] = field(default_factory=list)
    error_key: str | None = None


def set_path(data: dict, dotted_path: str, value: Any) -> None:
    segments = [segment for segment in dotted_path.split(".") if segment]
    if not segments:
        return
    cursor = data
    for segment in segments[:-1]:
        nxt = cursor.get(segment)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[segment] = nxt
        cursor = nxt
    cursor[segments[-1]] = value


class TokenInstanceSheetService:
    def __init__(self) -> None:
        self.tokens = TokenRepository()
        self.actors = ActorRepository()
        self.scenes = SceneRepository()
        self.campaigns = CampaignRepository()
        self.storage = ScopedJsonStorage()
        self.systems = PackageInstallService()
        self.layouts = SystemLayoutService()
        self.rules = SystemRulesService()
        self.schemas = SchemaService()
        self.projector = ActorTokenProjector()

    def build_bundle(self, *, token_id: str, user_id: str, locale: str | None = None) -> ActorSheetBundle | None:
        loaded = self._load(token_id=token_id, user_id=user_id, require_edit=False)
        if loaded is None:
            return None
        token, actor, campaign = loaded
        instance = self._ensure_instance(token=token, actor=actor)
        raw_data = deepcopy(instance.get("data") if isinstance(instance.get("data"), dict) else {})

        system_id = actor["system_id"]
        layout: dict | None = None
        sheet: dict | None = None
        data = raw_data
        if self.systems.get_active_manifest(system_id) is not None:
            sheet = self.layouts.get_actor_html_sheet(
                system_id=system_id, actor_type=actor["type"]
            )
            if sheet is None:
                candidate = self.layouts.get_actor_sheet(
                    system_id=system_id,
                    actor_type=actor["type"],
                    locale=locale,
                )
                if candidate is not None:
                    layout = candidate
            helpers = self.rules.get_helpers(system_id)
            data = apply_derived(
                actor_type=actor["type"],
                data=raw_data,
                derived_rules=self.rules.get_derived(system_id),
                helpers=helpers,
                core={"name": instance.get("name") or token.get("name") or actor["name"]},
            )
            data = apply_stat_modifiers(data)

        return ActorSheetBundle(
            actor_id=actor["id"],
            campaign_id=actor["campaign_id"],
            system_id=system_id,
            name=instance.get("name") or token.get("name") or actor["name"],
            type=actor["type"],
            version=int(instance.get("version", 1)),
            can_edit=self._can_control_token(token=token, campaign=campaign, user_id=user_id),
            layout=layout,
            sheet=sheet,
            data=data,
            portrait_url=actor_image_url(actor, "portrait"),
            token_url=token.get("token_asset_url") or actor_image_url(actor, "token"),
            summary=self._project_instance(actor=actor, name=instance.get("name") or actor["name"], data=raw_data),
            token_id=token["id"],
            source_actor_id=actor["id"],
            token_link_mode=token.get("actor_link_mode"),
        )

    def patch_data(self, *, token_id: str, user_id: str, patch: dict[str, Any]) -> TokenSheetDataResult:
        loaded = self._load(token_id=token_id, user_id=user_id, require_edit=True)
        if loaded is None:
            return TokenSheetDataResult(success=False, error_key="tokens.errors.not_found")
        token, actor, _campaign = loaded
        if not isinstance(patch, dict) or not patch:
            return TokenSheetDataResult(success=False, error_key="game.sheet_data.errors.empty_patch")

        core_name = patch.get("core.name")
        sheet_patch = {key: value for key, value in patch.items() if key != "core.name"}
        clean, _rejected = sanitize_write(
            self.schemas.get_actor_schema(system_id=actor["system_id"], actor_type=actor["type"]),
            self.rules.get_validation(actor["system_id"], actor["type"]),
            sheet_patch,
        )
        has_core_name = core_name is not None
        if not clean and not has_core_name:
            return TokenSheetDataResult(success=False, error_key="game.sheet_data.errors.empty_patch")

        overrides = deepcopy(token.get("overrides") or {})
        instance = deepcopy(overrides.get(INSTANCE_KEY) or self._ensure_instance(token=token, actor=actor))
        data = instance.get("data") if isinstance(instance.get("data"), dict) else {}
        if has_core_name:
            instance["name"] = str(core_name)
            overrides["name"] = str(core_name)
        for path, value in clean.items():
            set_path(data, str(path), value)
        instance["data"] = data
        instance["version"] = int(instance.get("version", 1)) + 1
        overrides[INSTANCE_KEY] = instance
        overrides.update(self._project_instance(actor=actor, name=instance.get("name") or actor["name"], data=data).get("bars") or {})
        effects = self._project_instance(actor=actor, name=instance.get("name") or actor["name"], data=data).get("effects")
        if isinstance(effects, list):
            overrides["effects"] = effects

        updated = self.tokens.update_overrides(token_id=token_id, overrides=overrides)
        return TokenSheetDataResult(
            success=True,
            token_id=token_id,
            actor_id=actor["id"],
            campaign_id=actor["campaign_id"],
            scene_id=token["scene_id"],
            system_id=actor["system_id"],
            version=updated["version"] if updated else token["version"],
            overrides=overrides,
            changed_paths=sorted([*clean.keys(), *(["core.name"] if has_core_name else [])]),
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
            },
            "version": bundle.version,
            "can_edit": bundle.can_edit,
            "layout": bundle.layout,
            "sheet": bundle.sheet,
            "data": bundle.data,
            "portrait_url": bundle.portrait_url,
            "token_url": bundle.token_url,
            "summary": bundle.summary,
        }

    def make_instance_snapshot(self, *, actor: dict) -> dict:
        envelope = self.storage.read_actor(
            system_id=actor["system_id"],
            campaign_id=actor["campaign_id"],
            actor_id=actor["id"],
        ) or {"version": 1, "data": {}}
        return {
            "source_actor_id": actor["id"],
            "name": actor["name"],
            "type": actor["type"],
            "system_id": actor["system_id"],
            "version": int(envelope.get("version", 1)),
            "data": deepcopy(envelope.get("data") if isinstance(envelope.get("data"), dict) else {}),
        }

    def _ensure_instance(self, *, token: dict, actor: dict) -> dict:
        overrides = token.get("overrides") or {}
        instance = overrides.get(INSTANCE_KEY)
        if isinstance(instance, dict):
            return instance
        return self.make_instance_snapshot(actor=actor)

    def _project_instance(self, *, actor: dict, name: str, data: dict) -> dict:
        pseudo_actor = dict(actor)
        pseudo_actor["name"] = name
        envelope = {"version": 1, "data": deepcopy(data)}
        return self.projector.project(pseudo_actor, envelope=envelope)

    def _load(self, *, token_id: str, user_id: str, require_edit: bool) -> tuple[dict, dict, dict] | None:
        token = self.tokens.get_by_id(token_id)
        if token is None or not token.get("actor_id"):
            return None
        scene = self.scenes.get_by_id(token["scene_id"])
        if scene is None:
            return None
        actor = self.actors.get(token["actor_id"])
        if actor is None or actor["status"] != "active" or actor["campaign_id"] != scene["campaign_id"]:
            return None
        campaign = self.campaigns.get_for_user(campaign_id=scene["campaign_id"], user_id=user_id)
        if campaign is None:
            return None
        if token.get("hidden") and campaign["member_role"] != PlayerRole.GM.value:
            return None
        if require_edit:
            if not self._can_control_token(token=token, campaign=dict(campaign), user_id=user_id):
                return None
        elif not can_view_actor(actor=actor, campaign=dict(campaign), user_id=user_id) and campaign["member_role"] != PlayerRole.GM.value:
            return None
        return token, actor, dict(campaign)

    def _can_control_token(self, *, token: dict, campaign: dict, user_id: str) -> bool:
        if campaign["member_role"] == PlayerRole.GM.value:
            return True
        actor_id = token.get("actor_id")
        if not actor_id:
            return False
        actor = self.actors.get(actor_id)
        return bool(actor and can_edit_actor(actor=actor, campaign=campaign, user_id=user_id))
