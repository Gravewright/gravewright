"""Server-authoritative execution of sheet actions (§9.3, command ``sheet.action.execute``).

Loads the Actor Core + Sheet Data, applies the system's derived fields, then
interprets the declarative action:

* ``roll``  : evaluate the formula (rolling dice), produce a chat/roll-toast payload
* ``patch`` : evaluate patch expressions and persist them (version bump)
* ``append``: resolve a value template and append it to a target list (used by drop)

All formulas run through the no-eval :mod:`formula_engine`. Nothing here imports
Litestar; the HTTP layer broadcasts chat/roll-toast and realtime events.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace
import re
from typing import Any
from uuid import uuid4

from app.engine.actors.actor_permissions import can_edit_actor, can_view_actor
from app.engine.effects.active_effects import (
    adjust_incoming_damage,
    apply_resource_delta,
    apply_roll_modifiers,
    apply_stat_modifiers,
    effect_modifiers,
    effect_restrictions,
    resolve_resource_target,
)
from app.engine.rules.derived_field_service import apply_derived
from app.engine.rules.condition_effects import sync_condition_effects
from app.engine.rules.threshold_damage import resolve_threshold_damage
from app.engine.rules.formula_engine import FormulaError, evaluate
from app.engine.rules.rules_registry import SystemRulesService
from app.engine.sdk.package_locale_service import PackageLocaleService
from app.engine.rules.token_mapping_resolver import resolve_token_view
from app.engine.system_storage.scoped_json_storage import ScopedJsonStorage
from app.engine.sdk.package_install_service import PackageInstallService
from app.persistence.repositories.actor_repository import ActorRepository
from app.persistence.repositories.campaign_repository import CampaignRepository
from app.persistence.repositories.scene_repository import SceneRepository
from app.persistence.repositories.token_repository import TokenRepository


@dataclass(frozen=True)
class ActionResult:
    success: bool
    actor_id: str | None = None
    campaign_id: str | None = None
    system_id: str | None = None
    actor_name: str | None = None
    action_type: str | None = None
    label: str | None = None

    expression: str | None = None
    groups: list[dict] = field(default_factory=list)
    modifier: int = 0


    total: int | None = 0
    visibility: str = "public"
    chat_card: str | None = None
    roll_toast: str | None = None
    base_formula: str | None = None
    final_formula: str | None = None
    resolved_formula: str | None = None
    display_formula: str | None = None
    roll_input: dict = field(default_factory=dict)
    intent: str | None = None
    source: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    version: int | None = None
    changed_paths: list[str] = field(default_factory=list)
    token_view: dict | None = None

    applied: dict | None = None
    error_key: str | None = None


def _display_expression(formula_groups: list[dict], modifier: int, total: int) -> str:
    if not formula_groups:
        return str(total)
    parts = [group["notation"] for group in formula_groups]
    text = " + ".join(parts)
    if modifier:
        text += f" {'+' if modifier > 0 else '-'} {abs(modifier)}"
    return text


def _resolve_template(node: Any, lookup: dict) -> Any:
    """Resolve a value template: ``"@a.b"`` -> lookup path; dicts/lists recurse."""
    if isinstance(node, dict):
        return {key: _resolve_template(value, lookup) for key, value in node.items()}
    if isinstance(node, list):
        return [_resolve_template(item, lookup) for item in node]
    if isinstance(node, str) and node.startswith("@"):
        cursor: Any = lookup
        for segment in node[1:].split("."):
            if isinstance(cursor, dict):
                cursor = cursor.get(segment)
            else:
                cursor = None
                break
        return cursor
    return node


_DICE_RE = re.compile(r"^[1-9][0-9]?d[1-9][0-9]{0,2}$")


_PATH_REF_RE = re.compile(r"@([A-Za-z0-9_.]+)")


def _lookup_dotted(root: dict, dotted: str) -> Any:
    cursor: Any = root
    for segment in str(dotted or "").split("."):
        if not segment:
            continue
        if isinstance(cursor, dict):
            cursor = cursor.get(segment)
        else:
            return None
    return cursor


def _set_dotted(root: dict, dotted: str, value: Any) -> None:
    parts = [part for part in str(dotted or "").split(".") if part]
    if not parts:
        return
    cursor = root
    for part in parts[:-1]:
        child = cursor.get(part)
        if not isinstance(child, dict):
            child = {}
            cursor[part] = child
        cursor = child
    cursor[parts[-1]] = value


def _resolve_success_raise_healing(data: dict, total: int, groups: list[dict], config: dict) -> dict:
    target = max(1, _safe_int(config.get("target"), 4))
    raise_step = max(1, _safe_int(config.get("raiseStep"), 4))
    maximum = max(1, _safe_int(config.get("maximumHealed"), 2))
    wounds_path = str(config.get("woundsPath") or "wounds.value")
    incapacitated_path = str(config.get("incapacitatedPath") or "conditions.incapacitated")
    before = max(0, _safe_int(_lookup_dotted(data, wounds_path)))
    critical_failure = _roll_all_ones(groups)
    if critical_failure:
        max_path = str(config.get("maxWoundsPath") or "wounds.max")
        wound_max = max(0, _safe_int(_lookup_dotted(data, max_path), 3))
        after = before + 1
        _set_dotted(data, wounds_path, after)
        if after > wound_max:
            _set_dotted(data, incapacitated_path, True)
        return {"healed": 0, "woundsAdded": 1, "woundsBefore": before, "woundsAfter": after, "criticalFailure": True}
    healed = 0 if total < target else min(maximum, 1 + max(0, (total - target) // raise_step))
    healed = min(before, healed)
    after = before - healed
    if healed:
        _set_dotted(data, wounds_path, after)
        _set_dotted(data, incapacitated_path, False)
    return {"healed": healed, "woundsAdded": 0, "woundsBefore": before, "woundsAfter": after, "criticalFailure": False}


def _apply_next_roll_support(data: dict, total: int, groups: list[dict]) -> dict:
    critical_failure = _roll_all_ones(groups)
    awarded = -2 if critical_failure else (0 if total < 4 else 1 + int(total >= 8))
    if not awarded:
        return {"awarded": 0, "totalBonus": 0, "criticalFailure": False}
    effects = data.get("effects") if isinstance(data.get("effects"), list) else []
    support_id = "runtime:support:next-roll"
    existing = next((effect for effect in effects if isinstance(effect, dict) and effect.get("id") == support_id), None)
    current = 0
    if isinstance(existing, dict):
        modifiers = existing.get("data", {}).get("modifiers", []) if isinstance(existing.get("data"), dict) else []
        if modifiers and isinstance(modifiers[0], dict):
            current = _safe_int(modifiers[0].get("value"))
        effects = [effect for effect in effects if effect is not existing]
    combined = max(-2, min(4, current + awarded))
    effects.append({
        "id": support_id,
        "name": "Suporte",
        "img": "",
        "data": {
            "source": "runtime",
            "duration": {"type": "next-roll"},
            "modifiers": [{"target": "roll.check", "operation": "add", "value": combined, "label": "Suporte"}],
        },
    })
    data["effects"] = effects
    return {"awarded": awarded, "totalBonus": combined, "criticalFailure": critical_failure}


def _applied_next_roll_effect_ids(data: dict, applied: list[dict]) -> set[str]:
    applied_ids = {str(entry.get("effectId") or "") for entry in applied if isinstance(entry, dict)}
    return {
        str(effect.get("id") or "")
        for effect in (data.get("effects") if isinstance(data.get("effects"), list) else [])
        if isinstance(effect, dict)
        and str(effect.get("id") or "") in applied_ids
        and isinstance(effect.get("data"), dict)
        and isinstance(effect["data"].get("duration"), dict)
        and effect["data"]["duration"].get("type") == "next-roll"
    }


def _resolve_opposed_trait(data: dict, attribute: str, actor_type: str, helpers: dict, config: dict) -> dict:
    allowed = {str(value) for value in config.get("attributes", [])}
    attribute = attribute if attribute in allowed else "spirit"
    wild_types = {str(value) for value in config.get("wildCardActorTypes", [])}
    trait = data.get("attributes", {}).get(attribute, {}) if isinstance(data.get("attributes"), dict) else {}
    sides = max(4, _safe_int(trait.get("sides"), 4))
    modifier = _safe_int(trait.get("modifier")) - _safe_int(_lookup_dotted(data, "penalty.total"))
    formula = f"acing({sides})"
    if actor_type in wild_types:
        wild_sides = max(4, _safe_int(_lookup_dotted(data, "wildDie.sides"), 6))
        formula = f"max(acing({sides}), acing({wild_sides}))"
    if modifier:
        formula += f" {'+' if modifier > 0 else '-'} {abs(modifier)}"
    active, applied = effect_modifiers(data, {"roll.check", "roll.opposed", f"roll.trait.{attribute}"})
    final_formula = apply_roll_modifiers(formula, active)
    result = evaluate(final_formula, context={"sheet": data}, helpers=helpers)
    consumed = _applied_next_roll_effect_ids(data, applied)
    if consumed:
        data["effects"] = [effect for effect in data.get("effects", []) if not (isinstance(effect, dict) and str(effect.get("id") or "") in consumed)]
    return {
        "attribute": attribute,
        "total": result.int_total,
        "groups": result.groups,
        "formula": final_formula,
        "criticalFailure": _roll_all_ones(result.groups),
        "effects": applied,
        "consumedEffects": sorted(consumed),
    }


def _formula_value_for_display(value: Any) -> str:

    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)
    return "0"


def _resolve_formula_paths_for_display(formula: str, *, context: dict, scope: dict) -> str:
    if not isinstance(formula, str) or "@" not in formula:
        return formula

    def repl(match: re.Match[str]) -> str:
        path = match.group(1)
        root, _, rest = path.partition(".")
        if root in context:
            value = _lookup_dotted(context[root], rest) if rest else context[root]
        elif root in scope:
            value = _lookup_dotted(scope[root], rest) if rest else scope[root]
        else:
            value = None
        return _formula_value_for_display(value)

    return _PATH_REF_RE.sub(repl, formula)


def _input_value(inputs: dict, path: str) -> Any:
    cursor: Any = inputs
    for segment in str(path or "").split("."):
        if not segment:
            continue
        if isinstance(cursor, dict):
            cursor = cursor.get(segment)
        else:
            return None
    return cursor


def _literal_value(raw: str) -> Any:
    text = raw.strip()
    if (text.startswith("'") and text.endswith("'")) or (
        text.startswith('"') and text.endswith('"')
    ):
        return text[1:-1]
    if text.lower() == "true":
        return True
    if text.lower() == "false":
        return False
    try:
        return int(text)
    except ValueError:
        return text


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _roll_all_ones(groups: list[dict]) -> bool:
    values: list[int] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        values.extend(_safe_int(value) for value in group.get("results", []) if value is not None)
        values.extend(_safe_int(value) for value in group.get("dropped", []) if value is not None)
    return bool(values) and all(value == 1 for value in values)


_CONDITION_ROOTS = ("input.", "item.", "sheet.")


def _condition_operand(path: str, scope: dict) -> Any:
    root, _, rest = path.partition(".")
    return _input_value(scope.get(root) or {}, rest)


def _condition_matches(condition: object, scope: dict) -> bool:
    """Very small no-eval predicate language for roll transforms.

    Reads the roll dialog's answers and the item the action was fired from:

      input.mode == 'advantage'
      input.extraModifier != 0
      input.extraDice
      item.data.addStrength

    The item matters because some options belong to the equipment, not to the
    moment: whether a weapon adds the wielder's Strength to its damage is a
    property of the weapon, and asking the player every swing would be asking
    them to remember the weapon's own stat block.
    """
    if condition in (None, "", True):
        return True
    if condition is False or not isinstance(condition, str):
        return False
    text = condition.strip()
    for separator in ("&&", " and "):
        if separator in text:
            return all(_condition_matches(part.strip(), scope) for part in text.split(separator))
    for op in ("==", "!="):
        if op in text:
            left, right = [part.strip() for part in text.split(op, 1)]
            if not left.startswith(_CONDITION_ROOTS):
                return False
            value = _condition_operand(left, scope)
            expected = _literal_value(right)
            return (value == expected) if op == "==" else (value != expected)
    if text.startswith(_CONDITION_ROOTS):
        return bool(_condition_operand(text, scope))
    return False


def _resolve_input_ref(value: object, inputs: dict) -> Any:
    if isinstance(value, str) and value.startswith("@input."):
        return _input_value(inputs, value[len("@input.") :])
    return value


def _append_formula_part(formula: str, value: Any, *, user_supplied: bool = False) -> str:
    if isinstance(value, bool) or value in (None, ""):
        return formula
    if isinstance(value, (int, float)):
        numeric = max(-999, min(999, int(value)))
        if not numeric:
            return formula
        return f"{formula} {'+' if numeric > 0 else '-'} {abs(numeric)}"
    text = str(value).strip()
    if not text:
        return formula

    if user_supplied and not _DICE_RE.fullmatch(text):
        return formula
    if text.startswith("-"):
        return f"{formula} - {text[1:].strip()}"
    return f"{formula} + {text}"


def _apply_roll_transforms(
    formula: str,
    action: dict,
    roll_options: dict | None,
    item: dict | None = None,
    sheet: dict | None = None,
) -> str:
    transforms = action.get("transforms")
    if not isinstance(transforms, list):

        return formula

    roll_options = roll_options if isinstance(roll_options, dict) else {}
    scope = {
        "input": roll_options,
        "item": item if isinstance(item, dict) else {},
        "sheet": sheet if isinstance(sheet, dict) else {},
    }

    next_formula = formula
    for transform in transforms[:16]:
        if not isinstance(transform, dict):
            continue
        if not _condition_matches(transform.get("when"), scope):
            continue

        replace = transform.get("replaceFirstDie")
        if isinstance(replace, dict):
            source = str(replace.get("from") or "")
            target = str(replace.get("to") or "")
            if source and target:
                pattern = re.compile(
                    rf"(?<![A-Za-z0-9_]){re.escape(source)}(?![A-Za-z0-9_])", re.IGNORECASE
                )
                next_formula = pattern.sub(target, next_formula, count=1)

        if "append" in transform:
            value = _resolve_input_ref(transform.get("append"), roll_options)
            next_formula = _append_formula_part(
                next_formula,
                value,
                user_supplied=isinstance(transform.get("append"), str)
                and transform.get("append", "").startswith("@input."),
            )

        if "appendEach" in transform:
            values = _resolve_input_ref(transform.get("appendEach"), roll_options)
            if isinstance(values, list):
                for value in values[:8]:
                    next_formula = _append_formula_part(next_formula, value, user_supplied=True)

    return next_formula


def _roll_visibility(default: object, roll_options: dict | None) -> str:
    fallback = str(default or "public")
    if not isinstance(roll_options, dict):
        return fallback
    visibility = str(roll_options.get("visibility") or fallback)
    return visibility if visibility in {"public", "gm", "blind_gm", "self"} else fallback


_ATTACK_CLASSES = {"melee", "ranged", "spell"}


def _attack_classification(
    action: dict,
    item: dict | None = None,
    roll_options: dict | None = None,
) -> str:
    """Classify an attack without embedding any ruleset-specific mechanics."""
    options = roll_options if isinstance(roll_options, dict) else {}
    item = item if isinstance(item, dict) else {}
    item_data = item.get("data") if isinstance(item.get("data"), dict) else {}

    candidates = (
        options.get("attackMode"),
        options.get("attack_mode"),
        action.get("attackClass"),
        action.get("attack_class"),
        item_data.get("attackMode"),
        item_data.get("attack_mode"),
        item_data.get("attackType"),
        item_data.get("attack_type"),
    )
    for candidate in candidates:
        normalized = str(candidate or "").strip().lower()
        if normalized in _ATTACK_CLASSES:
            return normalized

    item_type = str(item.get("type") or "").strip().lower()
    tags = item_data.get("tags") if isinstance(item_data.get("tags"), list) else []
    normalized_tags = {str(tag).strip().lower() for tag in tags}
    if item_type in {"spell", "power"} or normalized_tags.intersection({"spell", "power", "magic"}):
        return "spell"
    return "ranged" if str(item_data.get("range") or "").strip() else "melee"


def _unlinked_target_sheet(token: dict | None) -> dict | None:
    if not isinstance(token, dict) or token.get("actor_link_mode") != "unlinked":
        return None
    overrides = token.get("overrides")
    overrides = overrides if isinstance(overrides, dict) else {}
    instance = overrides.get("_actor_instance")
    if not isinstance(instance, dict) or not isinstance(instance.get("data"), dict):
        return None
    return deepcopy(instance["data"])


def _target_token_is_eligible(token: dict | None, active_scene: dict | None) -> bool:
    """Targets are game-layer tokens on the campaign's currently active scene."""
    return bool(
        isinstance(token, dict)
        and isinstance(active_scene, dict)
        and token.get("scene_id") == active_scene.get("id")
        and not bool(token.get("hidden"))
    )


