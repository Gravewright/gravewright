"""Runtime helpers for Active Effect instances stored in ``sheet.effects``.

Effect items are system-authored or GM-authored templates. Once dropped on an
actor sheet they become Active Effect instances. This module is the shared
runtime layer that turns their semantic ``data.modifiers[]`` into concrete
sheet/roll effects without exposing JSON editing to players.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any
import re

from app.engine.rules import formula_engine


_DICE_RE = re.compile(r"^[1-9][0-9]?d[1-9][0-9]{0,2}$")

                                                                                 
                                                                                
                                                                           
_GRANTING_COLLECTIONS = ("inventory", "features", "weapons")
_D20_RE = re.compile(r"(?<![A-Za-z0-9_])1d20(?![A-Za-z0-9_])", re.IGNORECASE)

                                                                           
                                                                               
                   
_STAT_TARGET_PATHS = {
    "stat.ac": "ac",
    "stat.armor_class": "ac",
    "stat.speed": "speed",
    "stat.hp.max": "hp.max",
    "stat.hp_max": "hp.max",
    "stat.initiative": "initiative",
    "stat.prof": "prof",
    "stat.proficiency": "prof",
    "stat.spell.dc": "spell.dc",
    "stat.spell.attack": "spell.attack",
}


def active_effects(sheet_data: dict) -> list[dict]:
    """Return enabled manual Active Effect instances from ``sheet.effects``."""
    effects = sheet_data.get("effects") if isinstance(sheet_data, dict) else []
    if not isinstance(effects, list):
        return []
    return [effect for effect in effects[:128] if isinstance(effect, dict) and effect.get("enabled") is not False]


def granted_effects(sheet_data: dict) -> list[dict]:
    """Effect instances contributed by carried items (see ``_GRANTING_COLLECTIONS``).

    An item contributes only if it carries modifiers and is either always-on (no
    ``equipped`` flag) or currently equipped. Items without modifiers are ignored.
    """
    if not isinstance(sheet_data, dict):
        return []
    out: list[dict] = []
    for collection in _GRANTING_COLLECTIONS:
        items = sheet_data.get(collection)
        if not isinstance(items, list):
            continue
        for item in items[:128]:
            if not isinstance(item, dict):
                continue
            if "equipped" in item and not item.get("equipped"):
                continue
            payload = item.get("data") if isinstance(item.get("data"), dict) else {}
            mods = payload.get("modifiers")
            if isinstance(mods, list) and mods:
                out.append(item)
    return out


def all_effects(sheet_data: dict) -> list[dict]:
    """Enabled manual effects followed by item-granted effects."""
    return active_effects(sheet_data) + granted_effects(sheet_data)


def _effective_effects(sheet_data: dict) -> list[dict]:
    """``all_effects`` minus any whose optional ``data.condition`` evaluates false."""
    result: list[dict] = []
    for effect in all_effects(sheet_data):
        payload = effect.get("data") if isinstance(effect.get("data"), dict) else {}
        condition = payload.get("condition")
        if isinstance(condition, str) and condition.strip() and not _condition_passes(condition, sheet_data):
            continue
        result.append(effect)
    return result


def _condition_passes(expression: str, sheet_data: dict) -> bool:
    try:
        result = formula_engine.evaluate(expression, context={"sheet": sheet_data})
    except formula_engine.FormulaError:
        return False
    return bool(result.total)


def effect_modifiers(sheet_data: dict, targets: set[str]) -> tuple[list[dict], list[dict]]:
    """Collect modifiers whose target applies to any of ``targets``.

    Matching is prefix-aware so a generic modifier like ``roll.save`` applies to
    a more specific roll target such as ``roll.save.dex`` while a specific
    modifier only applies when the action exposes that specific target.
    """
    if not isinstance(targets, set):
        targets = set(targets or [])
    modifiers: list[dict] = []
    applied: list[dict] = []
    for effect in _effective_effects(sheet_data):
        payload = effect.get("data") if isinstance(effect.get("data"), dict) else {}
        raw_mods = payload.get("modifiers") or effect.get("modifiers") or []
        if not isinstance(raw_mods, list):
            continue
        for mod in raw_mods[:32]:
            if not isinstance(mod, dict):
                continue
            target = str(mod.get("target") or "").strip()
            if not target or not _target_matches(target, targets):
                continue
            normalized = {
                "effectId": str(effect.get("id") or ""),
                "effectName": str(effect.get("name") or payload.get("name") or "Effect"),
                "label": str(mod.get("label") or effect.get("name") or "Effect"),
                "target": target,
                "operation": str(mod.get("operation") or ""),
                "value": mod.get("value"),
            }
            modifiers.append(mod)
            applied.append(normalized)
    return modifiers, applied


def apply_roll_modifiers(formula: str, modifiers: list[dict]) -> str:
    """Apply Active Effect roll modifiers to a formula string."""
    next_formula = formula
    for mod in modifiers[:32]:
        operation = str(mod.get("operation") or "").strip()
        value = mod.get("value")
        if operation in {"add", "add_dice"}:
            next_formula = append_formula_part(next_formula, value, user_supplied=False)
        elif operation == "subtract":
            if isinstance(value, (int, float)):
                next_formula = append_formula_part(next_formula, -int(value), user_supplied=False)
            elif value not in (None, ""):
                text = str(value).strip()
                if text:
                    next_formula = f"{next_formula} - {text}"
        elif operation == "advantage":
            next_formula = _D20_RE.sub("2d20kh1", next_formula, count=1)
        elif operation == "disadvantage":
            next_formula = _D20_RE.sub("2d20kl1", next_formula, count=1)
    return next_formula


def apply_stat_modifiers(sheet_data: dict) -> dict:
    """Return a derived-data copy with stat/sheet Active Effects applied.

    This is intentionally non-persistent. It gives open sheets, token projection,
    and action contexts the effective values while keeping the user's base sheet
    data untouched.
    """
    if not isinstance(sheet_data, dict):
        return {}
    effective = deepcopy(sheet_data)
    for effect in _effective_effects(sheet_data):
        payload = effect.get("data") if isinstance(effect.get("data"), dict) else {}
        raw_mods = payload.get("modifiers") or effect.get("modifiers") or []
        if not isinstance(raw_mods, list):
            continue
        for mod in raw_mods[:32]:
            if not isinstance(mod, dict):
                continue
            target = str(mod.get("target") or "").strip()
            path = _stat_target_path(target)
            if not path:
                continue
            _apply_stat_modifier(effective, path, mod)
    return effective


def damage_adjustments(sheet_data: dict, damage_type: str = "") -> list[dict]:
    """Return enabled ``damage.received`` modifiers matching ``damage_type``.

    Includes both generic (``damage.received``) and type-specific
    (``damage.received.<type>``) resistance/vulnerability/immunity/reduce
    modifiers. :func:`adjust_incoming_damage` applies them.
    """
    targets = {"damage.received"}
    if damage_type:
        targets.add(f"damage.received.{str(damage_type).lower()}")
    _, applied = effect_modifiers(sheet_data, targets)
    return [item for item in applied if str(item.get("operation") or "") in {"resistance", "vulnerability", "immunity", "reduce"}]


def adjust_incoming_damage(sheet_data: dict, amount: int, damage_type: str = "") -> int:
    """Apply the actor's damage adjustments to an incoming ``amount``.

    Order mirrors tabletop resolution: immunity zeroes the damage; otherwise flat
    ``reduce`` values come off first, then ``resistance`` halves (round down) and
    ``vulnerability`` doubles. Returns the adjusted, non-negative amount.
    """
    try:
        amount = max(0, int(amount))
    except (TypeError, ValueError):
        return 0
    if amount == 0:
        return 0

    adjustments = damage_adjustments(sheet_data, damage_type)
    operations = {str(item.get("operation") or "") for item in adjustments}
    if "immunity" in operations:
        return 0

    for item in adjustments:
        if str(item.get("operation") or "") != "reduce":
            continue
        try:
            amount -= max(0, int(item.get("value") or 0))
        except (TypeError, ValueError):
            continue
    amount = max(0, amount)
    if "resistance" in operations:
        amount //= 2
    if "vulnerability" in operations:
        amount *= 2
    return max(0, amount)


def periodic_modifiers(sheet_data: dict, *, roller: Any = None) -> list[dict]:
    """Roll each active ``damage_over_time`` / ``heal_over_time`` modifier once.

    These are the recurring effects ticked by the combat round loop (poison,
    bleed, regeneration, …). Each returned entry carries the rolled integer
    ``amount`` and a signed ``delta`` to apply to ``hp.value`` (negative for
    damage). Pure: it rolls dice but does not mutate ``sheet_data``; the caller
    persists the result via :func:`apply_hp_delta`.
    """
    out: list[dict] = []
    for effect in _effective_effects(sheet_data):
        payload = effect.get("data") if isinstance(effect.get("data"), dict) else {}
        raw_mods = payload.get("modifiers") or effect.get("modifiers") or []
        if not isinstance(raw_mods, list):
            continue
        for mod in raw_mods[:32]:
            if not isinstance(mod, dict):
                continue
            operation = str(mod.get("operation") or "").strip()
            if operation not in {"damage_over_time", "heal_over_time"}:
                continue
            rolled = _roll_amount(mod.get("value"), roller)
            if rolled <= 0:
                continue
            damage_type = str(mod.get("damageType") or mod.get("damage_type") or "")
                                                                                  
                                                   
            amount = (
                adjust_incoming_damage(sheet_data, rolled, damage_type)
                if operation == "damage_over_time"
                else rolled
            )
            if amount <= 0:
                continue
            out.append(
                {
                    "effectId": str(effect.get("id") or ""),
                    "effectName": str(effect.get("name") or payload.get("name") or "Effect"),
                    "label": str(mod.get("label") or effect.get("name") or "Effect"),
                    "operation": operation,
                    "target": str(mod.get("target") or "").strip(),
                    "damageType": damage_type,
                    "amount": amount,
                    "rawAmount": rolled,
                    "delta": -amount if operation == "damage_over_time" else amount,
                }
            )
    return out


                                                                       
_SELF_RESOURCE_TARGETS = {"", "damage.self", "heal.self", "self"}


def resolve_resource_target(target: str, resources: dict | None) -> tuple[str, str, int] | None:
    """Map a periodic modifier ``target`` to ``(value_path, max_path, floor)``.

    Paths are relative to the sheet-data root (the ``sheet`` namespace), so any
    leading ``sheet.`` is stripped. Resolution is system-agnostic:

    * ``sheet.<path>``   → that explicit path (``max`` inferred from a ``.value`` →
      ``.max`` sibling at apply time; floor ``0``).
    * ``resource.<id>``  → the named resource from the system's combat
      ``resources`` config (its ``path`` / ``maxPath`` / ``min``).
    * neutral (``damage.self`` / ``heal.self`` / ``self`` / empty) → the system's
      primary configured resource, falling back to ``hp.value`` when none is
      declared so simple systems still work out of the box.

    Returns ``None`` when a named resource id cannot be resolved.
    """
    target = (target or "").strip()
    resources = resources if isinstance(resources, dict) else {}

    if target.startswith("sheet."):
        return _strip_sheet(target), "", 0
    if target.startswith("resource."):
        entry = resources.get(target[len("resource.") :])
        return _resource_paths(entry) if isinstance(entry, dict) else None
    if target in _SELF_RESOURCE_TARGETS:
        primary = next((value for value in resources.values() if isinstance(value, dict)), None)
        return _resource_paths(primary) if primary is not None else ("hp.value", "hp.max", 0)
    return None


def apply_resource_delta(
    sheet_data: dict, value_path: str, max_path: str, floor: int, delta: int
) -> int | None:
    """Apply ``delta`` to ``value_path`` clamped to ``[floor, max]`` in place.

    ``max`` comes from ``max_path`` when given, otherwise from a ``.value`` →
    ``.max`` sibling of ``value_path``. Returns the resulting value, or ``None``
    when ``value_path`` is empty / unwritable.
    """
    if not isinstance(sheet_data, dict) or not value_path:
        return None
    try:
        current = int(_get_path(sheet_data, value_path))
    except (TypeError, ValueError):
        current = 0
    new_value = current + int(delta)
    if new_value < int(floor):
        new_value = int(floor)
    cap = _resolve_max(sheet_data, value_path, max_path)
    if cap is not None and new_value > cap:
        new_value = cap
    _set_path(sheet_data, value_path, new_value)
    return new_value


def _resource_paths(entry: dict) -> tuple[str, str, int]:
    value_path = _strip_sheet(str(entry.get("path") or "hp.value"))
    max_path = _strip_sheet(str(entry.get("maxPath") or ""))
    try:
        floor = int(entry.get("min", 0))
    except (TypeError, ValueError):
        floor = 0
    return value_path, max_path, floor


def _strip_sheet(path: str) -> str:
    return path[len("sheet.") :] if path.startswith("sheet.") else path


def _resolve_max(sheet_data: dict, value_path: str, max_path: str) -> int | None:
    raw: Any = None
    if max_path:
        raw = _get_path(sheet_data, max_path)
    elif value_path.endswith(".value"):
        raw = _get_path(sheet_data, value_path[: -len(".value")] + ".max")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return None
    return int(raw)


def _roll_amount(value: Any, roller: Any = None) -> int:
    """Resolve a dice/number modifier value to a non-negative integer for one tick."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    if not isinstance(value, str) or not value.strip():
        return 0
    try:
        result = formula_engine.evaluate(value.strip(), roller=roller)
    except formula_engine.FormulaError:
        return 0
    return max(0, int(result.total))


