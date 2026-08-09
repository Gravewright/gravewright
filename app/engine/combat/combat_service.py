from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from app.domain.roles import PlayerRole
from app.engine.actors.actor_asset_urls import actor_image_url, actor_token_image_url
from app.engine.combat.combat_config import CombatConfig, CombatConfigService
from app.engine.combat.initiative import InitiativeRoller
from app.engine.combat.round_effects import RoundEffectService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.tokens.actor_token_projector import ActorTokenProjector
from app.engine.tokens.token_view_service import TokenViewService
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.combat_encounter_repository import CombatEncounterRepository
from app.persistence.repositories.token_condition_repository import TokenConditionRepository
from app.persistence.repositories.token_repository import TokenRepository

MAX_COMBATANTS = 64
MAX_INITIATIVE_LENGTH = 24
NPC_TYPES = {"monster", "npc", "creature", "enemy", "vehicle", "hazard"}


@dataclass(frozen=True)
class CombatResult:
    """What every mutation returns: the whole state, plus what changed elsewhere."""

    success: bool
    campaign_id: str | None = None
    combat: dict | None = None
    combatants: list[dict] = field(default_factory=list)
    config: dict = field(default_factory=dict)
    updated_actors: list[dict] = field(default_factory=list)
    expired_effects: list[dict] = field(default_factory=list)
    effect_ticks: list[dict] = field(default_factory=list)
    error_key: str | None = None

    @property
    def active(self) -> bool:
        return bool(self.combat and self.combat.get("status") == "active")

    def state_payload(self) -> dict:
        combat = self.combat or {}
        current = next((c for c in self.combatants if c["is_current"]), {})
        upcoming = next((c for c in self.combatants if c["is_next"]), {})
        return {
            "campaign_id": self.campaign_id or combat.get("campaign_id", ""),
            "combat_id": combat.get("id", ""),
            "active": self.active,
            "round": int(combat.get("round_number") or 0),
            "turn": int(combat.get("turn_index") or 0),
            "combatants": self.combatants,
            "current_id": current.get("id", ""),
            "current_name": current.get("name", ""),
            "next_id": upcoming.get("id", ""),
            "next_name": upcoming.get("name", ""),
            "config": self.config,
            "updated_actors": self.updated_actors,
            "expired_effects": self.expired_effects,
            "effect_ticks": self.effect_ticks,
        }