def _roll_targets(
    action_id: str | None,
    action: dict,
    item: dict | None = None,
    roll_options: dict | None = None,
) -> set[str]:
    action_key = str(action_id or "")
    dialog = action.get("dialog") if isinstance(action.get("dialog"), dict) else {}
    intent = str(dialog.get("intent") or action.get("intent") or "").strip()
    targets = {"roll.any"}
    if action_key:
        targets.add(f"action.{action_key}")
        if action_key.startswith("roll.save."):
            targets.add(action_key)
        if action_key.startswith("roll.check."):
            targets.add(action_key)
        if action_key.startswith("roll.skill."):
            targets.add(action_key)
        if action_key == "roll.skill" or action_key.startswith("roll.skill."):
            item_data = item.get("data") if isinstance(item, dict) and isinstance(item.get("data"), dict) else {}
            attribute = str(item_data.get("attribute") or "").strip().lower()
            if re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", attribute):
                targets.add(f"action.roll.skill.attribute.{attribute}")
    if intent:
        targets.add(f"roll.{intent}")
    lowered = action_key.lower()
    chat_card = str(action.get("chatCard") or "").lower()
    probe = f"{lowered} {chat_card} {intent}".lower()
    if "attack" in probe:
        targets.add("roll.attack")
        attack_class = _attack_classification(action, item, roll_options)
        targets.add(f"roll.attack.{attack_class}")
        if attack_class == "ranged":
            options = roll_options if isinstance(roll_options, dict) else {}
            proximity = str(options.get("targetDistance") or "").strip().lower()
            if proximity in {"close", "distant"}:
                targets.add(f"roll.attack.ranged.{proximity}")
    if "damage" in probe or "dano" in probe:
        targets.add("roll.damage")
        options = roll_options if isinstance(roll_options, dict) else {}
        damage_class = str(options.get("damageMode") or "").strip().lower()
        if damage_class in {"direct", "area"}:
            targets.add(f"roll.damage.{damage_class}")
    if (
        ".save" in lowered
        or lowered.startswith("roll.save")
        or "save" in probe
        or "salvaguarda" in probe
    ):
        targets.add("roll.save")
    if lowered.startswith("roll.ability") or "check" in probe or "teste" in probe:
        targets.add("roll.check")
    return targets


