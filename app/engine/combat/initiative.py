from __future__ import annotations

from typing import Any

from app.engine.combat.combat_config import CombatConfig
from app.engine.effects.active_effects import apply_stat_modifiers
from app.engine.rules.derived_field_service import apply_derived
from app.engine.rules.formula_engine import FormulaError, evaluate
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage

INSTANCE_KEY = "_actor_instance"


class InitiativeRoller:
    """Turns an actor into a single initiative number.

    The formula is the system's, from ``combat.gw.json`` or from the roll action
    it points at, so a package declares it once. The core has no formula of its
    own: a system that never declared one has nothing to roll, and says so by
    getting ``None`` back.
    """

    def __init__(self) -> None:
        self.storage = ScopedJsonStorage()
        self.rules = SystemRulesService()

    def roll(
        self,
        *,
        combat_config: CombatConfig,
        actor: dict | None,
        campaign_id: str,
        token: dict | None = None,
    ) -> tuple[float, float] | None:
        """Return ``(total, tie_breaker)``, or ``None`` if there is no formula."""
        formula = self._formula(combat_config, actor)
        if not formula:
            return None
        context = self._actor_context(actor=actor, campaign_id=campaign_id, token=token)
        helpers = self.rules.get_helpers(actor["system_id"]) if actor else {}
        try:
            total = float(evaluate(formula, context=context, scope={}, helpers=helpers).int_total)
        except (FormulaError, KeyError, TypeError, ValueError):
            total = 0.0
        return total, self._tie_breaker(combat_config.tie_breaker, context)

    def _formula(self, combat_config: CombatConfig, actor: dict | None) -> str:
        if combat_config.formula:
            return combat_config.formula
        if actor and combat_config.action_id:
            action = self.rules.get_action(actor["system_id"], combat_config.action_id)
            if isinstance(action, dict) and action.get("type") == "roll" and action.get("formula"):
                return str(action["formula"])
        return ""

    def _tie_breaker(self, path: str, context: dict) -> float:
        """Resolve the system's tie-breaker stat (e.g. Dexterity) to a number."""
        if not path.startswith("@"):
            return 0.0
        try:
            return float(_lookup(context, path[1:]))
        except (TypeError, ValueError):
            return 0.0

    def _actor_context(
        self, *, actor: dict | None, campaign_id: str, token: dict | None
    ) -> dict:
        """Build the ``{core, sheet}`` context the formula engine expects.

        An unlinked token carries its own sheet snapshot in ``overrides``, so two
        copies of the same monster roll from their own numbers.
        """
        if not actor:
            return {"core": {}, "sheet": {}}
        data: dict[str, Any] = {}
        core = dict(actor)
        if token and token.get("actor_link_mode") == "unlinked":
            overrides = token.get("overrides") if isinstance(token.get("overrides"), dict) else {}
            instance = (
                overrides.get(INSTANCE_KEY)
                if isinstance(overrides.get(INSTANCE_KEY), dict)
                else None
            )
            if instance is not None:
                data = instance.get("data") if isinstance(instance.get("data"), dict) else {}
                core["name"] = str(
                    instance.get("name") or token.get("name") or actor.get("name") or ""
                )
        if not data:
            envelope = self.storage.read_actor(
                system_id=actor["system_id"], campaign_id=campaign_id, actor_id=actor["id"]
            ) or {"data": {}}
            data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        sheet = apply_derived(
            actor_type=str(actor.get("type") or ""),
            data=data,
            derived_rules=self.rules.get_derived(actor["system_id"]),
            helpers=self.rules.get_helpers(actor["system_id"]),
            core={"name": core.get("name") or actor.get("name") or ""},
        )
        return {"core": core, "sheet": apply_stat_modifiers(sheet)}


def _lookup(root: dict, dotted: str) -> Any:
    cursor: Any = root
    for segment in dotted.split("."):
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(segment)
    return cursor