class CombatService:
    """The combat tracker.

    An encounter is a round number, a position in the order, and a list of
    combatants. Each combatant holds one initiative value, stored as text the
    core never interprets — the active system decides whether that value is a
    rolled number, a typed number, or a word like "ambush".

    Ordering follows from what the system declared. Numeric systems sort by the
    value; systems that use anything else keep the order the GM arranged by
    hand. Either way the order is derived on read, so nothing goes stale.

    Every mutation is GM-only and returns the full state, which is what gets
    broadcast to the table.
    """

    def __init__(self) -> None:
        self.campaigns = CampaignRepository()
        self.actors = ActorRepository()
        self.tokens = TokenRepository()
        self.conditions = TokenConditionRepository()
        self.encounters = CombatEncounterRepository()
        self.configs = CombatConfigService()
        self.roller = InitiativeRoller()
        self.effects = RoundEffectService()
        self.projector = ActorTokenProjector(storage=ScopedJsonStorage())
        self.token_views = TokenViewService()



    def get_state(self, *, campaign_id: str, user_id: str) -> CombatResult:
        campaign = self._campaign(campaign_id=campaign_id, user_id=user_id)
        if campaign is None:
            return CombatResult(success=False, error_key="game.combat.errors.not_found")
        config = self.configs.get_for_system(campaign.get("active_system_id"))
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is None:
            return CombatResult(
                success=True, campaign_id=campaign_id, config=config.payload()
            )
        return CombatResult(
            success=True,
            campaign_id=campaign_id,
            combat=combat,
            combatants=self._build_combatants(combat=combat, user_id=user_id, config=config),
            config=config.payload(),
        )



    def start(
        self,
        *,
        campaign_id: str,
        user_id: str,
        scene_id: str | None = None,
        actor_ids: list[str] | None = None,
        token_ids: list[str] | None = None,
    ) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        if self._campaign(campaign_id=campaign_id, user_id=user_id) is None:
            return CombatResult(success=False, error_key="game.combat.errors.not_found")
        self.encounters.create(
            campaign_id=campaign_id, scene_id=scene_id, created_by_user_id=user_id
        )
        if actor_ids or token_ids:
            return self.add_combatants(
                campaign_id=campaign_id,
                user_id=user_id,
                actor_ids=actor_ids or [],
                token_ids=token_ids or [],
            )
        return self.get_state(campaign_id=campaign_id, user_id=user_id)

    def end(self, *, campaign_id: str, user_id: str) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is not None:
            self.encounters.end(combat_id=combat["id"])
        return self.get_state(campaign_id=campaign_id, user_id=user_id)



    def add_combatants(
        self,
        *,
        campaign_id: str,
        user_id: str,
        actor_ids: list[str],
        token_ids: list[str] | None = None,
    ) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is None:
            started = self.start(campaign_id=campaign_id, user_id=user_id)
            if not started.success:
                return started
            combat = started.combat
        assert combat is not None

        existing = self.encounters.list_combatants(combat_id=combat["id"])
        seen_tokens = {str(c["token_id"]) for c in existing if c.get("token_id")}


        seen_actors = {str(c["actor_id"]) for c in existing if not c.get("token_id")}

        for token_id in (token_ids or [])[:MAX_COMBATANTS]:
            if token_id in seen_tokens:
                continue
            token = self.tokens.get_by_id(token_id)
            if token is None or not token.get("actor_id"):
                continue
            actor = self._campaign_actor(str(token["actor_id"]), campaign_id=campaign_id)
            if actor is None:
                continue
            overrides = token.get("overrides") if isinstance(token.get("overrides"), dict) else {}
            self.encounters.add_combatant(
                combat_id=combat["id"],
                actor_id=actor["id"],
                token_id=token_id,
                name=str(overrides.get("name") or token.get("name") or actor["name"] or "?"),
                hidden=bool(token.get("hidden")),
            )
            seen_tokens.add(token_id)
            seen_actors.add(actor["id"])

        for actor_id in actor_ids[:MAX_COMBATANTS]:
            if actor_id in seen_actors:
                continue
            actor = self._campaign_actor(actor_id, campaign_id=campaign_id)
            if actor is None:
                continue
            self.encounters.add_combatant(
                combat_id=combat["id"],
                actor_id=actor_id,
                token_id=None,
                name=str(actor.get("name") or "?"),
            )
            seen_actors.add(actor_id)

        return self._preserving_turn(combat, campaign_id=campaign_id, user_id=user_id)

    def remove_combatant(
        self, *, campaign_id: str, user_id: str, combatant_id: str
    ) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is None:
            return CombatResult(success=False, error_key="game.combat.errors.inactive")
        current_id = self._combatant_id_at_turn(
            combat, self._config_for(campaign_id=campaign_id, user_id=user_id)
        )
        self.encounters.remove_combatant(combat_id=combat["id"], combatant_id=combatant_id)


        keep = "" if current_id == combatant_id else current_id
        return self._preserving_turn(combat, campaign_id=campaign_id, user_id=user_id, keep=keep)

    def set_flags(
        self,
        *,
        campaign_id: str,
        user_id: str,
        combatant_id: str,
        hidden: bool | None = None,
        defeated: bool | None = None,
    ) -> CombatResult:
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is None:
            return CombatResult(success=False, error_key="game.combat.errors.inactive")
        if not self._find(combat, combatant_id):
            return CombatResult(success=False, error_key="game.combat.errors.combatant_not_found")
        self.encounters.set_flags(combatant_id=combatant_id, hidden=hidden, defeated=defeated)
        return self.get_state(campaign_id=campaign_id, user_id=user_id)



    def roll_initiative(
        self, *, campaign_id: str, user_id: str, scope: str = "all", combatant_id: str = ""
    ) -> CombatResult:
        """Roll for ``all`` combatants, only the ``npc`` ones, only those
        ``missing`` a value, or a single one via ``combatant_id``.

        Only systems that declared ``input: "roll"`` have anything to roll.
        """
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        campaign = self._campaign(campaign_id=campaign_id, user_id=user_id)
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if campaign is None or combat is None:
            return CombatResult(success=False, error_key="game.combat.errors.inactive")
        config = self.configs.get_for_system(campaign.get("active_system_id"))
        if config.input != "roll":
            return CombatResult(success=False, error_key="game.combat.errors.roll_unavailable")

        combatants = self.encounters.list_combatants(combat_id=combat["id"])
        if combatant_id:
            combatants = [c for c in combatants if c["id"] == combatant_id]
            if not combatants:
                return CombatResult(
                    success=False, error_key="game.combat.errors.combatant_not_found"
                )
        elif scope == "npc":
            combatants = [c for c in combatants if self._is_npc(c, campaign_id=campaign_id)]
        elif scope == "missing":
            combatants = [c for c in combatants if c["initiative"] is None]

        for combatant in combatants:
            actor = self._campaign_actor(
                str(combatant.get("actor_id") or ""), campaign_id=campaign_id
            )
            token = (
                self.tokens.get_by_id(str(combatant["token_id"]))
                if combatant.get("token_id")
                else None
            )
            rolled = self.roller.roll(
                combat_config=config, actor=actor, token=token, campaign_id=campaign_id
            )
            if rolled is None:
                continue
            total, tie_break = rolled
            self.encounters.set_initiative(
                combatant_id=combatant["id"],
                initiative=_format_number(total),
                sort_value=total,
                tie_break=tie_break,
            )


        if not combatant_id:
            self.encounters.set_position(
                combat_id=combat["id"], round_number=int(combat["round_number"]), turn_index=0
            )
        return self.get_state(campaign_id=campaign_id, user_id=user_id)

    def set_initiative(
        self, *, campaign_id: str, user_id: str, combatant_id: str, value: str | None
    ) -> CombatResult:
        """Write the value the GM typed, interpreted the way the system asked.

        A numeric system parses it and reorders. Any other system stores the text
        as-is and leaves the order alone, because there the order is the GM's.
        """
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is None:
            return CombatResult(success=False, error_key="game.combat.errors.inactive")
        if not self._find(combat, combatant_id):
            return CombatResult(success=False, error_key="game.combat.errors.combatant_not_found")

        config = self._config_for(campaign_id=campaign_id, user_id=user_id)
        text = str(value).strip()[:MAX_INITIATIVE_LENGTH] if value is not None else ""
        if not config.is_numeric:
            self.encounters.set_label(combatant_id=combatant_id, initiative=text or None)
            return self.get_state(campaign_id=campaign_id, user_id=user_id)

        current_id = self._combatant_id_at_turn(combat, config)
        number = _parse_number(text)
        self.encounters.set_initiative(
            combatant_id=combatant_id,
            initiative=None if number is None else _format_number(number),
            sort_value=number,
            tie_break=0,
        )
        return self._preserving_turn(
            combat, campaign_id=campaign_id, user_id=user_id, keep=current_id
        )

    def move_combatant(
        self, *, campaign_id: str, user_id: str, combatant_id: str, delta: int
    ) -> CombatResult:
        """Slide a combatant one place up or down a hand-arranged order.

        Systems that sort by a number have no use for this: their order comes
        from the values, so moving a row would immediately be undone.
        """
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is None:
            return CombatResult(success=False, error_key="game.combat.errors.inactive")
        config = self._config_for(campaign_id=campaign_id, user_id=user_id)
        if not config.is_manual_order:
            return CombatResult(success=False, error_key="game.combat.errors.order_is_automatic")

        order = self._ordered(combat=combat, config=config)
        index = next((i for i, c in enumerate(order) if c["id"] == combatant_id), None)
        if index is None:
            return CombatResult(success=False, error_key="game.combat.errors.combatant_not_found")
        target = index + (1 if delta >= 0 else -1)
        if target < 0 or target >= len(order):
            return self.get_state(campaign_id=campaign_id, user_id=user_id)

        current_id = self._combatant_id_at_turn(combat, config)
        order[index], order[target] = order[target], order[index]
        self.encounters.renumber(combatant_ids=[c["id"] for c in order])
        return self._preserving_turn(
            combat, campaign_id=campaign_id, user_id=user_id, keep=current_id
        )

    def record_initiative_roll(
        self,
        *,
        campaign_id: str,
        user_id: str,
        actor_id: str,
        total: float,
        token_id: str | None = None,
    ) -> None:
        """Adopt the result of a ``roll.initiative`` made from an actor sheet.

        This is how a player rolls their own initiative: they click it on their
        sheet and the tracker picks the number up. Systems whose initiative is
        not a number ignore it — there is nothing to put the result into.
        """
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is None:
            return
        if not self._config_for(campaign_id=campaign_id, user_id=user_id).is_numeric:
            return
        try:
            value = float(total)
        except (TypeError, ValueError):
            return
        combatants = self.encounters.list_combatants(combat_id=combat["id"])
        if token_id:
            matched = [c for c in combatants if str(c.get("token_id") or "") == token_id]
        else:
            matched = [c for c in combatants if str(c.get("actor_id") or "") == actor_id]
        for combatant in matched:
            self.encounters.set_initiative(
                combatant_id=combatant["id"],
                initiative=_format_number(value),
                sort_value=value,
                tie_break=0,
            )



    def advance_turn(self, *, campaign_id: str, user_id: str, delta: int) -> CombatResult:
        """Step one turn forward or back, wrapping into the next/previous round."""
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        state = self.get_state(campaign_id=campaign_id, user_id=user_id)
        if state.combat is None or not state.active:
            return CombatResult(success=False, error_key="game.combat.errors.inactive")
        order = state.combatants
        if not order:
            return state

        round_number = int(state.combat["round_number"])
        turn = int(state.combat["turn_index"]) + (1 if delta >= 0 else -1)
        wrapped_forward = turn >= len(order)
        if wrapped_forward:
            turn, round_number = 0, round_number + 1
        elif turn < 0:
            if round_number > 1:
                turn, round_number = len(order) - 1, round_number - 1
            else:
                turn = 0

        self.encounters.set_position(
            combat_id=state.combat["id"], round_number=round_number, turn_index=turn
        )

        updated: list[dict] = []
        expired: list[dict] = []
        ticks: list[dict] = []
        if wrapped_forward:
            updated, expired = self.effects.tick_round(campaign_id=campaign_id)
        if delta >= 0:
            actor_update, ticks = self.effects.tick_turn(
                campaign_id=campaign_id, actor_id=str(order[turn].get("actor_id") or "")
            )
            if actor_update is not None:
                updated.append(actor_update)
        return self._with_side_effects(
            self.get_state(campaign_id=campaign_id, user_id=user_id),
            updated_actors=updated,
            expired_effects=expired,
            effect_ticks=ticks,
        )

    def set_turn(self, *, campaign_id: str, user_id: str, combatant_id: str) -> CombatResult:
        """Jump the turn marker straight to a combatant."""
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is None:
            return CombatResult(success=False, error_key="game.combat.errors.inactive")
        config = self._config_for(campaign_id=campaign_id, user_id=user_id)
        order = self._ordered(combat=combat, config=config)
        index = next((i for i, c in enumerate(order) if c["id"] == combatant_id), None)
        if index is None:
            return CombatResult(success=False, error_key="game.combat.errors.combatant_not_found")
        self.encounters.set_position(
            combat_id=combat["id"], round_number=int(combat["round_number"]), turn_index=index
        )
        return self.get_state(campaign_id=campaign_id, user_id=user_id)

    def advance_round(self, *, campaign_id: str, user_id: str, delta: int) -> CombatResult:
        """Step a whole round without walking every turn."""
        if not self._can_manage(campaign_id=campaign_id, user_id=user_id):
            return CombatResult(success=False, error_key="game.combat.errors.gm_required")
        combat = self.encounters.get_active(campaign_id=campaign_id)
        if combat is None:
            return CombatResult(success=False, error_key="game.combat.errors.inactive")
        round_number = max(1, int(combat["round_number"]) + (1 if delta >= 0 else -1))
        self.encounters.set_position(
            combat_id=combat["id"], round_number=round_number, turn_index=0
        )
        updated: list[dict] = []
        expired: list[dict] = []
        if delta >= 0:
            updated, expired = self.effects.tick_round(campaign_id=campaign_id)
        return self._with_side_effects(
            self.get_state(campaign_id=campaign_id, user_id=user_id),
            updated_actors=updated,
            expired_effects=expired,
        )



    def _ordered(self, *, combat: dict, config: CombatConfig) -> list[dict]:
        combatants = self.encounters.list_combatants(combat_id=combat["id"])
        return sorted(combatants, key=_order_key(config))

    def _combatant_id_at_turn(self, combat: dict, config: CombatConfig) -> str:
        order = self._ordered(combat=combat, config=config)
        if not order:
            return ""
        index = max(0, min(len(order) - 1, int(combat["turn_index"])))
        return str(order[index]["id"])

    def _preserving_turn(
        self, combat: dict, *, campaign_id: str, user_id: str, keep: str | None = None
    ) -> CombatResult:
        """Re-point the turn marker at ``keep`` after the order changed.

        Without this, adding a combatant with high initiative would silently hand
        the turn to whoever the old index now lands on.
        """
        config = self._config_for(campaign_id=campaign_id, user_id=user_id)
        target = self._combatant_id_at_turn(combat, config) if keep is None else keep
        order = self._ordered(combat=combat, config=config)
        index = next((i for i, c in enumerate(order) if c["id"] == target), None)
        if index is None:
            index = max(0, min(len(order) - 1, int(combat["turn_index"]))) if order else 0
        self.encounters.set_position(
            combat_id=combat["id"], round_number=int(combat["round_number"]), turn_index=index
        )
        return self.get_state(campaign_id=campaign_id, user_id=user_id)



    def _build_combatants(
        self, *, combat: dict, user_id: str, config: CombatConfig
    ) -> list[dict]:
        """Order the roster and decorate it with what the panel draws.

        Players see a hidden combatant as an unnamed placeholder rather than not
        at all, so the turn count stays honest.
        """
        is_gm = self._can_manage(campaign_id=str(combat["campaign_id"]), user_id=user_id)
        order = self._ordered(combat=combat, config=config)
        if not order:
            return []
        current_index = max(0, min(len(order) - 1, int(combat["turn_index"])))
        next_index = (current_index + 1) % len(order) if len(order) > 1 else -1

        token_ids = [str(c["token_id"]) for c in order if c.get("token_id")]
        conditions_by_token = self.conditions.list_by_tokens(token_ids)
        projections: dict[str, dict] = {}
        out: list[dict] = []

        for index, combatant in enumerate(order):
            view = {
                "id": combatant["id"],
                "actor_id": combatant.get("actor_id") or "",
                "token_id": combatant.get("token_id") or "",
                "name": combatant["name"],
                "initiative": combatant["initiative"],
                "hidden": combatant["hidden"],
                "defeated": combatant["defeated"],
                "position": index + 1,
                "is_current": index == current_index,
                "is_next": index == next_index,
                "has_acted": index < current_index,
                "can_move_up": config.is_manual_order and index > 0,
                "can_move_down": config.is_manual_order and index < len(order) - 1,
                "portrait_url": "",
                "bar": None,
                "conditions_count": 0,
                "effects_count": 0,
            }
            if combatant["hidden"] and not is_gm:
                view["name"] = "???"
                out.append(view)
                continue

            actor = (
                self.actors.get(str(combatant["actor_id"])) if combatant.get("actor_id") else None
            )
            token = (
                self.tokens.get_by_id(str(combatant["token_id"]))
                if combatant.get("token_id")
                else None
            )
            projection: dict = {}
            if actor is not None:
                actor_id = str(actor["id"])
                if actor_id not in projections:
                    projections[actor_id] = self.projector.project(actor)
                projection = projections[actor_id]

            if token is not None:
                token_conditions = conditions_by_token.get(str(token["id"]), [])
                token_view = self.token_views.build_view(
                    token=token,
                    projection=projection,
                    actor=actor,
                    conditions=token_conditions,
                )
                view["bar"] = _primary_bar(token_view.get("bars"))
                view["conditions_count"] = len(token_conditions)
                view["effects_count"] = _count(token_view.get("effects"))
                overrides = (
                    token.get("overrides") if isinstance(token.get("overrides"), dict) else {}
                )
                view["portrait_url"] = str(
                    token.get("token_asset_url") or overrides.get("token_asset_url") or ""
                )
            else:
                view["bar"] = _primary_bar(projection.get("bars"))
                view["effects_count"] = _count(projection.get("effects"))

            if not view["portrait_url"] and actor is not None:
                view["portrait_url"] = (
                    actor_token_image_url(actor) or actor_image_url(actor, "portrait") or ""
                )
            out.append(view)
        return out



    def _campaign(self, *, campaign_id: str, user_id: str) -> dict | None:
        row = self.campaigns.get_for_user(campaign_id=campaign_id, user_id=user_id)
        return dict(row) if row is not None else None

    def _config_for(self, *, campaign_id: str, user_id: str) -> CombatConfig:
        campaign = self._campaign(campaign_id=campaign_id, user_id=user_id)
        return self.configs.get_for_system((campaign or {}).get("active_system_id"))

    def _can_manage(self, *, campaign_id: str, user_id: str) -> bool:
        role = self.campaigns.get_member_role(campaign_id=campaign_id, user_id=user_id)
        return role in {PlayerRole.GM.value, PlayerRole.ASSISTANT_GM.value}

    def _campaign_actor(self, actor_id: str, *, campaign_id: str) -> dict | None:
        if not actor_id:
            return None
        actor = self.actors.get(actor_id)
        if actor is None or actor["campaign_id"] != campaign_id or actor["status"] != "active":
            return None
        return actor

    def _find(self, combat: dict, combatant_id: str) -> bool:
        return any(
            c["id"] == combatant_id
            for c in self.encounters.list_combatants(combat_id=combat["id"])
        )

    def _is_npc(self, combatant: dict, *, campaign_id: str) -> bool:
        actor = self._campaign_actor(str(combatant.get("actor_id") or ""), campaign_id=campaign_id)
        return str((actor or {}).get("type") or "").strip().lower() in NPC_TYPES

    def _with_side_effects(
        self,
        state: CombatResult,
        *,
        updated_actors: list[dict],
        expired_effects: list[dict] | None = None,
        effect_ticks: list[dict] | None = None,
    ) -> CombatResult:
        return CombatResult(
            success=state.success,
            campaign_id=state.campaign_id,
            combat=state.combat,
            combatants=state.combatants,
            config=state.config,
            updated_actors=updated_actors,
            expired_effects=expired_effects or [],
            effect_ticks=effect_ticks or [],
            error_key=state.error_key,
        )