def _first_action_restriction(sheet_data: dict, targets: set[str]) -> dict | None:
    for target in sorted(targets):
        restrictions = effect_restrictions(sheet_data, target)
        if restrictions:
            return restrictions[0]
    return None


class SheetActionService:
    def __init__(self) -> None:
        self.actors = ActorRepository()
        self.campaigns = CampaignRepository()
        self.scenes = SceneRepository()
        self.tokens = TokenRepository()
        self.storage = ScopedJsonStorage()
        self.systems = PackageInstallService()
        self.rules = SystemRulesService()

    locales = PackageLocaleService()

    def _localized(self, system_id: str, label: object, locale: str | None) -> str:
        """Traduz a chave do ruleset; texto livre passa intacto."""
        text = str(label or "")
        if not text:
            return text
        from app.config import config

        return self.locales.get_locale(system_id, locale or config.default_locale).get(text, text)

    def execute(
        self,
        *,
        actor_id: str,
        action_id: str,
        user_id: str,
        inputs: dict | None = None,
        drop: dict | None = None,
        item: dict | None = None,
        roll_options: dict | None = None,
        target_actor_id: str | None = None,
        target_token_id: str | None = None,
        source_token_id: str | None = None,
        locale: str | None = None,
    ) -> ActionResult:
        ctx = self._load(actor_id, user_id)
        if ctx.error is not None:
            return ctx.error
        actor, campaign = ctx.actor, ctx.campaign

        action = self.rules.get_action(actor["system_id"], action_id)
        if action is None:
            return ActionResult(success=False, error_key="game.actions.errors.action_not_found")
        action_type = action.get("type")

        needs_edit = action_type in {"patch", "append"}
        allowed = (
            can_edit_actor(actor=actor, campaign=campaign, user_id=user_id)
            if needs_edit
            else can_view_actor(actor=actor, campaign=campaign, user_id=user_id)
        )
        if not allowed:
            return ActionResult(success=False, error_key="game.actors.errors.not_allowed")

        envelope = self.storage.read_actor(
            system_id=actor["system_id"], campaign_id=actor["campaign_id"], actor_id=actor_id
        ) or {"version": 1, "data": {}}
        source_token = self.tokens.get_by_id(source_token_id) if source_token_id else None
        if not (
            source_token
            and source_token.get("actor_id") == actor_id
            and source_token.get("actor_link_mode") == "unlinked"
        ):
            source_token = None
        if source_token is not None:
            source_overrides = source_token.get("overrides") if isinstance(source_token.get("overrides"), dict) else {}
            source_instance = source_overrides.get("_actor_instance") if isinstance(source_overrides.get("_actor_instance"), dict) else None
            if source_instance is None:
                source_instance = {
                    "source_actor_id": actor["id"],
                    "name": source_token.get("name") or actor["name"],
                    "type": actor["type"],
                    "system_id": actor["system_id"],
                    "version": int(envelope.get("version", 1)),
                    "data": deepcopy(
                        envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
                    ),
                }
            envelope = {
                "version": int(source_instance.get("version", 1)),
                "data": deepcopy(
                    source_instance.get("data")
                    if isinstance(source_instance.get("data"), dict)
                    else {}
                ),
            }
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        helpers = self.rules.get_helpers(actor["system_id"])
        derived = self.rules.get_derived(actor["system_id"])
        core = {"name": actor["name"]}
        derived_data = apply_derived(
            actor_type=actor["type"], data=data, derived_rules=derived, helpers=helpers, core=core
        )
        effective_data = apply_stat_modifiers(derived_data)
        context = {"core": core, "sheet": effective_data, "item": item or {}}
        scope = {"input": inputs or {}, "drop": drop or {}}

        target_sheet: dict | None = None
        resolved_target_actor_id = target_actor_id
        target_token = self.tokens.get_by_id(target_token_id) if target_token_id else None
        if target_token_id:
            active_scene = self.scenes.get_active_scene(actor["campaign_id"])
            if not _target_token_is_eligible(target_token, active_scene):
                return ActionResult(
                    success=False,
                    actor_id=actor["id"],
                    campaign_id=actor["campaign_id"],
                    system_id=actor["system_id"],
                    actor_name=actor["name"],
                    error_key="game.actions.errors.invalid_target",
                )
            resolved_target_actor_id = str(target_token.get("actor_id") or "") or None
            target_sheet = _unlinked_target_sheet(target_token)
        if target_sheet is None and resolved_target_actor_id:
            target_actor = self.actors.get(resolved_target_actor_id)
            if target_actor is not None and target_actor.get("campaign_id") == actor.get("campaign_id"):
                target_envelope = self.storage.read_actor(
                    system_id=target_actor["system_id"],
                    campaign_id=target_actor["campaign_id"],
                    actor_id=resolved_target_actor_id,
                ) or {"data": {}}
                candidate = target_envelope.get("data")
                if isinstance(candidate, dict):
                    target_sheet = deepcopy(candidate)

        if action_type == "roll":
            if isinstance(action.get("pool"), dict):
                sanitized_allocations = self._pool_target_allocations(
                    actor=actor, action=action, roll_options=roll_options,
                )
                if sanitized_allocations is None:
                    return ActionResult(
                        success=False, actor_id=actor["id"],
                        campaign_id=actor["campaign_id"], system_id=actor["system_id"],
                        actor_name=actor["name"], error_key="game.actions.errors.invalid_targets",
                    )
                roll_options = dict(roll_options or {})
                roll_options["targetAllocations"] = sanitized_allocations
            action_targets = _roll_targets(
                action_id,
                action,
                item if isinstance(item, dict) else None,
                roll_options,
            )
            restriction = _first_action_restriction(data, action_targets)
            if restriction:
                return ActionResult(
                    success=False,
                    actor_id=actor["id"],
                    campaign_id=actor["campaign_id"],
                    system_id=actor["system_id"],
                    actor_name=actor["name"],
                    action_type="roll",
                    error_key="game.actions.errors.restricted_by_effect",
                    metadata={"restriction": restriction},
                )
            result = self._do_roll(
                actor,
                action,
                context,
                scope,
                helpers,
                locale=locale,
                action_id=action_id,
                item=item if isinstance(item, dict) else None,
                roll_options=roll_options,
                target_sheet=target_sheet,
            )
            consumed_effect_ids = _applied_next_roll_effect_ids(
                data,
                result.metadata.get("effects", []) if isinstance(result.metadata, dict) else [],
            )
            if result.success and consumed_effect_ids:
                result = self._apply_self_roll_resolution(
                    actor=actor,
                    user_id=user_id,
                    roll_result=result,
                    resolution={"mode": "consume-effects", "effectIds": sorted(consumed_effect_ids)},
                    source_token=source_token,
                )
            self_resolution = action.get("selfResolution")
            if result.success and isinstance(self_resolution, dict):
                result = self._apply_self_roll_resolution(
                    actor=actor,
                    user_id=user_id,
                    roll_result=result,
                    resolution=self_resolution,
                    source_token=source_token,
                )
            apply_directive = action.get("apply")
            if (
                result.success
                and isinstance(apply_directive, dict)
                and (target_token_id or target_actor_id)
            ):
                lookup = {**context, "input": scope.get("input", {}), "drop": scope.get("drop", {})}
                if target_token_id:
                    return self._apply_to_target_token(
                        roll_result=result,
                        requester_user_id=user_id,
                        target_token_id=target_token_id,
                        directive=apply_directive,
                        lookup=lookup,
                    )
                return self._apply_to_target(
                    roll_result=result,
                    requester_user_id=user_id,
                    target_actor_id=target_actor_id or "",
                    directive=apply_directive,
                    lookup=lookup,
                )
            return result
        if action_type == "chat":
            return self._do_chat(
                actor,
                action,
                context,
                scope,
                locale=locale,
                action_id=action_id,
                item=item if isinstance(item, dict) else None,
            )
        if action_type == "patch":
            return self._do_patch(
                actor, action, data, context, scope, helpers, envelope, core, derived
            )
        if action_type == "append":
            return self._do_append(
                actor, action, data, context, scope, envelope, core, derived, helpers
            )
        return ActionResult(success=False, error_key="game.actions.errors.unsupported_type")

    def _pool_target_allocations(self, *, actor: dict, action: dict, roll_options: dict | None):
        options = roll_options if isinstance(roll_options, dict) else {}
        raw = options.get("targetAllocations")
        if raw in (None, []):
            return []
        if not isinstance(raw, list) or len(raw) > 100:
            return None
        pool = action.get("pool") if isinstance(action.get("pool"), dict) else {}
        count = max(1, min(100, _safe_int(options.get(str(pool.get("countInput") or "")), 1)))
        active_scene = self.scenes.get_active_scene(actor["campaign_id"])
        sanitized = []
        seen = set()
        allocated = 0
        for entry in raw:
            if not isinstance(entry, dict):
                return None
            token_id = str(entry.get("targetTokenId") or "")
            amount = _safe_int(entry.get("amount"))
            token = self.tokens.get_by_id(token_id) if token_id else None
            if token_id in seen or amount < 1 or not _target_token_is_eligible(token, active_scene):
                return None
            seen.add(token_id)
            allocated += amount
            sanitized.append({
                "targetTokenId": token_id,
                "targetActorId": str(token.get("actor_id") or ""),
                "targetName": str(token.get("name") or token.get("actor_id") or "Alvo"),
                "amount": amount,
            })
        return sanitized if allocated == count else None

    def _apply_self_roll_resolution(
        self, *, actor: dict, user_id: str, roll_result: ActionResult, resolution: dict,
        source_token: dict | None = None,
    ) -> ActionResult:
        mode = str(resolution.get("mode") or "")
        with self.storage.lock_entity(
            kind="actor", system_id=actor["system_id"],
            campaign_id=actor["campaign_id"], entity_id=actor["id"],
        ):
            if source_token is not None:
                latest_token = self.tokens.get_by_id(source_token["id"]) or source_token
                overrides = deepcopy(latest_token.get("overrides") or {})
                instance = deepcopy(overrides.get("_actor_instance") or {})
                if not instance:
                    base = self.storage.read_actor(
                        system_id=actor["system_id"],
                        campaign_id=actor["campaign_id"],
                        actor_id=actor["id"],
                    ) or {"version": 1, "data": {}}
                    instance = {
                        "source_actor_id": actor["id"],
                        "name": latest_token.get("name") or actor["name"],
                        "type": actor["type"],
                        "system_id": actor["system_id"],
                        "version": int(base.get("version", 1)),
                        "data": deepcopy(
                            base.get("data") if isinstance(base.get("data"), dict) else {}
                        ),
                    }
                envelope = {
                    "version": int(instance.get("version", 1)),
                    "data": instance.get("data")
                    if isinstance(instance.get("data"), dict)
                    else {},
                }
            else:
                envelope = self.storage.read_actor(
                    system_id=actor["system_id"], campaign_id=actor["campaign_id"],
                    actor_id=actor["id"],
                ) or {"version": 1, "data": {}}
            data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
            changed: list[str] = []
            details: dict[str, Any] = {"mode": mode}
            if mode == "soak-pending-damage":
                pending = data.get("_pendingDamage") if isinstance(data.get("_pendingDamage"), dict) else {}
                pending_wounds = max(0, _safe_int(pending.get("wounds")))
                bennies = data.get("bennies") if isinstance(data.get("bennies"), dict) else {}
                current_bennies = max(0, _safe_int(bennies.get("value")))
                if pending_wounds < 1:
                    return ActionResult(success=False, error_key="game.actions.errors.no_pending_damage")
                if current_bennies < 1:
                    return ActionResult(success=False, error_key="game.rolls.reroll.no_bennies")
                bennies["value"] = current_bennies - 1
                data["bennies"] = bennies
                total = _safe_int(roll_result.total)
                critical_failure = _roll_all_ones(roll_result.groups)
                original_wounds = max(pending_wounds, _safe_int(pending.get("originalWounds"), pending_wounds))
                previously_soaked = max(0, _safe_int(pending.get("soaked")))
                rolled_soak = 0 if total < 4 or critical_failure else 1 + max(0, (total - 4) // 4)
                best_soaked = min(original_wounds, max(previously_soaked, rolled_soak))
                soaked = best_soaked - previously_soaked
                wounds = data.get("wounds") if isinstance(data.get("wounds"), dict) else {}
                wounds["value"] = max(0, _safe_int(wounds.get("value")) - soaked)
                data["wounds"] = wounds
                remaining = original_wounds - best_soaked
                if remaining:
                    pending["wounds"] = remaining
                    pending["originalWounds"] = original_wounds
                    pending["soaked"] = best_soaked
                    data["_pendingDamage"] = pending
                else:
                    data.pop("_pendingDamage", None)
                changed = ["bennies.value", "wounds.value", "_pendingDamage"]
                details |= {"spentBenny": 1, "soaked": soaked, "remaining": remaining, "criticalFailure": critical_failure}
            elif mode == "clear-condition-on-success":
                if _roll_all_ones(roll_result.groups) or _safe_int(roll_result.total) < max(1, _safe_int(resolution.get("target"), 4)):
                    return roll_result
                condition = str(resolution.get("condition") or "")
                conditions = data.get("conditions") if isinstance(data.get("conditions"), dict) else {}
                if not condition or not bool(conditions.get(condition)):
                    return roll_result
                conditions[condition] = False
                data["conditions"] = conditions
                changed = [f"conditions.{condition}"]
                details |= {"condition": condition, "cleared": True}
            elif mode == "recover-wounds-on-success":
                combat = self.rules.get_combat_config(actor["system_id"])
                healing_resolution = combat.get("healingResolution") if isinstance(combat.get("healingResolution"), dict) else {}
                if healing_resolution.get("mode") != "success-raises":
                    return roll_result
                healing = _resolve_success_raise_healing(data, _safe_int(roll_result.total), roll_result.groups, healing_resolution)
                if not healing["healed"] and not healing["woundsAdded"]:
                    return roll_result
                changed = [str(healing_resolution.get("woundsPath") or "wounds.value")]
                if healing["healed"] or healing["woundsAdded"]:
                    changed.append(str(healing_resolution.get("incapacitatedPath") or "conditions.incapacitated"))
                details |= healing
            elif mode == "consume-effects":
                effect_ids = {str(value) for value in resolution.get("effectIds", []) if str(value)}
                effects = data.get("effects") if isinstance(data.get("effects"), list) else []
                remaining = [effect for effect in effects if not (isinstance(effect, dict) and str(effect.get("id") or "") in effect_ids)]
                if len(remaining) == len(effects):
                    return roll_result
                data["effects"] = remaining
                changed = ["effects"]
                details |= {"consumed": sorted(effect_ids)}
            else:
                return roll_result
            from app.config import config
            sync_condition_effects(data, self.rules.get_conditions(actor["system_id"]), self.locales.get_locale(actor["system_id"], config.default_locale))
            version = int(envelope.get("version", 1)) + 1
            if source_token is not None:
                instance["data"] = data
                instance["version"] = version
                overrides["_actor_instance"] = instance
                token_view = self._token_view(
                    actor,
                    data,
                    {"name": instance.get("name") or source_token.get("name") or actor["name"]},
                    self.rules.get_derived(actor["system_id"]),
                    self.rules.get_helpers(actor["system_id"]),
                )
                if isinstance(token_view.get("bars"), dict):
                    overrides.update(token_view["bars"])
                if isinstance(token_view.get("effects"), list):
                    overrides["effects"] = token_view["effects"]
                self.tokens.update_overrides(token_id=source_token["id"], overrides=overrides)
            else:
                self.storage.write_actor(
                    system_id=actor["system_id"], campaign_id=actor["campaign_id"],
                    actor_id=actor["id"], version=version, data=data,
                    action_receipts=envelope.get("_core_action_receipts"),
                )
        return replace(
            roll_result, version=version, changed_paths=changed,
            metadata=dict(roll_result.metadata or {}) | {"selfResolution": details},
        )

    def roll_formula(
        self,
        *,
        actor_id: str,
        formula: str,
        user_id: str,
        label: str = "",
        roll_options: dict | None = None,
        target_sheet: dict | None = None,
    ) -> ActionResult:
        ctx = self._load(actor_id, user_id)
        if ctx.error is not None:
            return ctx.error
        actor, campaign = ctx.actor, ctx.campaign
        if not can_view_actor(actor=actor, campaign=campaign, user_id=user_id):
            return ActionResult(success=False, error_key="game.actors.errors.not_allowed")

        envelope = self.storage.read_actor(
            system_id=actor["system_id"], campaign_id=actor["campaign_id"], actor_id=actor_id
        ) or {"version": 1, "data": {}}
        data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}
        helpers = self.rules.get_helpers(actor["system_id"])
        derived = self.rules.get_derived(actor["system_id"])
        core = {"name": actor["name"]}
        derived_data = apply_derived(
            actor_type=actor["type"], data=data, derived_rules=derived, helpers=helpers, core=core
        )
        effective_data = apply_stat_modifiers(derived_data)
        context = {"core": core, "sheet": effective_data, "item": {}}
        return self._do_roll(
            actor,
            {"formula": formula, "label": label or "Roll", "visibility": "public"},
            context,
            {"input": {}, "drop": {}},
            helpers,
            action_id="dice.roll",
            item=None,
            roll_options=roll_options,
            target_sheet=target_sheet,
        )

    def _do_roll(
        self,
        actor,
        action,
        context,
        scope,
        helpers,
        *,
        locale: str | None = None,
        action_id: str | None = None,
        item: dict | None = None,
        roll_options: dict | None = None,
        target_sheet: dict | None = None,
    ) -> ActionResult:
        formula = action.get("formula")
        if not isinstance(formula, str):
            return ActionResult(success=False, error_key="game.actions.errors.invalid_formula")
        base_formula = formula
        lookup = {**context, "input": scope.get("input", {}), "drop": scope.get("drop", {})}
        resolved_formula = _resolve_template(formula, lookup)
        if isinstance(resolved_formula, str) and resolved_formula:
            formula = resolved_formula
        final_formula = _apply_roll_transforms(
            formula, action, roll_options, item, context.get("sheet", {})
        )
        roll_targets = _roll_targets(action_id, action, item, roll_options)
        active_modifiers, applied_effects = effect_modifiers(
            context.get("sheet", {}),
            roll_targets,
        )
        if isinstance(target_sheet, dict):
            incoming_modifiers, incoming_effects = effect_modifiers(
                target_sheet,
                {f"incoming.{target}" for target in roll_targets},
            )
            active_modifiers.extend(incoming_modifiers)
            applied_effects.extend(incoming_effects)
        final_formula = apply_roll_modifiers(final_formula, active_modifiers)
        label = action.get("label") or "Roll"
        if isinstance(label, str) and label.startswith("@"):
            resolved_label = _resolve_template(label, lookup)
            label = str(resolved_label) if resolved_label not in (None, "") else "Roll"
        label = self._localized(actor["system_id"], label, locale)
        roll_input = dict(roll_options) if isinstance(roll_options, dict) else {}
        pool_config = action.get("pool") if isinstance(action.get("pool"), dict) else None
        pool_metadata: dict[str, Any] | None = None
        try:
            if pool_config:
                count_input = str(pool_config.get("countInput") or "")
                count = max(1, min(100, _safe_int(roll_input.get(count_input), 1)))
                primary_results = [
                    evaluate(final_formula, context=context, scope=scope, helpers=helpers)
                    for _ in range(count)
                ]
                wild_result = None
                wild_formula = pool_config.get("wildFormula")
                if isinstance(wild_formula, str) and wild_formula:
                    resolved_wild = _resolve_template(wild_formula, lookup)
                    final_wild = _apply_roll_transforms(
                        str(resolved_wild or wild_formula), action, roll_options, item,
                        context.get("sheet", {}),
                    )
                    final_wild = apply_roll_modifiers(final_wild, active_modifiers)
                    wild_result = evaluate(final_wild, context=context, scope=scope, helpers=helpers)
                candidates = [
                    {"role": "trait", "index": index, "total": rolled.int_total}
                    for index, rolled in enumerate(primary_results)
                ]
                if wild_result is not None:
                    candidates.append({"role": "wild", "index": 0, "total": wild_result.int_total})
                kept = sorted(candidates, key=lambda entry: entry["total"], reverse=True)[:count]
                target = max(1, _safe_int(pool_config.get("target"), 4))
                step = max(1, _safe_int(pool_config.get("step"), 4))
                hits = sum(1 for entry in kept if entry["total"] >= target)
                raises = sum(max(0, (entry["total"] - target) // step) for entry in kept)
                groups = []
                for index, rolled in enumerate(primary_results):
                    groups.extend({**group, "poolRole": "trait", "poolIndex": index} for group in rolled.groups)
                if wild_result is not None:
                    groups.extend({**group, "poolRole": "wild", "poolIndex": 0} for group in wild_result.groups)
                best = max((entry["total"] for entry in kept), default=0)
                result = type("PoolResult", (), {
                    "groups": groups, "modifier": 0, "int_total": best,
                })()
                declared_targets = deepcopy(roll_input.get("targetAllocations", []))
                pool_metadata = {
                    "count": count,
                    "trait": [rolled.int_total for rolled in primary_results],
                    "wild": wild_result.int_total if wild_result is not None else None,
                    "kept": kept,
                    "hits": hits,
                    "raises": raises,
                    "target": target,
                    "step": step,
                    "declaredTargets": declared_targets,
                    "targetSummary": ", ".join(
                        f"{entry.get('targetName', 'Alvo')} ×{entry.get('amount', 0)}"
                        for entry in declared_targets if isinstance(entry, dict)
                    ),
                }
            else:
                result = evaluate(final_formula, context=context, scope=scope, helpers=helpers)
        except FormulaError:
            return ActionResult(success=False, error_key="game.actions.errors.invalid_formula")
        resolved_formula_for_display = _resolve_formula_paths_for_display(
            final_formula,
            context=context,
            scope=scope,
        )
        display_formula = _display_expression(result.groups, result.modifier, result.int_total)
        visibility = _roll_visibility(action.get("visibility", "public"), roll_options)
        dialog = action.get("dialog") if isinstance(action.get("dialog"), dict) else {}
        source = (
            {"kind": "actor_item_instance", "itemInstanceId": str(item.get("id"))}
            if isinstance(item, dict) and item.get("id")
            else {"kind": "actor", "actorId": actor["id"]}
        )
        metadata = {
            "actionId": action_id or "",
            "actorId": actor["id"],
            "actorName": actor["name"],
            "systemId": actor["system_id"],
            "label": str(label or "Roll"),
            "intent": str(dialog.get("intent") or action.get("intent") or ""),
            "source": source,
            "item": deepcopy(item) if isinstance(item, dict) else {},
            "formula": {
                "base": base_formula,
                "final": final_formula,
                "resolved": resolved_formula_for_display,
                "display": display_formula,
            },
            "rollInput": roll_input,
            "effects": applied_effects,
            "presentation": {
                "chatCard": action.get("chatCard"),
                "rollToast": action.get("rollToast"),
            },
            "visibility": visibility,
        }
        if pool_metadata is not None:
            metadata["pool"] = pool_metadata
        return ActionResult(
            success=True,
            actor_id=actor["id"],
            campaign_id=actor["campaign_id"],
            system_id=actor["system_id"],
            actor_name=actor["name"],
            action_type="roll",
            label=label,
            expression=display_formula,
            groups=result.groups,
            modifier=result.modifier,
            total=result.int_total,
            visibility=visibility,
            chat_card=action.get("chatCard"),
            roll_toast=action.get("rollToast"),
            base_formula=base_formula,
            final_formula=final_formula,
            resolved_formula=resolved_formula_for_display,
            display_formula=display_formula,
            roll_input=roll_input,
            intent=metadata["intent"] or None,
            source=source,
            metadata=metadata,
        )

    def _do_chat(
        self,
        actor: dict,
        action: dict,
        context: dict,
        scope: dict,
        *,
        locale: str | None = None,
        action_id: str | None,
        item: dict | None,
    ) -> ActionResult:
        """Post an item or feature to chat without rolling anything.

        Most of what a character carries is not a die: an Edge, a Hindrance, a
        piece of armour. They still need a way onto the table, and repeating
        their text out loud is the way a table actually uses them. This produces
        the same chat card a roll does, minus the dice: so a system describes it
        once, in the same mapping, and it renders and localises identically.
        """
        lookup = {**context, "input": scope.get("input", {}), "drop": scope.get("drop", {})}
        label = action.get("label") or "Chat"
        if isinstance(label, str) and label.startswith("@"):
            resolved = _resolve_template(label, lookup)
            label = str(resolved) if resolved not in (None, "") else "Chat"
        label = self._localized(actor["system_id"], label, locale)

        source = (
            {"kind": "actor_item_instance", "itemInstanceId": str(item.get("id"))}
            if isinstance(item, dict) and item.get("id")
            else {}
        )
        visibility = str(action.get("visibility") or "public")
        metadata = {
            "actionId": action_id or "",
            "actorId": actor["id"],
            "actorName": actor["name"],
            "systemId": actor["system_id"],
            "label": str(label),
            "intent": str(action.get("intent") or "describe"),
            "source": source,


            "formula": {},
            "rollInput": {},
            "effects": [],
            "presentation": {
                "chatCard": action.get("chatCard"),
                "rollToast": action.get("rollToast"),
            },
            "visibility": visibility,
            "item": item if isinstance(item, dict) else {},
        }
        return ActionResult(
            success=True,
            actor_id=actor["id"],
            campaign_id=actor["campaign_id"],
            system_id=actor["system_id"],
            actor_name=actor["name"],
            action_type="chat",
            label=str(label),
            expression="",
            groups=[],
            modifier=0,

            total=None,
            visibility=visibility,
            chat_card=action.get("chatCard"),
            roll_toast=action.get("rollToast"),
            intent=metadata["intent"],
            source=source,
            metadata=metadata,
        )

    def _apply_to_target(
        self,
        *,
        roll_result: ActionResult,
        requester_user_id: str,
        target_actor_id: str,
        directive: dict,
        lookup: dict,
    ) -> ActionResult:
        """Apply a rolled total to a target actor's resource (damage or heal).

        Damage routes through the target's resistance/vulnerability/immunity via
        ``adjust_incoming_damage``; the resource path comes from the target
        system's combat ``resources`` config. Requires edit access on the target.
        """
        target = self.actors.get(target_actor_id)
        if target is None or target["status"] != "active":
            return ActionResult(success=False, error_key="game.actors.errors.not_found")
        if target["campaign_id"] != roll_result.campaign_id:
            return ActionResult(success=False, error_key="game.actors.errors.not_found")
        target_campaign = self.campaigns.get_for_user(
            campaign_id=target["campaign_id"], user_id=requester_user_id
        )
        if target_campaign is None:
            return ActionResult(success=False, error_key="game.actors.errors.not_found")
        configured_damage = directive.get("resolution") == "configured"
        source = self.actors.get(str(roll_result.actor_id or ""))
        controls_source = bool(
            source
            and can_edit_actor(
                actor=source, campaign=dict(target_campaign), user_id=requester_user_id
            )
        )
        if not can_edit_actor(
            actor=target, campaign=dict(target_campaign), user_id=requester_user_id
        ) and not (configured_damage and controls_source):
            return ActionResult(success=False, error_key="game.actors.errors.not_allowed")

        requested_mode = str(directive.get("mode") or "damage")
        mode = requested_mode if requested_mode in {"heal", "support", "opposed"} else "damage"
        amount = max(0, int(roll_result.total))

        envelope = self.storage.read_actor(
            system_id=target["system_id"],
            campaign_id=target["campaign_id"],
            actor_id=target_actor_id,
        ) or {"version": 1, "data": {}}
        target_data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}

        combat = self.rules.get_combat_config(target["system_id"])
        damage_resolution = combat.get("damageResolution") if isinstance(combat.get("damageResolution"), dict) else {}
        healing_resolution = combat.get("healingResolution") if isinstance(combat.get("healingResolution"), dict) else {}
        opposed_resolution = combat.get("opposedResolution") if isinstance(combat.get("opposedResolution"), dict) else {}
        if mode == "opposed" and directive.get("resolution") == "configured" and opposed_resolution.get("mode") == "trait-comparison":
            input_key = str(opposed_resolution.get("attributeInput") or "opposedAttribute")
            attribute = str(lookup.get("input", {}).get(input_key) or "spirit")
            defense = _resolve_opposed_trait(target_data, attribute, target["type"], self.rules.get_helpers(target["system_id"]), opposed_resolution)
            source_total = _safe_int(roll_result.total)
            source_critical = _roll_all_ones(roll_result.groups)
            difference = source_total - defense["total"]
            success = not source_critical and source_total >= max(1, _safe_int(opposed_resolution.get("target"), 4)) and difference > 0
            raise_step = max(1, _safe_int(opposed_resolution.get("raiseStep"), 4))
            outcome = {"success": success, "tie": difference == 0, "raise": success and difference >= raise_step, "difference": difference, "sourceCriticalFailure": source_critical}
            version = int(envelope.get("version", 1))
            if defense["consumedEffects"]:
                version += 1
                self.storage.write_actor(system_id=target["system_id"], campaign_id=target["campaign_id"], actor_id=target_actor_id, version=version, data=target_data)
            return replace(roll_result, applied={
                "targetActorId": target_actor_id, "targetName": target["name"], "campaignId": target["campaign_id"],
                "systemId": target["system_id"], "mode": "opposed", "sourceTotal": source_total,
                "defense": defense, **outcome, "version": version,
            })
        if mode == "support" and directive.get("resolution") == "configured":
            support = _apply_next_roll_support(target_data, amount, roll_result.groups)
            if not support["awarded"]:
                return replace(roll_result, applied={"targetActorId": target_actor_id, "targetName": target["name"], "mode": "support", **support})
            version = int(envelope.get("version", 1)) + 1
            self.storage.write_actor(system_id=target["system_id"], campaign_id=target["campaign_id"], actor_id=target_actor_id, version=version, data=target_data)
            return replace(roll_result, applied={
                "targetActorId": target_actor_id, "targetName": target["name"],
                "campaignId": target["campaign_id"], "systemId": target["system_id"],
                "mode": "support", **support, "version": version,
            })
        if mode == "heal" and directive.get("resolution") == "configured" and healing_resolution.get("mode") == "success-raises":
            healing = _resolve_success_raise_healing(target_data, amount, roll_result.groups, healing_resolution)
            from app.config import config
            sync_condition_effects(target_data, self.rules.get_conditions(target["system_id"]), self.locales.get_locale(target["system_id"], config.default_locale))
            version = int(envelope.get("version", 1)) + 1
            self.storage.write_actor(system_id=target["system_id"], campaign_id=target["campaign_id"], actor_id=target_actor_id, version=version, data=target_data)
            return replace(roll_result, applied={
                "targetActorId": target_actor_id, "targetName": target["name"],
                "campaignId": target["campaign_id"], "systemId": target["system_id"],
                "mode": "success-raises-healing", "rawAmount": amount,
                **healing, "version": version,
            })
        if mode == "damage" and directive.get("resolution") == "configured" and damage_resolution.get("mode") == "threshold-raises":
            raw_ap = _resolve_template(directive.get("armorPiercing", 0), lookup)
            previous_wounds = _safe_int(_lookup_dotted(target_data, "wounds.value"))
            resolution = resolve_threshold_damage(target_data, amount, damage_resolution, actor_type=target["type"], armor_piercing=_safe_int(raw_ap))
            if resolution.wounds:
                target_data["_pendingDamage"] = {
                    "wounds": resolution.wounds,
                    "originalWounds": resolution.wounds,
                    "soaked": 0,
                    "damage": resolution.damage,
                    "sourceActorId": roll_result.actor_id,
                    "woundPenaltyIncrease": min(3, previous_wounds + resolution.wounds) - min(3, previous_wounds),
                }
            from app.config import config
            sync_condition_effects(target_data, self.rules.get_conditions(target["system_id"]), self.locales.get_locale(target["system_id"], config.default_locale))
            version = int(envelope.get("version", 1)) + 1
            self.storage.write_actor(system_id=target["system_id"], campaign_id=target["campaign_id"], actor_id=target_actor_id, version=version, data=target_data)
            return replace(roll_result, applied={
                "targetActorId": target_actor_id, "targetName": target["name"],
                "campaignId": target["campaign_id"], "systemId": target["system_id"],
                "mode": "threshold-damage", "rawAmount": amount,
                "toughness": resolution.toughness, "armor": resolution.armor,
                "armorPiercing": resolution.armor_piercing,
                "effectiveToughness": resolution.effective_toughness, "raises": resolution.raises,
                "wounds": resolution.wounds, "shaken": resolution.shaken,
                "incapacitated": resolution.incapacitated, "version": version,
            })
        resources = combat.get("resources") if isinstance(combat.get("resources"), dict) else {}

        if mode == "heal":
            damage_type = ""
            applied = amount
            resolved = resolve_resource_target("heal.self", resources)
            delta = applied
        else:
            raw_type = directive.get("damageType")
            damage_type = str(_resolve_template(raw_type, lookup) or "") if raw_type else ""
            applied = adjust_incoming_damage(target_data, amount, damage_type)
            resolved = resolve_resource_target("damage.self", resources)
            delta = -applied

        if resolved is None:
            return ActionResult(success=False, error_key="game.actions.errors.no_target_resource")
        value_path, max_path, floor = resolved
        value_after = apply_resource_delta(target_data, value_path, max_path, floor, delta)
        if value_after is None:
            return ActionResult(success=False, error_key="game.actions.errors.no_target_resource")

        version = int(envelope.get("version", 1)) + 1
        self.storage.write_actor(
            system_id=target["system_id"],
            campaign_id=target["campaign_id"],
            actor_id=target_actor_id,
            version=version,
            data=target_data,
        )
        return replace(
            roll_result,
            applied={
                "targetActorId": target_actor_id,
                "targetName": target["name"],
                "campaignId": target["campaign_id"],
                "systemId": target["system_id"],
                "mode": mode,
                "rawAmount": amount,
                "amount": applied,
                "damageType": damage_type,
                "resourcePath": value_path,
                "valueAfter": value_after,
                "version": version,
            },
        )

    def _apply_to_target_token(
        self,
        *,
        roll_result: ActionResult,
        requester_user_id: str,
        target_token_id: str,
        directive: dict,
        lookup: dict,
    ) -> ActionResult:
        token = self.tokens.get_by_id(target_token_id)
        if token is None or not token.get("actor_id"):
            return ActionResult(success=False, error_key="tokens.errors.not_found")
        scene = self.scenes.get_by_id(token["scene_id"])
        if scene is None or scene["campaign_id"] != roll_result.campaign_id:
            return ActionResult(success=False, error_key="tokens.errors.not_found")
        target = self.actors.get(token["actor_id"])
        if (
            target is None
            or target["status"] != "active"
            or target["campaign_id"] != scene["campaign_id"]
        ):
            return ActionResult(success=False, error_key="tokens.errors.not_found")
        target_campaign = self.campaigns.get_for_user(
            campaign_id=scene["campaign_id"], user_id=requester_user_id
        )
        if target_campaign is None:
            return ActionResult(success=False, error_key="tokens.errors.not_found")
        configured_damage = directive.get("resolution") == "configured"
        source = self.actors.get(str(roll_result.actor_id or ""))
        controls_source = bool(
            source
            and can_edit_actor(
                actor=source, campaign=dict(target_campaign), user_id=requester_user_id
            )
        )
        if not can_edit_actor(
            actor=target, campaign=dict(target_campaign), user_id=requester_user_id
        ) and not (configured_damage and controls_source):
            return ActionResult(success=False, error_key="game.actors.errors.not_allowed")

        is_unlinked = token.get("actor_link_mode") == "unlinked"
        if is_unlinked:
            overrides = dict(token.get("overrides") or {})
            instance = overrides.get("_actor_instance")
            if not isinstance(instance, dict):
                base = self.storage.read_actor(
                    system_id=target["system_id"],
                    campaign_id=target["campaign_id"],
                    actor_id=target["id"],
                ) or {"version": 1, "data": {}}
                instance = {
                    "source_actor_id": target["id"],
                    "name": target["name"],
                    "type": target["type"],
                    "system_id": target["system_id"],
                    "version": int(base.get("version", 1)),
                    "data": dict(base.get("data") if isinstance(base.get("data"), dict) else {}),
                }
            target_data = instance.get("data") if isinstance(instance.get("data"), dict) else {}
        else:
            envelope = self.storage.read_actor(
                system_id=target["system_id"],
                campaign_id=target["campaign_id"],
                actor_id=target["id"],
            ) or {"version": 1, "data": {}}
            target_data = envelope.get("data") if isinstance(envelope.get("data"), dict) else {}

        requested_mode = str(directive.get("mode") or "damage")
        mode = requested_mode if requested_mode in {"heal", "support", "opposed"} else "damage"
        amount = max(0, int(roll_result.total))
        combat = self.rules.get_combat_config(target["system_id"])
        damage_resolution = combat.get("damageResolution") if isinstance(combat.get("damageResolution"), dict) else {}
        healing_resolution = combat.get("healingResolution") if isinstance(combat.get("healingResolution"), dict) else {}
        opposed_resolution = combat.get("opposedResolution") if isinstance(combat.get("opposedResolution"), dict) else {}
        if mode == "opposed" and directive.get("resolution") == "configured" and opposed_resolution.get("mode") == "trait-comparison":
            input_key = str(opposed_resolution.get("attributeInput") or "opposedAttribute")
            attribute = str(lookup.get("input", {}).get(input_key) or "spirit")
            defense = _resolve_opposed_trait(target_data, attribute, target["type"], self.rules.get_helpers(target["system_id"]), opposed_resolution)
            source_total = _safe_int(roll_result.total)
            source_critical = _roll_all_ones(roll_result.groups)
            difference = source_total - defense["total"]
            success = not source_critical and source_total >= max(1, _safe_int(opposed_resolution.get("target"), 4)) and difference > 0
            raise_step = max(1, _safe_int(opposed_resolution.get("raiseStep"), 4))
            outcome = {"success": success, "tie": difference == 0, "raise": success and difference >= raise_step, "difference": difference, "sourceCriticalFailure": source_critical}
            version = int(instance.get("version", 1)) if is_unlinked else int(envelope.get("version", 1))
            token_version = token.get("version")
            if defense["consumedEffects"]:
                if is_unlinked:
                    instance["data"] = target_data; instance["version"] = version + 1; version += 1
                    overrides["_actor_instance"] = instance
                    token_view = self._token_view(target, target_data, {"name": instance.get("name") or token.get("name") or target["name"]}, self.rules.get_derived(target["system_id"]), self.rules.get_helpers(target["system_id"]))
                    if isinstance(token_view.get("effects"), list): overrides["effects"] = token_view["effects"]
                    updated = self.tokens.update_overrides(token_id=target_token_id, overrides=overrides)
                    token_version = updated["version"] if updated else token_version
                else:
                    version += 1
                    self.storage.write_actor(system_id=target["system_id"], campaign_id=target["campaign_id"], actor_id=target["id"], version=version, data=target_data)
            return replace(roll_result, applied={
                "targetActorId": target["id"], "targetTokenId": target_token_id, "targetName": token.get("name") or target["name"],
                "campaignId": target["campaign_id"], "sceneId": token["scene_id"], "systemId": target["system_id"],
                "mode": "opposed", "sourceTotal": source_total, "defense": defense, **outcome,
                "version": version, "tokenVersion": token_version,
            })
        if mode == "support" and directive.get("resolution") == "configured":
            support = _apply_next_roll_support(target_data, amount, roll_result.groups)
            if not support["awarded"]:
                return replace(roll_result, applied={"targetActorId": target["id"], "targetTokenId": target_token_id, "targetName": token.get("name") or target["name"], "mode": "support", **support})
            if is_unlinked:
                instance["data"] = target_data
                instance["version"] = int(instance.get("version", 1)) + 1
                overrides["_actor_instance"] = instance
                token_view = self._token_view(target, target_data, {"name": instance.get("name") or token.get("name") or target["name"]}, self.rules.get_derived(target["system_id"]), self.rules.get_helpers(target["system_id"]))
                if isinstance(token_view.get("bars"), dict): overrides.update(token_view["bars"])
                if isinstance(token_view.get("effects"), list): overrides["effects"] = token_view["effects"]
                updated = self.tokens.update_overrides(token_id=target_token_id, overrides=overrides)
                version = int(instance["version"]); token_version = updated["version"] if updated else token.get("version")
            else:
                version = int(envelope.get("version", 1)) + 1
                self.storage.write_actor(system_id=target["system_id"], campaign_id=target["campaign_id"], actor_id=target["id"], version=version, data=target_data)
                token_version = token.get("version")
            return replace(roll_result, applied={
                "targetActorId": target["id"], "targetTokenId": target_token_id,
                "targetName": token.get("name") or target["name"], "campaignId": target["campaign_id"],
                "sceneId": token["scene_id"], "systemId": target["system_id"],
                "mode": "support", **support, "version": version, "tokenVersion": token_version,
            })
        if mode == "heal" and directive.get("resolution") == "configured" and healing_resolution.get("mode") == "success-raises":
            healing = _resolve_success_raise_healing(target_data, amount, roll_result.groups, healing_resolution)
            from app.config import config
            sync_condition_effects(target_data, self.rules.get_conditions(target["system_id"]), self.locales.get_locale(target["system_id"], config.default_locale))
            if is_unlinked:
                instance["data"] = target_data
                instance["version"] = int(instance.get("version", 1)) + 1
                overrides["_actor_instance"] = instance
                token_view = self._token_view(target, target_data, {"name": instance.get("name") or token.get("name") or target["name"]}, self.rules.get_derived(target["system_id"]), self.rules.get_helpers(target["system_id"]))
                if isinstance(token_view.get("bars"), dict): overrides.update(token_view["bars"])
                if isinstance(token_view.get("effects"), list): overrides["effects"] = token_view["effects"]
                updated = self.tokens.update_overrides(token_id=target_token_id, overrides=overrides)
                version = int(instance["version"]); token_version = updated["version"] if updated else token.get("version")
            else:
                version = int(envelope.get("version", 1)) + 1
                self.storage.write_actor(system_id=target["system_id"], campaign_id=target["campaign_id"], actor_id=target["id"], version=version, data=target_data)
                token_version = token.get("version")
            return replace(roll_result, applied={
                "targetActorId": target["id"], "targetTokenId": target_token_id,
                "targetName": token.get("name") or target["name"], "campaignId": target["campaign_id"],
                "sceneId": token["scene_id"], "systemId": target["system_id"],
                "mode": "success-raises-healing", "rawAmount": amount,
                **healing, "version": version, "tokenVersion": token_version,
            })
        if mode == "damage" and directive.get("resolution") == "configured" and damage_resolution.get("mode") == "threshold-raises":
            raw_ap = _resolve_template(directive.get("armorPiercing", 0), lookup)
            previous_wounds = _safe_int(_lookup_dotted(target_data, "wounds.value"))
            resolution = resolve_threshold_damage(target_data, amount, damage_resolution, actor_type=target["type"], armor_piercing=_safe_int(raw_ap))
            if resolution.wounds:
                target_data["_pendingDamage"] = {
                    "wounds": resolution.wounds,
                    "originalWounds": resolution.wounds,
                    "soaked": 0,
                    "damage": resolution.damage,
                    "sourceActorId": roll_result.actor_id,
                    "woundPenaltyIncrease": min(3, previous_wounds + resolution.wounds) - min(3, previous_wounds),
                }
            from app.config import config
            sync_condition_effects(target_data, self.rules.get_conditions(target["system_id"]), self.locales.get_locale(target["system_id"], config.default_locale))
            if is_unlinked:
                instance["data"] = target_data
                instance["version"] = int(instance.get("version", 1)) + 1
                overrides["_actor_instance"] = instance
                token_view = self._token_view(target, target_data, {"name": instance.get("name") or token.get("name") or target["name"]}, self.rules.get_derived(target["system_id"]), self.rules.get_helpers(target["system_id"]))
                if isinstance(token_view.get("bars"), dict): overrides.update(token_view["bars"])
                if isinstance(token_view.get("effects"), list): overrides["effects"] = token_view["effects"]
                updated = self.tokens.update_overrides(token_id=target_token_id, overrides=overrides)
                version = int(instance["version"]); token_version = updated["version"] if updated else token.get("version")
            else:
                version = int(envelope.get("version", 1)) + 1
                self.storage.write_actor(system_id=target["system_id"], campaign_id=target["campaign_id"], actor_id=target["id"], version=version, data=target_data)
                token_version = token.get("version")
            return replace(roll_result, applied={
                "targetActorId": target["id"], "targetTokenId": target_token_id,
                "targetName": token.get("name") or target["name"], "campaignId": target["campaign_id"],
                "sceneId": token["scene_id"], "systemId": target["system_id"],
                "mode": "threshold-damage", "rawAmount": amount,
                "toughness": resolution.toughness, "armor": resolution.armor,
                "armorPiercing": resolution.armor_piercing,
                "effectiveToughness": resolution.effective_toughness, "raises": resolution.raises,
                "wounds": resolution.wounds, "shaken": resolution.shaken,
                "incapacitated": resolution.incapacitated, "version": version,
                "tokenVersion": token_version,
            })
        resources = combat.get("resources") if isinstance(combat.get("resources"), dict) else {}

        if mode == "heal":
            damage_type = ""
            applied = amount
            resolved = resolve_resource_target("heal.self", resources)
            delta = applied
        else:
            raw_type = directive.get("damageType")
            damage_type = str(_resolve_template(raw_type, lookup) or "") if raw_type else ""
            applied = adjust_incoming_damage(target_data, amount, damage_type)
            resolved = resolve_resource_target("damage.self", resources)
            delta = -applied

        if resolved is None:
            return ActionResult(success=False, error_key="game.actions.errors.no_target_resource")
        value_path, max_path, floor = resolved
        value_after = apply_resource_delta(target_data, value_path, max_path, floor, delta)
        if value_after is None:
            return ActionResult(success=False, error_key="game.actions.errors.no_target_resource")

        if is_unlinked:
            instance["data"] = target_data
            instance["version"] = int(instance.get("version", 1)) + 1
            overrides["_actor_instance"] = instance
            token_view = self._token_view(
                target,
                target_data,
                {"name": instance.get("name") or token.get("name") or target["name"]},
                self.rules.get_derived(target["system_id"]),
                self.rules.get_helpers(target["system_id"]),
            )
            bars = token_view.get("bars")
            if isinstance(bars, dict):
                overrides.update(bars)
            effects = token_view.get("effects")
            if isinstance(effects, list):
                overrides["effects"] = effects
            updated = self.tokens.update_overrides(token_id=target_token_id, overrides=overrides)
            version = int(instance["version"])
            token_version = updated["version"] if updated else token.get("version")
        else:
            version = int(envelope.get("version", 1)) + 1
            self.storage.write_actor(
                system_id=target["system_id"],
                campaign_id=target["campaign_id"],
                actor_id=target["id"],
                version=version,
                data=target_data,
            )
            token_version = token.get("version")

        return replace(
            roll_result,
            applied={
                "targetActorId": target["id"],
                "targetTokenId": target_token_id,
                "targetName": token.get("name") or target["name"],
                "campaignId": target["campaign_id"],
                "sceneId": token["scene_id"],
                "systemId": target["system_id"],
                "mode": mode,
                "rawAmount": amount,
                "amount": applied,
                "damageType": damage_type,
                "resourcePath": value_path,
                "valueAfter": value_after,
                "version": version,
                "tokenVersion": token_version,
            },
        )

    def _do_patch(
        self, actor, action, data, context, scope, helpers, envelope, core, derived
    ) -> ActionResult:
        patch = action.get("patch")
        if not isinstance(patch, dict) or not patch:
            return ActionResult(success=False, error_key="game.actions.errors.invalid_patch")
        for path, declaration in patch.items():
            value_type = "number"
            expression = declaration
            if isinstance(declaration, dict):
                expression = declaration.get("expression")
                value_type = str(declaration.get("valueType") or "number")
            if not isinstance(expression, str):
                continue
            try:
                value = evaluate(expression, context=context, scope=scope, helpers=helpers).total
            except FormulaError:
                return ActionResult(success=False, error_key="game.actions.errors.invalid_formula")
            numeric = bool(value) if value_type == "boolean" else (int(value) if float(value).is_integer() else value)
            target = path[len("sheet.") :] if path.startswith("sheet.") else path
            _set_path(data, target, numeric)

        if any(str(path).removeprefix("sheet.").startswith("conditions.") for path in patch):
            from app.config import config
            sync_condition_effects(
                data,
                self.rules.get_conditions(actor["system_id"]),
                self.locales.get_locale(actor["system_id"], config.default_locale),
            )

        version = int(envelope.get("version", 1)) + 1
        self.storage.write_actor(
            system_id=actor["system_id"],
            campaign_id=actor["campaign_id"],
            actor_id=actor["id"],
            version=version,
            data=data,
        )
        return self._mutation_result(
            actor, action, data, version, sorted(patch.keys()), core, derived, helpers
        )

    def _do_append(
        self, actor, action, data, context, scope, envelope, core, derived, helpers
    ) -> ActionResult:
        target = action.get("target")
        if not isinstance(target, str) or not target:
            return ActionResult(success=False, error_key="game.actions.errors.invalid_target")
        lookup = {
            **context,
            "input": scope.get("input", {}),
            "drop": scope.get("drop", {}),
            "id": {"uuid": f"actor_item_{uuid4().hex[:12]}"},
        }
        value = _resolve_template(action.get("value"), lookup)
        if isinstance(value, dict) and not value.get("id"):
            value = {"id": f"actor_item_{uuid4().hex[:12]}", **value}
        target_key = target[len("sheet.") :] if target.startswith("sheet.") else target
        current = _get_path(data, target_key)
        items = list(current) if isinstance(current, list) else []
        items.append(value)
        _set_path(data, target_key, items)

        version = int(envelope.get("version", 1)) + 1
        self.storage.write_actor(
            system_id=actor["system_id"],
            campaign_id=actor["campaign_id"],
            actor_id=actor["id"],
            version=version,
            data=data,
        )
        return self._mutation_result(actor, action, data, version, [target], core, derived, helpers)

    def _mutation_result(
        self, actor, action, data, version, changed_paths, core, derived, helpers
    ) -> ActionResult:
        token_view = self._token_view(actor, data, core, derived, helpers)
        return ActionResult(
            success=True,
            actor_id=actor["id"],
            campaign_id=actor["campaign_id"],
            system_id=actor["system_id"],
            actor_name=actor["name"],
            action_type=action.get("type"),
            label=action.get("label"),
            version=version,
            changed_paths=changed_paths,
            token_view=token_view,
        )

    def _token_view(self, actor, data, core, derived, helpers) -> dict:
        mappings = self.rules.get_token_mappings(actor["system_id"])
        if not mappings:
            return {}
        derived_data = apply_derived(
            actor_type=actor["type"], data=data, derived_rules=derived, helpers=helpers, core=core
        )
        return resolve_token_view(
            actor_type=actor["type"], sheet_data=derived_data, core=core, token_mappings=mappings
        )

    def _load(self, actor_id: str, user_id: str) -> _LoadCtx:
        actor = self.actors.get(actor_id)
        if actor is None or actor["status"] != "active":
            return _LoadCtx(
                error=ActionResult(success=False, error_key="game.actors.errors.not_found")
            )
        campaign = self.campaigns.get_for_user(campaign_id=actor["campaign_id"], user_id=user_id)
        if campaign is None:
            return _LoadCtx(
                error=ActionResult(success=False, error_key="game.actors.errors.not_found")
            )
        if self.systems.get_active_manifest(actor["system_id"]) is None:
            return _LoadCtx(
                error=ActionResult(success=False, error_key="game.actors.errors.system_not_enabled")
            )
        return _LoadCtx(actor=actor, campaign=dict(campaign))


@dataclass
class _LoadCtx:
    actor: dict | None = None
    campaign: dict | None = None
    error: ActionResult | None = None


def _set_path(data: dict, dotted: str, value: Any) -> None:
    segments = [segment for segment in dotted.split(".") if segment]
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


def _get_path(data: dict, dotted: str) -> Any:
    cursor: Any = data
    for segment in dotted.split("."):
        if isinstance(cursor, dict):
            cursor = cursor.get(segment)
        else:
            return None
    return cursor
