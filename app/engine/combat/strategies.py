from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from app.engine.effects.active_effects import apply_stat_modifiers
from app.engine.rules.derived_field_service import apply_derived
from app.engine.rules.formula_engine import FormulaError, FormulaResult, evaluate
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage

INSTANCE_KEY = "_actor_instance"


@dataclass(frozen=True)
class InitiativeResult:
    participant_id: str
    label: str
    value: float | None
    sort_key: float
    data: dict = field(default_factory=dict)


class CombatStrategyService:
    """System-authored turn order and initiative strategies.

    The core owns encounter state. The active system owns how participant order is
    produced through ``rules/combat.gw.json`` and, for one-off participant rolls,
    through the system's declarative ``roll.initiative`` action when available.
    """

    def __init__(self) -> None:
        self.storage = ScopedJsonStorage()
        self.rules = SystemRulesService()

    def roll_order(
        self,
        *,
        combat_config: dict,
        participants: list[dict],
        actors_by_id: dict[str, dict],
        campaign_id: str,
        tokens_by_id: dict[str, dict] | None = None,
    ) -> list[InitiativeResult]:
        turn_order = combat_config.get("turnOrder") if isinstance(combat_config.get("turnOrder"), dict) else combat_config
        initiative = self._initiative_config(combat_config=combat_config, turn_order=turn_order)
        mode = str(initiative.get("mode") or self._mode_for_strategy(str(turn_order.get("strategy") or "manual")))
        tokens_by_id = tokens_by_id or {}
        if mode == "individual":
            return self._individual_initiative(
                initiative=initiative,
                turn_order=turn_order,
                participants=participants,
                actors_by_id=actors_by_id,
                tokens_by_id=tokens_by_id,
                campaign_id=campaign_id,
            )
        if mode == "side":
            return self._side_initiative(initiative=initiative, turn_order=turn_order, participants=participants)
        if mode == "deck":
            return self._deck_draw(turn_order={**turn_order, **initiative}, participants=participants)
        if mode == "alternating_sides":
            return self._alternating_sides(turn_order=turn_order, participants=participants)
        if mode == "spotlight":
            return self._spotlight(participants=participants)
        return self._manual(participants=participants)

    def roll_participant_initiative(
        self,
        *,
        combat_config: dict,
        participant: dict,
        actor: dict | None,
        campaign_id: str,
        token: dict | None = None,
    ) -> InitiativeResult | None:
        """Roll initiative for exactly one participant using system-authored rules.

        Preference order:
        1. canonical ``combat.gw.json -> initiative.roll.formula``;
        2. ``initiative.roll.actionId`` pointing to a system action such as
           ``roll.initiative``;
        3. strategy-specific single result for deck/manual systems.
        """
        turn_order = combat_config.get("turnOrder") if isinstance(combat_config.get("turnOrder"), dict) else {}
        initiative = self._initiative_config(combat_config=combat_config, turn_order=turn_order)
        mode = str(initiative.get("mode") or self._mode_for_strategy(str(turn_order.get("strategy") or "manual")))
        if mode == "deck":
            return self._deck_draw(turn_order={**turn_order, **initiative}, participants=[participant])[0]

        context = self._actor_context(actor=actor, campaign_id=campaign_id, token=token)
        formula, source = self._initiative_formula(initiative=initiative, turn_order=turn_order, actor=actor)
        if formula:
            sort = initiative.get("sort") if isinstance(initiative.get("sort"), dict) else {}
            return self._evaluate_formula(
                participant=participant,
                formula=formula,
                sort=str(sort.get("direction") or turn_order.get("sort") or "desc"),
                tie_breakers=sort.get("tieBreakers") or turn_order.get("tieBreakers"),
                context=context,
                source=source,
            )

        if mode == "side":
            return self._side_initiative(initiative=initiative, turn_order=turn_order, participants=[participant])[0]
        if mode == "spotlight":
            return self._spotlight(participants=[participant])[0]
        if mode == "alternating_sides":
            return self._alternating_sides(turn_order=turn_order, participants=[participant])[0]
        return self._manual(participants=[participant])[0]

    def _individual_initiative(
        self,
        *,
        initiative: dict,
        turn_order: dict,
        participants: list[dict],
        actors_by_id: dict[str, dict],
        tokens_by_id: dict[str, dict],
        campaign_id: str,
    ) -> list[InitiativeResult]:
        sort = initiative.get("sort") if isinstance(initiative.get("sort"), dict) else {}
        out: list[InitiativeResult] = []
        for participant in participants:
            actor = actors_by_id.get(str(participant.get("actor_id") or ""))
            token = tokens_by_id.get(str(participant.get("token_id") or ""))
            context = self._actor_context(actor=actor, campaign_id=campaign_id, token=token)
            formula, source = self._initiative_formula(initiative=initiative, turn_order=turn_order, actor=actor)
            if not formula:
                formula = str(turn_order.get("formula") or "1d20")
                source = {"kind": "turn_order", "strategy": "formula_sort"}
            out.append(
                self._evaluate_formula(
                    participant=participant,
                    formula=formula,
                    sort=str(sort.get("direction") or turn_order.get("sort") or "desc"),
                    tie_breakers=sort.get("tieBreakers") or turn_order.get("tieBreakers"),
                    context=context,
                    source=source,
                )
            )
        return out

    def _formula_sort(
        self,
        *,
        turn_order: dict,
        participants: list[dict],
        actors_by_id: dict[str, dict],
        tokens_by_id: dict[str, dict],
        campaign_id: str,
    ) -> list[InitiativeResult]:
        formula = str(turn_order.get("formula") or "1d20")
        sort = str(turn_order.get("sort") or "desc")
        out: list[InitiativeResult] = []
        for participant in participants:
            actor = actors_by_id.get(str(participant.get("actor_id") or ""))
            token = tokens_by_id.get(str(participant.get("token_id") or ""))
            context = self._actor_context(actor=actor, campaign_id=campaign_id, token=token)
            out.append(
                self._evaluate_formula(
                    participant=participant,
                    formula=formula,
                    sort=sort,
                    tie_breakers=turn_order.get("tieBreakers"),
                    context=context,
                    source={"kind": "turn_order", "strategy": "formula_sort"},
                )
            )
        return out

    def _evaluate_formula(
        self,
        *,
        participant: dict,
        formula: str,
        sort: str,
        tie_breakers: Any,
        context: dict,
        source: dict,
    ) -> InitiativeResult:
        actor = context.get("core") if isinstance(context.get("core"), dict) else None
        try:
            result = evaluate(formula, context=context, scope={}, helpers=self.rules.get_helpers(actor["system_id"]) if actor else {})
        except (FormulaError, KeyError, TypeError):
            result = FormulaResult(total=0, groups=[])
        total = result.int_total
        tiebreaker = self._tie_breaker(tie_breakers, context=context, participant=participant)
        sort_key = float(total) + (float(tiebreaker) / 1000.0)
        if sort == "asc":
            sort_key = -sort_key
        return InitiativeResult(
            participant_id=str(participant["id"]),
            label=str(total),
            value=float(total),
            sort_key=sort_key,
            data={
                "kind": "formula",
                "formula": formula,
                "total": total,
                "groups": result.groups,
                "modifier": result.modifier,
                "source": source,
            },
        )

    def _initiative_formula(self, *, initiative: dict, turn_order: dict, actor: dict | None) -> tuple[str, dict]:
        roll = initiative.get("roll") if isinstance(initiative.get("roll"), dict) else {}
        action_id = str(roll.get("actionId") or "roll.initiative")
        label = initiative.get("label") or turn_order.get("label")

        if roll.get("formula"):
            return str(roll["formula"]), {"kind": "initiative", "label": label, "actionId": action_id}
        if actor and action_id:
            action = self.rules.get_action(actor["system_id"], action_id)
            if isinstance(action, dict) and action.get("type") == "roll" and action.get("formula"):
                return str(action["formula"]), {"kind": "system_action", "actionId": action_id, "label": action.get("label") or label}
        return "", {"kind": "manual"}

    def _initiative_config(self, *, combat_config: dict, turn_order: dict) -> dict:
        initiative = combat_config.get("initiative") if isinstance(combat_config.get("initiative"), dict) else {}
        if initiative:
            return initiative
        return {
            "mode": self._mode_for_strategy(str(turn_order.get("strategy") or "manual")),
            "label": turn_order.get("label") or "Iniciativa",
            "roll": {"actionId": "roll.initiative"},
            "sort": {
                "direction": turn_order.get("sort") or "desc",
                "tieBreakers": turn_order.get("tieBreakers") or [],
            },
            "allowReroll": True,
            "allowManualEdit": True,
        }

    def _mode_for_strategy(self, strategy: str) -> str:
        return {
            "formula_sort": "individual",
            "group_formula_sort": "side",
            "deck_draw": "deck",
            "spotlight": "spotlight",
            "alternating_sides": "alternating_sides",
        }.get(strategy, "manual")

    def _actor_context(self, *, actor: dict | None, campaign_id: str, token: dict | None = None) -> dict:
        if not actor:
            return {"core": {}, "sheet": {}}
        data: dict[str, Any] = {}
        core = dict(actor)
        if token and token.get("actor_link_mode") == "unlinked":
            overrides = token.get("overrides") if isinstance(token.get("overrides"), dict) else {}
            instance = overrides.get(INSTANCE_KEY) if isinstance(overrides.get(INSTANCE_KEY), dict) else None
            if instance is not None:
                data = instance.get("data") if isinstance(instance.get("data"), dict) else {}
                core["name"] = str(instance.get("name") or token.get("name") or actor.get("name") or "")
        if not data:
            envelope = self.storage.read_actor(system_id=actor["system_id"], campaign_id=campaign_id, actor_id=actor["id"]) or {"data": {}}
            data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        helpers = self.rules.get_helpers(actor["system_id"])
        derived_rules = self.rules.get_derived(actor["system_id"])
        sheet = apply_derived(
            actor_type=str(actor.get("type") or ""),
            data=data,
            derived_rules=derived_rules,
            helpers=helpers,
            core={"name": core.get("name") or actor.get("name") or ""},
        )
        sheet = apply_stat_modifiers(sheet)
        return {"core": core, "sheet": sheet}

    def _tie_breaker(self, raw: Any, *, context: dict, participant: dict) -> int:
        if not isinstance(raw, list):
            return 0
        for item in raw[:4]:
            if not isinstance(item, str) or not item.startswith("@"):
                continue
            value = _lookup({"participant": participant, **context}, item[1:])
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return 0

    def _group_formula_sort(self, *, turn_order: dict, participants: list[dict]) -> list[InitiativeResult]:
        initiative = {
            "label": turn_order.get("label") or "Iniciativa",
            "roll": {"formula": turn_order.get("formula") or "1d6"},
            "sort": {"direction": turn_order.get("sort") or "desc", "tieBreakers": turn_order.get("tieBreakers") or []},
            "groups": turn_order.get("groups") or [],
        }
        return self._side_initiative(initiative=initiative, turn_order=turn_order, participants=participants)

    def _side_initiative(self, *, initiative: dict, turn_order: dict, participants: list[dict]) -> list[InitiativeResult]:
        sort = initiative.get("sort") if isinstance(initiative.get("sort"), dict) else {}
        direction = str(sort.get("direction") or turn_order.get("sort") or "desc")
        roll = initiative.get("roll") if isinstance(initiative.get("roll"), dict) else {}
        formula = str(roll.get("formula") or turn_order.get("formula") or "1d6")
        groups = initiative.get("groups") if isinstance(initiative.get("groups"), list) else []
        group_scores: dict[str, int] = {}
        for group in groups:
            if not isinstance(group, dict):
                continue
            group_id = str(group.get("id") or "")
            if not group_id:
                continue
            group_formula = str(group.get("formula") or formula)
            group_scores[group_id] = self._evaluate_group_formula(group_formula)
        out: list[InitiativeResult] = []
        for index, participant in enumerate(participants):
            group_key = str(participant.get("group_key") or participant.get("metadata", {}).get("side") or "players")
            score = group_scores.get(group_key)
            if score is None:
                score = self._evaluate_group_formula(formula)
                group_scores[group_key] = score
            sort_key = float(score) * 1000 - index
            if direction == "asc":
                sort_key = -sort_key
            out.append(
                InitiativeResult(
                    str(participant["id"]),
                    str(score),
                    float(score),
                    sort_key,
                    {"kind": "side_formula", "group": group_key, "formula": formula, "total": score, "source": {"kind": "initiative", "mode": "side"}},
                )
            )
        return out

    def _evaluate_group_formula(self, formula: str) -> int:
        try:
            result = evaluate(formula, context={}, scope={}, helpers={})
            return result.int_total
        except (FormulaError, KeyError, TypeError, ValueError):
            return random.randint(1, 6)

    def _deck_draw(self, *, turn_order: dict, participants: list[dict]) -> list[InitiativeResult]:
        cards = _standard_deck(include_jokers=bool((turn_order.get("deck") or {}).get("includeJokers", True)) if isinstance(turn_order.get("deck"), dict) else True)
        random.shuffle(cards)
        out: list[InitiativeResult] = []
        for index, participant in enumerate(participants):
            card = cards[index % len(cards)] if cards else {"label": "—", "sort": 0}
            out.append(
                InitiativeResult(
                    participant_id=str(participant["id"]),
                    label=str(card["label"]),
                    value=float(card["sort"]),
                    sort_key=float(card["sort"]),
                    data={"kind": "card", **card},
                )
            )
        return out

    def _manual(self, *, participants: list[dict]) -> list[InitiativeResult]:
        total = len(participants)
        return [InitiativeResult(str(p["id"]), str(i + 1), float(total - i), float(total - i), {"kind": "manual"}) for i, p in enumerate(participants)]

    def _spotlight(self, *, participants: list[dict]) -> list[InitiativeResult]:
        return [InitiativeResult(str(p["id"]), "", None, float(len(participants) - i), {"kind": "spotlight", "actedThisRound": False}) for i, p in enumerate(participants)]

    def _alternating_sides(self, *, turn_order: dict, participants: list[dict]) -> list[InitiativeResult]:
        sides = turn_order.get("sides") if isinstance(turn_order.get("sides"), list) else []
        order = [str(side.get("id") or "") for side in sides if isinstance(side, dict)] or ["players", "gm"]
        out: list[InitiativeResult] = []
        for index, participant in enumerate(participants):
            side = str(participant.get("group_key") or participant.get("metadata", {}).get("side") or order[index % len(order)])
            side_index = order.index(side) if side in order else len(order)
            sort_key = float((len(order) - side_index) * 1000 - index)
            out.append(InitiativeResult(str(participant["id"]), side, float(sort_key), sort_key, {"kind": "alternating_sides", "side": side}))
        return out


def _lookup(root: dict, dotted: str) -> Any:
    cursor: Any = root
    for segment in dotted.split("."):
        if isinstance(cursor, dict):
            cursor = cursor.get(segment)
        else:
            return None
    return cursor


def _standard_deck(*, include_jokers: bool) -> list[dict]:
    ranks = [("2", 2), ("3", 3), ("4", 4), ("5", 5), ("6", 6), ("7", 7), ("8", 8), ("9", 9), ("10", 10), ("J", 11), ("Q", 12), ("K", 13), ("A", 14)]
    suits = [("♣", "clubs", 1), ("♦", "diamonds", 2), ("♥", "hearts", 3), ("♠", "spades", 4)]
    cards: list[dict] = []
    for rank, rank_value in ranks:
        for symbol, suit, suit_value in suits:
            cards.append({"label": f"{rank}{symbol}", "rank": rank, "suit": suit, "sort": rank_value * 10 + suit_value, "joker": False})
    if include_jokers:
        cards.append({"label": "Joker", "rank": "Joker", "suit": "red", "sort": 1000, "joker": True})
        cards.append({"label": "Joker", "rank": "Joker", "suit": "black", "sort": 999, "joker": True})
    return cards
