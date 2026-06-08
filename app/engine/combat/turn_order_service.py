from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.roles import PlayerRole
from app.engine.actors.actor_asset_urls import actor_image_url, actor_token_image_url
from app.engine.combat.combat_config import CombatConfigService
from app.engine.effects.active_effects import (
    apply_resource_delta,
    periodic_modifiers,
    resolve_resource_target,
)
from app.engine.combat.strategies import CombatStrategyService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.tokens.actor_token_projector import ActorTokenProjector
from app.engine.tokens.token_view_service import TokenViewService
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.combat_encounter_repository import CombatEncounterRepository
from app.persistence.repositories.combat_state_repository import CombatStateRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.token_condition_repository import TokenConditionRepository
from app.persistence.repositories.token_repository import TokenRepository


@dataclass(frozen=True)
class CombatResult:
    success: bool
    campaign_id: str | None = None
    combat: dict | None = None
    participants: list[dict] = field(default_factory=list)
    config: dict = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    updated_actors: list[dict] = field(default_factory=list)
    expired_effects: list[dict] = field(default_factory=list)
    effect_ticks: list[dict] = field(default_factory=list)
    error_key: str | None = None

    @property
    def is_active(self) -> bool:
        return bool(self.combat and self.combat.get("status") in {"active", "paused"})

    @property
    def round_number(self) -> int:
        return int((self.combat or {}).get("round_number") or (self.combat or {}).get("round") or 0)

    def state_payload(self) -> dict:
        combat = self.combat or {}
        current = _current_participant(combat, self.participants)
        next_participant = _next_participant(combat, self.participants)
        turn_index = _current_turn_index(combat, self.participants) if combat else 0
        return {
            "campaign_id": self.campaign_id or combat.get("campaign_id", ""),
            "combat_id": combat.get("id", ""),
            "is_active": self.is_active,
            "status": combat.get("status", "inactive") if combat else "inactive",
            "mode": combat.get("mode", self.config.get("defaultMode", "manual")),
            "strategy": combat.get("strategy", self.config.get("turnOrder", {}).get("strategy", "manual")),
            "round": self.round_number,
            "turn_index": turn_index,
            "turn_position": turn_index + 1 if self.participants else 0,
            "turn_count": len(self.participants),
            "phase": combat.get("phase", "inactive") if combat else "inactive",
            "current": current,
            "current_participant_id": current.get("id", ""),
            "active_participant_id": current.get("id", ""),
            "active_actor_id": current.get("actor_id", ""),
            "active_token_id": current.get("token_id", ""),
            "next_participant_id": next_participant.get("id", ""),
            "next_actor_id": next_participant.get("actor_id", ""),
            "next_token_id": next_participant.get("token_id", ""),
            "participants": self.participants,
            "config": self.config,
            "events": self.events,
            "updated_actors": self.updated_actors,
            "expired_effects": self.expired_effects,
            "effect_ticks": self.effect_ticks,
        }


