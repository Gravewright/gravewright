from __future__ import annotations

from typing import Any

from app.engine.combat.combat_config import CombatConfigService
from app.engine.effects.active_effects import (
    apply_resource_delta,
    periodic_modifiers,
    resolve_resource_target,
)
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.persistence.repositories.actor_repository import ActorRepository


class RoundEffectService:
    """The two things the clock does to active effects.

    On a new round every round-based duration counts down and expires. On a
    combatant's turn its recurring damage/heal (poison, regeneration) is applied
    to whichever resource the effect targets.
    """

    def __init__(self) -> None:
        self.actors = ActorRepository()
        self.storage = ScopedJsonStorage()
        self.configs = CombatConfigService()

    def tick_round(self, *, campaign_id: str) -> tuple[list[dict], list[dict]]:
        """Count down round durations for every actor. Returns ``(updated, expired)``."""
        updated: list[dict] = []
        expired: list[dict] = []
        for actor in self.actors.list_active_for_campaign(campaign_id=campaign_id):
            envelope = self.storage.read_actor(
                system_id=actor["system_id"], campaign_id=campaign_id, actor_id=actor["id"]
            ) or {"version": 1, "data": {}}
            data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
            effects = data.get("effects")
            if not isinstance(effects, list):
                continue
            changed = False
            for effect in effects:
                if not isinstance(effect, dict):
                    continue
                did_change, did_expire = _tick_effect(effect)
                changed = changed or did_change
                if did_expire:
                    expired.append(
                        {
                            "actor_id": actor["id"],
                            "effect_id": str(effect.get("id") or ""),
                            "name": str(effect.get("name") or ""),
                        }
                    )
            if changed:
                version = int(envelope.get("version", 1)) + 1
                self.storage.write_actor(
                    system_id=actor["system_id"],
                    campaign_id=campaign_id,
                    actor_id=actor["id"],
                    version=version,
                    data=data,
                )
                updated.append(
                    {"actor_id": actor["id"], "system_id": actor["system_id"], "version": version}
                )
        return updated, expired

    def tick_turn(self, *, campaign_id: str, actor_id: str) -> tuple[dict | None, list[dict]]:
        """Apply one actor's recurring damage/heal. Returns ``(updated, ticks)``.

        The resource path comes from each modifier's target resolved against the
        system's ``resources`` config, so this is never hard-wired to an hp field.
        """
        if not actor_id:
            return None, []
        actor = self.actors.get(actor_id)
        if actor is None or actor["status"] != "active" or actor["campaign_id"] != campaign_id:
            return None, []
        system_id = actor["system_id"]
        envelope = self.storage.read_actor(
            system_id=system_id, campaign_id=campaign_id, actor_id=actor_id
        ) or {"version": 1, "data": {}}
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        applied = periodic_modifiers(data)
        if not applied:
            return None, []
        resources = self.configs.get_for_system(system_id).resources
        ticks: list[dict] = []
        for entry in applied:
            resolved = resolve_resource_target(entry["target"], resources)
            if resolved is None:
                continue
            value_path, max_path, floor = resolved
            value_after = apply_resource_delta(
                data, value_path, max_path, floor, int(entry["delta"])
            )
            if value_after is None:
                continue
            ticks.append(
                {
                    "actor_id": actor_id,
                    "actor_name": actor["name"],
                    "effect_id": entry["effectId"],
                    "name": entry["effectName"],
                    "operation": entry["operation"],
                    "amount": entry["amount"],
                    "damage_type": entry["damageType"],
                    "resource_path": value_path,
                    "value_after": value_after,
                }
            )
        if not ticks:
            return None, []
        version = int(envelope.get("version", 1)) + 1
        self.storage.write_actor(
            system_id=system_id,
            campaign_id=campaign_id,
            actor_id=actor_id,
            version=version,
            data=data,
        )
        return {"actor_id": actor_id, "system_id": system_id, "version": version}, ticks


def _tick_effect(effect: dict[str, Any]) -> tuple[bool, bool]:
    duration = effect.get("duration") if isinstance(effect.get("duration"), dict) else None
    data = effect.get("data") if isinstance(effect.get("data"), dict) else {}
    if duration is None:
        duration = data.get("duration") if isinstance(data.get("duration"), dict) else None
    if not isinstance(duration, dict) or duration.get("type") != "rounds":
        return False, False

    try:
        remaining = int(duration.get("remaining", duration.get("value")))
    except (TypeError, ValueError):
        return False, False
    next_remaining = max(0, remaining - 1)
    duration["remaining"] = next_remaining
    effect["duration"] = duration
    data_duration = data.get("duration") if isinstance(data.get("duration"), dict) else None
    if data_duration is not None:
        data_duration["remaining"] = next_remaining
    if next_remaining <= 0:
        effect["enabled"] = False
        return True, True
    return True, False
