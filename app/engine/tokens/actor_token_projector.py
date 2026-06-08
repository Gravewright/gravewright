"""Projects an Actor Core record into a manifest-defined TokenView (§12).

    Actor Core + Sheet Data + derived fields + token mappings  ->  TokenView

This is the single source of truth used both when scene tokens are created from
actors and when an actor's sheet data changes and linked tokens must be
recomputed live. The shape mirrors what :mod:`sheet_action_service` returns for
``sheet.data.updated`` so the on-canvas token and the open sheet stay in sync.
"""

from __future__ import annotations

from app.engine.actors.actor_asset_urls import actor_token_image_url
from app.engine.rules.derived_field_service import apply_derived
from app.engine.effects.active_effects import apply_stat_modifiers
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.rules.token_mapping_resolver import resolve_token_view
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage


class ActorTokenProjector:
    def __init__(
        self,
        *,
        storage: ScopedJsonStorage | None = None,
        rules: SystemRulesService | None = None,
    ) -> None:
        self.storage = storage or ScopedJsonStorage()
        self.rules = rules or SystemRulesService()

    def project(self, actor: dict, *, envelope: dict | None = None) -> dict:
        """Resolve the actor's mapped TokenView (``{name, bars, ...}``)."""
        mappings = self.rules.get_token_mappings(actor["system_id"])
        if not mappings:
            return {}
        if envelope is None:
            envelope = self.storage.read_actor(
                system_id=actor["system_id"],
                campaign_id=actor["campaign_id"],
                actor_id=actor["id"],
            ) or {"data": {}}
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        helpers = self.rules.get_helpers(actor["system_id"])
        derived = self.rules.get_derived(actor["system_id"])
        core = {"name": actor["name"]}
        derived_data = apply_derived(
            actor_type=actor["type"],
            data=data,
            derived_rules=derived,
            helpers=helpers,
            core=core,
        )
        effective_data = apply_stat_modifiers(derived_data)
        view = resolve_token_view(
            actor_type=actor["type"],
            sheet_data=effective_data,
            core=core,
            token_mappings=mappings,
        )
        token_asset_url = actor_token_image_url(actor)
        if token_asset_url:
            view["token_asset_url"] = token_asset_url
        view["effects"] = _compact_buff_debuff(data)
        return view


def _compact_buff_debuff(data: dict) -> list[dict]:
    """Enabled buff/debuff effects, trimmed to what the board HUD needs."""
    raw = data.get("effects") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for effect in raw:
        if not isinstance(effect, dict) or effect.get("enabled") is False:
            continue
        payload = effect.get("data") if isinstance(effect.get("data"), dict) else {}
        category = str(payload.get("category") or "").lower()
        if "buff" not in category and "debuff" not in category and "condition" not in category:
            continue
        duration = effect.get("duration") if isinstance(effect.get("duration"), dict) else payload.get("duration")
        out.append(
            {
                "id": effect.get("id") or "",
                "name": effect.get("name") or "Efeito",
                "img": effect.get("img") or "",
                "category": category,
                "description": payload.get("description") or effect.get("description") or "",
                "duration": duration if isinstance(duration, dict) else {},
                "concentration": bool(payload.get("concentration") or effect.get("concentration")),
                "modifiers": payload.get("modifiers") if isinstance(payload.get("modifiers"), list) else [],
            }
        )
    return out