class TurnOrderService:
    """Combat Encounter System v1.

    The core stores encounters, participants, lifecycle phase and round/turn
    position. The active system defines how participant order is produced through
    ``rules/combat.gw.json``. Existing ``combat_states`` is kept only for
    backwards compatibility with older round-only tests/UI.
    """

    def __init__(self) -> None:
        self.campaigns = CampaignRepository()
        self.actors = ActorRepository()
        self.encounters = CombatEncounterRepository()
        self.tokens = TokenRepository()
        self.scenes = SceneRepository()
        self.conditions = TokenConditionRepository()
        self.legacy_states = CombatStateRepository()
        self.configs = CombatConfigService()
        self.strategies = CombatStrategyService()
        self.storage = ScopedJsonStorage()
        self.projector = ActorTokenProjector(storage=self.storage)
        self.token_views = TokenViewService()

    def get_state(self, *, campaign_id: str, user_id: str) -> CombatResult:
        campaign = self._campaign_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return CombatResult(success=False, error_key="game.combat.errors.not_found")
        config = self._config_for_campaign(campaign).payload()
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is None:
            legacy = self.legacy_states.get(campaign_id=campaign_id)
            if legacy and bool(legacy.get("is_active")):
                combat = self._bootstrap_from_legacy(campaign=campaign, user_id=user_id, config=config)
            else:
                return CombatResult(success=True, campaign_id=campaign_id, config=config)
        participants = self._visible_participants(combat=combat, user_id=user_id)
        return CombatResult(success=True, campaign_id=campaign_id, combat=combat, participants=participants, config=config)

    def start(
        self,
        *,
        campaign_id: str,
        user_id: str,
        scene_id: str | None = None,
        actor_ids: list[str] | None = None,
    ) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        campaign = self._campaign_for_user(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return CombatResult(success=False, error_key="game.combat.errors.not_found")
        config_obj = self._config_for_campaign(campaign)
        config = config_obj.payload()
        combat = self.encounters.create(
            campaign_id=campaign_id,
            scene_id=scene_id,
            mode=config_obj.default_mode,
            strategy=config_obj.strategy,
            settings=config,
            created_by_user_id=user_id,
        )
        self.encounters.add_event(
            combat_id=combat["id"], round_number=1, turn_index=0, participant_id=None,
            actor_id=None, event_type="combat.start", payload={"strategy": config_obj.strategy},
        )
        self.legacy_states.upsert(campaign_id=campaign_id, is_active=True, round_number=1)
        if actor_ids:
            self.add_participants(campaign_id=campaign_id, user_id=user_id, actor_ids=actor_ids)
            combat = self.encounters.get_active(campaign_id=campaign_id) or combat
        return self.get_state(campaign_id=campaign_id, user_id=user_id)

    def end(self, *, campaign_id: str, user_id: str) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is not None:
            self._record_phase_event(combat, "combat.end")
            combat = self.encounters.end(combat_id=combat["id"])
        self.legacy_states.end(campaign_id=campaign_id)
        campaign = self._campaign_for_user(campaign_id=campaign_id, user_id=user_id)
        config = self._config_for_campaign(campaign).payload() if campaign is not None else {}
        return CombatResult(success=True, campaign_id=campaign_id, combat=combat, config=config)

    def add_participants(
        self,
        *,
        campaign_id: str,
        user_id: str,
        actor_ids: list[str],
        token_ids: list[str] | None = None,
    ) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        state = self.get_state(campaign_id=campaign_id, user_id=user_id)
        if not state.success:
            return state
        combat = state.combat
        if combat is None or not state.is_active:
            start = self.start(campaign_id=campaign_id, user_id=user_id)
            if not start.success:
                return start
            combat = start.combat
        assert combat is not None
        existing = self.encounters.list_participants(combat_id=combat["id"])
        existing_token_ids = {str(p.get("token_id") or "") for p in existing if p.get("token_id")}
        existing_actor_ids = {str(p.get("actor_id") or "") for p in existing if not p.get("token_id")}
        for token_id in (token_ids or [])[:64]:
            if token_id in existing_token_ids:
                continue
            token = self.tokens.get_by_id(token_id)
            if token is None or not token.get("actor_id"):
                continue
            actor = self.actors.get(str(token.get("actor_id")))
            if actor is None or actor.get("campaign_id") != campaign_id or actor.get("status") != "active":
                continue
            self.encounters.add_participant(
                combat_id=combat["id"],
                actor_id=actor["id"],
                token_id=token_id,
                name=str((token.get("overrides") or {}).get("name") or token.get("name") or actor.get("name") or "Actor"),
                visible_to_players=not bool(token.get("hidden")),
                group_key="players" if actor.get("type") == "character" else "monsters",
                metadata={"actorType": actor.get("type"), "systemId": actor.get("system_id"), "tokenId": token_id},
            )
            existing_token_ids.add(token_id)
            existing_actor_ids.add(actor["id"])
        for actor_id in actor_ids[:64]:
            actor = self.actors.get(actor_id)
            if actor is None or actor.get("campaign_id") != campaign_id or actor.get("status") != "active":
                continue
            if actor_id in existing_actor_ids:
                continue
            self.encounters.add_participant(
                combat_id=combat["id"],
                actor_id=actor_id,
                token_id=None,
                name=str(actor.get("name") or "Actor"),
                visible_to_players=True,
                group_key="players" if actor.get("type") == "character" else "monsters",
                metadata={"actorType": actor.get("type"), "systemId": actor.get("system_id")},
            )
        self._record_phase_event(combat, "combat.participant.added", {"actor_ids": actor_ids, "token_ids": token_ids or []})
        return self.get_state(campaign_id=campaign_id, user_id=user_id)

    def remove_participant(self, *, campaign_id: str, user_id: str, participant_id: str) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is None:
            return CombatResult(success=False, error_key="game.combat.errors.inactive")
        before = self.encounters.list_participants(combat_id=combat["id"])
        removed_index = next((index for index, item in enumerate(before) if str(item.get("id") or "") == participant_id), None)
        self.encounters.remove_participant(combat_id=combat["id"], participant_id=participant_id)
        after = self.encounters.list_participants(combat_id=combat["id"])
        current_index = int(combat.get("turn_index") or 0)
        if removed_index is not None and removed_index < current_index:
            current_index -= 1
        max_index = max(0, len(after) - 1)
        next_index = min(max(0, current_index), max_index)
        if next_index != int(combat.get("turn_index") or 0):
            combat = self.encounters.update_state(combat_id=combat["id"], turn_index=next_index, phase="turn.start") or combat
        self._record_phase_event(combat, "combat.participant.removed", {"participant_id": participant_id})
        return self.get_state(campaign_id=campaign_id, user_id=user_id)

    def roll_initiative(self, *, campaign_id: str, user_id: str) -> CombatResult:
        return self._roll_initiative_scope(campaign_id=campaign_id, user_id=user_id, scope="all")

    def roll_monster_initiative(self, *, campaign_id: str, user_id: str) -> CombatResult:
        return self._roll_initiative_scope(campaign_id=campaign_id, user_id=user_id, scope="monsters")

    def _roll_initiative_scope(self, *, campaign_id: str, user_id: str, scope: str) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        state = self.get_state(campaign_id=campaign_id, user_id=user_id)
        if not state.success or state.combat is None:
            return CombatResult(success=False, error_key="game.combat.errors.inactive")
        participants = self.encounters.list_participants(combat_id=state.combat["id"])
        actors_by_id = {actor["id"]: actor for actor in self.actors.list_active_for_campaign(campaign_id=campaign_id)}
        if scope == "monsters":
            participants_to_roll = [
                participant
                for participant in participants
                if _is_monster_participant(participant, actors_by_id=actors_by_id)
            ]
        else:
            participants_to_roll = participants
        if not participants_to_roll:
            self._record_phase_event(
                state.combat,
                "combat.initiative.roll_skipped",
                {"scope": scope, "reason": "no_eligible_participants"},
            )
            return self.get_state(campaign_id=campaign_id, user_id=user_id)
        token_ids = [str(participant.get("token_id") or "") for participant in participants_to_roll if participant.get("token_id")]
        tokens_by_id = {token_id: token for token_id in token_ids if (token := self.tokens.get_by_id(token_id)) is not None}
        rolled = self.strategies.roll_order(
            combat_config=state.config,
            participants=participants_to_roll,
            actors_by_id=actors_by_id,
            tokens_by_id=tokens_by_id,
            campaign_id=campaign_id,
        )
        for item in rolled:
            self.encounters.update_participant_order(
                participant_id=item.participant_id,
                initiative_label=item.label,
                initiative_value=item.value,
                initiative_data={**item.data, "scope": scope},
                sort_key=item.sort_key,
            )
        self.encounters.update_state(combat_id=state.combat["id"], turn_index=0, phase="round.start")
        self._record_phase_event(
            state.combat,
            "combat.initiative.rolled",
            {
                "strategy": state.config.get("turnOrder", {}).get("strategy"),
                "scope": scope,
                "rolled_participant_count": len(participants_to_roll),
            },
        )
        return self.get_state(campaign_id=campaign_id, user_id=user_id)

    def roll_participant_initiative(self, *, campaign_id: str, user_id: str, participant_id: str) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        state = self.get_state(campaign_id=campaign_id, user_id=user_id)
        if not state.success or state.combat is None:
            return CombatResult(success=False, error_key="game.combat.errors.inactive")
        participants = self.encounters.list_participants(combat_id=state.combat["id"])
        participant = next((item for item in participants if str(item.get("id") or "") == participant_id), None)
        if participant is None:
            return CombatResult(success=False, error_key="game.combat.errors.participant_not_found")

        actor = self.actors.get(str(participant.get("actor_id") or "")) if participant.get("actor_id") else None
        if actor is None or actor.get("campaign_id") != campaign_id or actor.get("status") != "active":
            return CombatResult(success=False, error_key="game.combat.errors.participant_not_found")

        token = self.tokens.get_by_id(str(participant.get("token_id") or "")) if participant.get("token_id") else None
        if token is not None:
            scene = self.scenes.get_by_id(str(token.get("scene_id") or ""))
            scene_campaign_id = scene["campaign_id"] if scene is not None else None
            if scene is None or scene_campaign_id != campaign_id or token.get("actor_id") != actor["id"]:
                token = None

        rolled = self.strategies.roll_participant_initiative(
            combat_config=state.config,
            participant=participant,
            actor=actor,
            token=token,
            campaign_id=campaign_id,
        )
        if rolled is None:
            return CombatResult(success=False, error_key="game.combat.errors.initiative_unavailable")
        self.encounters.update_participant_order(
            participant_id=rolled.participant_id,
            initiative_label=rolled.label,
            initiative_value=rolled.value,
            initiative_data=rolled.data,
            sort_key=rolled.sort_key,
        )
        self._record_phase_event(
            state.combat,
            "combat.initiative.participant_rolled",
            {"participant_id": participant_id, "actor_id": actor["id"], "token_id": participant.get("token_id")},
        )
        return self.get_state(campaign_id=campaign_id, user_id=user_id)

    def next_turn(self, *, campaign_id: str, user_id: str) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        state = self.get_state(campaign_id=campaign_id, user_id=user_id)
        if state.combat is None or not state.is_active:
            return CombatResult(success=False, error_key="game.combat.errors.inactive")
        participants = self.encounters.list_participants(combat_id=state.combat["id"])
        if not participants:
            return state
        previous = _current_participant(state.combat, participants)
        self._record_phase_event(state.combat, "turn.end", {"participant_id": previous.get("id") if previous else None})
        next_index = int(state.combat.get("turn_index") or 0) + 1
        next_round = int(state.combat.get("round_number") or 1)
        if next_index >= len(participants):
            self._record_phase_event(state.combat, "round.end", {"round": next_round})
            next_index = 0
            next_round += 1
            self._record_phase_event(state.combat, "round.start", {"round": next_round})
        updated = self.encounters.update_state(combat_id=state.combat["id"], round_number=next_round, turn_index=next_index, phase="turn.start")
        self.legacy_states.upsert(campaign_id=campaign_id, is_active=True, round_number=next_round)
        ticks: list[dict] = []
        updated_actors: list[dict] = []
        if updated is not None:
            current = _current_participant(updated, participants)
                                                                                
            actor_update, ticks = self._tick_actor_periodics(
                campaign_id=campaign_id, actor_id=str(current.get("actor_id") or ""), resources_cache={}
            )
            if actor_update is not None:
                updated_actors.append(actor_update)
            self._record_phase_event(updated, "turn.start", {
                "participant_id": current.get("id") if current else None,
                "effect_ticks": ticks,
            })
        refreshed = self.get_state(campaign_id=campaign_id, user_id=user_id)
        return CombatResult(
            success=refreshed.success,
            campaign_id=refreshed.campaign_id,
            combat=refreshed.combat,
            participants=refreshed.participants,
            config=refreshed.config,
            events=refreshed.events,
            updated_actors=updated_actors,
            effect_ticks=ticks,
            error_key=refreshed.error_key,
        )

    def previous_turn(self, *, campaign_id: str, user_id: str) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        state = self.get_state(campaign_id=campaign_id, user_id=user_id)
        if state.combat is None or not state.is_active:
            return CombatResult(success=False, error_key="game.combat.errors.inactive")
        participants = self.encounters.list_participants(combat_id=state.combat["id"])
        if not participants:
            return state
        previous = _current_participant(state.combat, participants)
        current_index = _current_turn_index(state.combat, participants)
        next_round = int(state.combat.get("round_number") or 1)
        next_index = current_index - 1
        if next_index < 0:
            if next_round > 1:
                next_round -= 1
                next_index = len(participants) - 1
            else:
                next_index = 0
        updated = self.encounters.update_state(
            combat_id=state.combat["id"],
            round_number=next_round,
            turn_index=next_index,
            phase="turn.start",
        )
        self.legacy_states.upsert(campaign_id=campaign_id, is_active=True, round_number=next_round)
        current = _current_participant(updated or state.combat, participants)
        self._record_phase_event(
            updated or state.combat,
            "turn.rewind",
            {
                "from_participant_id": previous.get("id") if previous else None,
                "participant_id": current.get("id") if current else None,
            },
        )
        return self.get_state(campaign_id=campaign_id, user_id=user_id)

    def next_round(self, *, campaign_id: str, user_id: str) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        state = self.get_state(campaign_id=campaign_id, user_id=user_id)
        if state.combat is None or not state.is_active:
            start = self.start(campaign_id=campaign_id, user_id=user_id)
            return start
        self._record_phase_event(state.combat, "round.end", {"round": state.round_number})
        next_round = state.round_number + 1
                                                                           
                                                                            
                                                                         
        updated, expired = self._tick_round_effects(campaign_id=campaign_id)
        self.encounters.update_state(combat_id=state.combat["id"], round_number=next_round, turn_index=0, phase="round.start")
        self.legacy_states.upsert(campaign_id=campaign_id, is_active=True, round_number=next_round)
        self._record_phase_event(state.combat, "round.start", {"round": next_round, "expired_effects": expired})
        refreshed = self.get_state(campaign_id=campaign_id, user_id=user_id)
        return CombatResult(
            success=refreshed.success,
            campaign_id=refreshed.campaign_id,
            combat=refreshed.combat,
            participants=refreshed.participants,
            config=refreshed.config,
            events=refreshed.events,
            updated_actors=updated,
            expired_effects=expired,
            error_key=refreshed.error_key,
        )

    def set_turn(self, *, campaign_id: str, user_id: str, turn_index: int) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        state = self.get_state(campaign_id=campaign_id, user_id=user_id)
        if state.combat is None:
            return CombatResult(success=False, error_key="game.combat.errors.inactive")
        max_index = max(0, len(state.participants) - 1)
        self.encounters.update_state(combat_id=state.combat["id"], turn_index=max(0, min(max_index, int(turn_index))), phase="turn.start")
        return self.get_state(campaign_id=campaign_id, user_id=user_id)

    def record_actor_activity(self, *, campaign_id: str, actor_id: str, activity_type: str, payload: dict | None = None) -> None:
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is None:
            return
        participants = self.encounters.list_participants(combat_id=combat["id"])
        participant = next((p for p in participants if p.get("actor_id") == actor_id), None)
        self.encounters.add_event(
            combat_id=combat["id"],
            round_number=int(combat.get("round_number") or 1),
            turn_index=int(combat.get("turn_index") or 0),
            participant_id=participant.get("id") if participant else None,
            actor_id=actor_id,
            event_type="actor.activity",
            payload={"activity_type": activity_type, **(payload or {})},
        )

    def record_initiative_roll(
        self,
        *,
        campaign_id: str,
        actor_id: str,
        user_id: str,
        total: int | float,
        token_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is None:
            return
        participants = self.encounters.list_participants(combat_id=combat["id"])
        if token_id:
            matched = [p for p in participants if str(p.get("token_id") or "") == token_id]
        else:
            matched = [p for p in participants if str(p.get("actor_id") or "") == actor_id]
        try:
            value = float(total)
        except (TypeError, ValueError):
            return
        for participant in matched:
            self.encounters.update_participant_order(
                participant_id=participant["id"],
                initiative_label=str(int(value) if value.is_integer() else value),
                initiative_value=value,
                initiative_data={"kind": "sheet_roll", "total": value, **(metadata or {})},
                sort_key=value,
            )


    def _tick_round_effects(self, *, campaign_id: str) -> tuple[list[dict], list[dict]]:
        """Count down round-based effect durations for every actor (no damage)."""
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
                    expired.append({
                        "actor_id": actor["id"],
                        "effect_id": str(effect.get("id") or ""),
                        "name": str(effect.get("name") or ""),
                    })
            if changed:
                version = int(envelope.get("version", 1)) + 1
                self.storage.write_actor(
                    system_id=actor["system_id"], campaign_id=campaign_id, actor_id=actor["id"], version=version, data=data
                )
                updated.append({"actor_id": actor["id"], "system_id": actor["system_id"], "version": version})
        return updated, expired

    def _tick_actor_periodics(
        self, *, campaign_id: str, actor_id: str, resources_cache: dict[str, dict]
    ) -> tuple[dict | None, list[dict]]:
        """Roll and apply one actor's recurring damage/heal at the start of its turn.

        The resource path is driven by each modifier's target and the system's
        configured ``resources`` (see ``resolve_resource_target``), so this is not
        tied to a fixed hp field. Returns ``(updated_actor_entry | None, ticks)``.
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
        if system_id not in resources_cache:
            resources_cache[system_id] = self.configs.get_for_system(system_id).resources
        resources = resources_cache[system_id]
        ticks: list[dict] = []
        for entry in applied:
            resolved = resolve_resource_target(entry["target"], resources)
            if resolved is None:
                continue
            value_path, max_path, floor = resolved
            value_after = apply_resource_delta(data, value_path, max_path, floor, int(entry["delta"]))
            if value_after is None:
                continue
            ticks.append({
                "actor_id": actor_id,
                "actor_name": actor["name"],
                "effect_id": entry["effectId"],
                "name": entry["effectName"],
                "operation": entry["operation"],
                "amount": entry["amount"],
                "damage_type": entry["damageType"],
                "resource_path": value_path,
                "value_after": value_after,
            })
        if not ticks:
            return None, []
        version = int(envelope.get("version", 1)) + 1
        self.storage.write_actor(
            system_id=system_id, campaign_id=campaign_id, actor_id=actor_id, version=version, data=data
        )
        return {"actor_id": actor_id, "system_id": system_id, "version": version}, ticks

    def _campaign_for_user(self, *, campaign_id: str, user_id: str) -> dict | None:
        row = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        return dict(row) if row is not None else None

    def _config_for_campaign(self, campaign: dict | None):
        return self.configs.get_for_system(campaign.get("active_system_id") if campaign else None)

    def _can_manage(self, *, campaign_id: str, user_id: str) -> bool:
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        return role in {PlayerRole.GM.value, PlayerRole.ASSISTANT_GM.value}

    def _visible_participants(self, *, combat: dict, user_id: str) -> list[dict]:
        include_hidden = self._can_manage(campaign_id=str(combat.get("campaign_id")), user_id=user_id)
        participants = self.encounters.list_participants(combat_id=combat["id"], include_hidden=include_hidden)
        actor_ids = {str(participant.get("actor_id") or "") for participant in participants if participant.get("actor_id")}
        token_ids = {str(participant.get("token_id") or "") for participant in participants if participant.get("token_id")}
        actors_by_id = {actor_id: actor for actor_id in actor_ids if (actor := self.actors.get(actor_id)) is not None}
        tokens_by_id = {token_id: token for token_id in token_ids if (token := self.tokens.get_by_id(token_id)) is not None}
        conditions_by_token = self.conditions.list_by_tokens(list(token_ids))
        projections_by_actor: dict[str, dict] = {}

        current_index = _current_turn_index(combat, participants)
        next_index = (current_index + 1) % len(participants) if len(participants) > 1 else -1
        for index, participant in enumerate(participants):
            is_current = index == current_index
            is_next = index == next_index
            participant["turn_index"] = index
            participant["turn_position"] = index + 1
            participant["is_current"] = is_current
            participant["is_active_turn"] = is_current
            participant["is_next"] = is_next
            participant["has_acted"] = index < current_index
            participant["turn_status"] = "current" if is_current else ("acted" if index < current_index else "waiting")
            participant["resources"] = {}
            participant["conditions_count"] = 0
            participant["effects_count"] = 0
            hidden_from_player = not include_hidden and not participant.get("visible_to_players")
            actor = actors_by_id.get(str(participant.get("actor_id") or ""))
            token = tokens_by_id.get(str(participant.get("token_id") or ""))
            if hidden_from_player:
                participant["name"] = "???"
                participant["portrait_url"] = ""
                participant["token_asset_url"] = ""
                continue

            token_asset_url = ""
            if token is not None:
                overrides = token.get("overrides") if isinstance(token.get("overrides"), dict) else {}
                token_asset_url = str(token.get("token_asset_url") or overrides.get("token_asset_url") or "")

            projection = {}
            token_view = None
            if actor is not None:
                actor_id = str(actor.get("id") or "")
                if actor_id not in projections_by_actor:
                    projections_by_actor[actor_id] = self.projector.project(actor)
                projection = projections_by_actor[actor_id]
            if token is not None:
                token_conditions = conditions_by_token.get(str(token.get("id") or ""), [])
                token_view = self.token_views.build_view(
                    token=token,
                    projection=projection,
                    actor=actor,
                    conditions=token_conditions,
                )
                participant["resources"] = _participant_resources(token_view.get("bars"))
                participant["conditions_count"] = len(token_conditions)
                participant["effects_count"] = len(token_view.get("effects") or []) if isinstance(token_view.get("effects"), list) else 0
            else:
                participant["resources"] = _participant_resources(projection.get("bars") if isinstance(projection, dict) else {})
                participant["effects_count"] = len(projection.get("effects") or []) if isinstance(projection.get("effects"), list) else 0

            actor_token_url = actor_token_image_url(actor) if actor is not None else None
            actor_portrait_url = actor_image_url(actor, "portrait") if actor is not None else None
            participant["portrait_url"] = token_asset_url or actor_token_url or actor_portrait_url or ""
            participant["token_asset_url"] = token_asset_url or actor_token_url or ""
        return participants

    def _record_phase_event(self, combat: dict, event_type: str, payload: dict | None = None) -> None:
        self.encounters.add_event(
            combat_id=combat["id"],
            round_number=int(combat.get("round_number") or 1),
            turn_index=int(combat.get("turn_index") or 0),
            participant_id=None,
            actor_id=None,
            event_type=event_type,
            payload=payload or {},
        )

    def _bootstrap_from_legacy(self, *, campaign: dict, user_id: str, config: dict) -> dict:
        combat = self.encounters.create(
            campaign_id=campaign["id"], scene_id=None, mode=config.get("defaultMode", "manual"),
            strategy=config.get("turnOrder", {}).get("strategy", "manual"), settings=config, created_by_user_id=user_id,
        )
        legacy = self.legacy_states.get(campaign_id=campaign["id"]) or {}
        self.encounters.update_state(combat_id=combat["id"], round_number=int(legacy.get("round_number") or 1), phase="round.start")
        return self.encounters.get(combat_id=combat["id"]) or combat



def _participant_resources(bars: Any) -> dict:
    if not isinstance(bars, dict):
        return {}
    out: dict[str, dict] = {}
    for key, raw in bars.items():
        if not isinstance(raw, dict):
            continue
        value = raw.get("value")
        if value is None:
            continue
        max_value = raw.get("max", value)
        try:
            numeric_value = int(value)
        except (TypeError, ValueError):
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                continue
        try:
            numeric_max = int(max_value)
        except (TypeError, ValueError):
            try:
                numeric_max = float(max_value)
            except (TypeError, ValueError):
                numeric_max = numeric_value
        percent = None
        if numeric_max and numeric_max > 0:
            percent = max(0, min(100, int(round((numeric_value / numeric_max) * 100))))
        out[str(key)] = {
            "value": numeric_value,
            "max": numeric_max,
            "percent": percent,
            "visibility": raw.get("visibility", "everyone"),
        }
    return out


def _is_monster_participant(participant: dict, *, actors_by_id: dict[str, dict]) -> bool:
    metadata = participant.get("metadata") if isinstance(participant.get("metadata"), dict) else {}
    raw_type = str(metadata.get("actorType") or "").strip().lower()
    actor = actors_by_id.get(str(participant.get("actor_id") or ""))
    if not raw_type and actor is not None:
        raw_type = str(actor.get("type") or "").strip().lower()
    if raw_type in {"character", "pc", "player", "player_character"}:
        return False
    if raw_type in {"monster", "npc", "creature", "enemy", "vehicle", "hazard"}:
        return True
    group_key = str(participant.get("group_key") or metadata.get("side") or "").strip().lower()
    return group_key in {"monsters", "monster", "npcs", "npc", "gm", "enemies", "enemy"}


def _current_turn_index(combat: dict, participants: list[dict]) -> int:
    if not participants:
        return 0
    return max(0, min(len(participants) - 1, int(combat.get("turn_index") or 0)))


def _current_participant(combat: dict, participants: list[dict]) -> dict:
    if not participants:
        return {}
    return participants[_current_turn_index(combat, participants)]


def _next_participant(combat: dict, participants: list[dict]) -> dict:
    if len(participants) <= 1:
        return {}
    current_index = _current_turn_index(combat, participants)
    return participants[(current_index + 1) % len(participants)]


def _tick_effect(effect: dict[str, Any]) -> tuple[bool, bool]:
    duration = effect.get("duration") if isinstance(effect.get("duration"), dict) else None
    data = effect.get("data") if isinstance(effect.get("data"), dict) else {}
    if duration is None:
        duration = data.get("duration") if isinstance(data.get("duration"), dict) else None
    if not isinstance(duration, dict) or duration.get("type") != "rounds":
        return False, False

    raw_remaining = duration.get("remaining", duration.get("value"))
    try:
        remaining = int(raw_remaining)
    except (TypeError, ValueError):
        return False, False
    next_remaining = max(0, remaining - 1)
    duration["remaining"] = next_remaining
    effect["duration"] = duration
    if isinstance(data, dict):
        data_duration = data.get("duration") if isinstance(data.get("duration"), dict) else None
        if data_duration is not None:
            data_duration["remaining"] = next_remaining
    expired = next_remaining <= 0
    if expired:
        effect["enabled"] = False
    return True, expired