def append_formula_part(formula: str, value: Any, *, user_supplied: bool = False) -> str:
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


def _target_matches(modifier_target: str, runtime_targets: set[str]) -> bool:
    for target in runtime_targets:
        if modifier_target == target:
            return True
        if target.startswith(f"{modifier_target}."):
            return True
    return False


def _stat_target_path(target: str) -> str:
    if target.startswith("sheet."):
        return target[len("sheet.") :]
    return _STAT_TARGET_PATHS.get(target, "")


def _apply_stat_modifier(data: dict, dotted_path: str, modifier: dict) -> None:
    operation = str(modifier.get("operation") or "").strip()
    value = modifier.get("value")
    if operation not in {"add", "subtract", "set"}:
        return
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return
    current = _get_path(data, dotted_path)
    try:
        current_number = int(current)
    except (TypeError, ValueError):
        current_number = 0
    if operation == "set":
        next_value = numeric
    elif operation == "subtract":
        next_value = current_number - numeric
    else:
        next_value = current_number + numeric
    _set_path(data, dotted_path, next_value)


def _get_path(data: dict, dotted: str) -> Any:
    cursor: Any = data
    for segment in dotted.split("."):
        if not segment:
            continue
        if isinstance(cursor, dict):
            cursor = cursor.get(segment)
        else:
            return None
    return cursor


def _set_path(data: dict, dotted: str, value: Any) -> None:
    segments = [segment for segment in dotted.split(".") if segment]
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