def _order_key(config: CombatConfig) -> Callable[[dict], tuple]:
    """Sort combatants the way the active system asked for.

    Unset always sinks to the bottom: a combatant with no value has not taken a
    place in the order yet, whatever the system counts with.
    """
    if config.is_manual_order:
        return lambda c: (c["sort_value"] is None, -(c["sort_value"] or 0), c["created_at"])
    direction = 1 if config.sort == "asc" else -1
    return lambda c: (
        c["sort_value"] is None,
        direction * (c["sort_value"] or 0),
        -c["tie_break"],
        c["created_at"],
    )


def _parse_number(text: str) -> float | None:
    try:
        return float(text.replace(",", "."))
    except (TypeError, ValueError):
        return None


def _format_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(round(value, 2))


def _count(value: object) -> int:
    return len(value) if isinstance(value, list) else 0


def _primary_bar(bars: object) -> dict | None:
    """The tracker shows one bar per combatant: whatever the token draws first."""
    if not isinstance(bars, dict):
        return None
    raw = bars.get("bar_1")
    if not isinstance(raw, dict) or raw.get("value") is None:
        return None
    try:
        value = float(raw["value"])
        maximum = float(raw.get("max", value))
    except (TypeError, ValueError):
        return None
    percent = max(0, min(100, round(value / maximum * 100))) if maximum > 0 else None
    return {
        "value": int(value) if value.is_integer() else value,
        "max": int(maximum) if maximum.is_integer() else maximum,
        "percent": percent,
        "visibility": raw.get("visibility", "everyone"),
    }
