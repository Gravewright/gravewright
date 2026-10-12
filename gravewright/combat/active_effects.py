"""Bounded helpers for explicitly addressed, system-authored effect data.

The host does not assign meanings to stats, dice, equipment or damage. Systems
select their sources and translate their own rules into numeric operations and
explicit ``sheet.<path>`` / ``resource.<id>`` targets before using these helpers.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any
import math
import re

from . import formula_engine


_DICE_RE = re.compile(r"^[1-9][0-9]?d[1-9][0-9]{0,2}$")


_EFFECT_TARGET_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*(?:\.[A-Za-z0-9_-]+)+$")
_PATH_RE = re.compile(r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$")


def active_effects(sheet_data: dict, *, path: str = "effects") -> list[dict]:
    """Select enabled entries from a caller-selected collection path."""
    effects = _get_path(sheet_data, path) if isinstance(sheet_data, dict) else []
    if not isinstance(effects, list):
        return []
    active: list[dict] = []
    for effect in effects[:128]:
        if not isinstance(effect, dict) or effect.get("enabled") is False:
            continue
        payload = effect.get("data") if isinstance(effect.get("data"), dict) else {}
        if payload.get("enabled") is False:
            continue
        active.append(effect)
    return active


def granted_effects(sheet_data: dict, *, collections, eligible=None) -> list[dict]:
    """Select modifier sources from explicit collection paths.

    Equipment, ownership and activation rules belong to ``eligible`` supplied by
    the system. A field named ``equipped`` has no intrinsic meaning here.
    """
    if not isinstance(sheet_data, dict):
        return []
    out: list[dict] = []
    for collection in tuple(collections)[:32]:
        items = _get_path(sheet_data, collection)
        if not isinstance(items, list):
            continue
        for item in items[:128]:
            if not isinstance(item, dict):
                continue
            payload = item.get("data") if isinstance(item.get("data"), dict) else {}
            if item.get("enabled") is False or payload.get("enabled") is False:
                continue
            if eligible is not None and not eligible(item):
                continue
            mods = payload.get("modifiers")
            if isinstance(mods, list) and mods:
                out.append(item)
    return out


def all_effects(sheet_data: dict, *, path="effects", collections=(), eligible=None) -> list[dict]:
    """Select sources without assuming a system's collection or equipment schema."""
    return active_effects(sheet_data, path=path) + granted_effects(
        sheet_data, collections=collections, eligible=eligible,
    )


def _effective_effects(sheet_data: dict, effects=None) -> list[dict]:
    """Filter the selected sources by their optional declarative expression."""
    result: list[dict] = []
    for effect in (active_effects(sheet_data) if effects is None else effects)[:128]:
        if not isinstance(effect, dict) or effect.get("enabled") is False:
            continue
        payload = effect.get("data") if isinstance(effect.get("data"), dict) else {}
        if payload.get("enabled") is False:
            continue
        condition = payload.get("condition")
        if (
            isinstance(condition, str)
            and condition.strip()
            and not _condition_passes(condition, sheet_data)
        ):
            continue
        result.append(effect)
    return result


def _condition_passes(expression: str, sheet_data: dict) -> bool:
    try:
        result = formula_engine.evaluate(expression, context={"sheet": sheet_data})
    except formula_engine.FormulaError:
        return False
    return bool(result.total)


def effect_modifiers(sheet_data: dict, targets: set[str], *, effects=None) -> tuple[list[dict], list[dict]]:
    """Collect modifiers whose target applies to any of ``targets``.

    Matching is prefix-aware: ``sensor.scan`` matches ``sensor.scan.remote``.
    Targets are opaque identifiers selected by the calling system.
    """
    if not isinstance(targets, set):
        targets = set(targets or [])
    modifiers: list[dict] = []
    applied: list[dict] = []
    for effect in _effective_effects(sheet_data, effects):
        payload = effect.get("data") if isinstance(effect.get("data"), dict) else {}
        raw_mods = payload.get("modifiers") or effect.get("modifiers") or []
        if not isinstance(raw_mods, list):
            continue
        for mod in raw_mods[:32]:
            if not isinstance(mod, dict):
                continue
            target = str(mod.get("target") or "").strip()
            if not _EFFECT_TARGET_RE.fullmatch(target) or not _target_matches(target, targets):
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


def effect_restrictions(sheet_data: dict, target: str, *, effects=None) -> list[dict]:
    """Return active declarative restrictions matching a semantic target."""
    normalized_target = str(target or "").strip()
    if not _EFFECT_TARGET_RE.fullmatch(normalized_target):
        return []
    matched: list[dict] = []
    for effect in _effective_effects(sheet_data, effects):
        payload = effect.get("data") if isinstance(effect.get("data"), dict) else {}
        restrictions = payload.get("restrictions") or effect.get("restrictions") or []
        if not isinstance(restrictions, list):
            continue
        for restriction in restrictions[:16]:
            if not isinstance(restriction, dict):
                continue
            restriction_target = str(restriction.get("target") or "").strip()
            if _EFFECT_TARGET_RE.fullmatch(restriction_target) and _target_matches(
                restriction_target, {normalized_target}
            ):
                matched.append(
                    {
                        **restriction,
                        "effectId": str(effect.get("id") or ""),
                        "effectName": str(effect.get("name") or payload.get("name") or "Effect"),
                    }
                )
    return matched


def apply_roll_modifiers(formula: str, modifiers: list[dict]) -> str:
    """Append explicit arithmetic; system-specific roll operations are ignored."""
    next_formula = formula
    for mod in modifiers[:32]:
        operation = str(mod.get("operation") or "").strip()
        value = mod.get("value")
        if operation in {"add", "add_dice"}:
            next_formula = append_formula_part(next_formula, value, user_supplied=False)
        elif operation == "subtract":
            if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
                next_formula = append_formula_part(next_formula, -int(value), user_supplied=False)
            elif value not in (None, ""):
                text = str(value).strip()
                if text:
                    next_formula = f"{next_formula} - {text}"
    return next_formula


def apply_stat_modifiers(sheet_data: dict, *, effects=None) -> dict:
    """Return a copy with modifiers on explicit ``sheet.<path>`` targets applied.

    This is intentionally non-persistent. It gives open sheets, token projection,
    and action contexts the effective values while keeping the user's base sheet
    data untouched.
    """
    if not isinstance(sheet_data, dict):
        return {}
    effective = deepcopy(sheet_data)
    for effect in _effective_effects(sheet_data, effects):
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


def periodic_modifiers(sheet_data: dict, *, roller: Any = None, effects=None) -> list[dict]:
    """Evaluate explicit signed ``resource_delta`` values without game semantics.

    Systems translate damage, healing or other rule terms themselves. This helper
    does not choose a resource, apply resistance or interpret a damage type.
    """
    out: list[dict] = []
    for effect in _effective_effects(sheet_data, effects):
        payload = effect.get("data") if isinstance(effect.get("data"), dict) else {}
        raw_mods = payload.get("modifiers") or effect.get("modifiers") or []
        if not isinstance(raw_mods, list):
            continue
        for mod in raw_mods[:32]:
            if not isinstance(mod, dict):
                continue
            operation = str(mod.get("operation") or "").strip()
            if operation != "resource_delta":
                continue
            rolled = _roll_amount(mod.get("value"), roller)
            if rolled == 0:
                continue
            out.append(
                {
                    "effectId": str(effect.get("id") or ""),
                    "effectName": str(effect.get("name") or payload.get("name") or "Effect"),
                    "label": str(mod.get("label") or effect.get("name") or "Effect"),
                    "operation": operation,
                    "target": str(mod.get("target") or "").strip(),
                    "amount": abs(rolled),
                    "rawAmount": rolled,
                    "delta": rolled,
                }
            )
    return out


def resolve_resource_target(target: str, resources: dict | None) -> tuple[str, str, int] | None:
    """Map a periodic modifier ``target`` to ``(value_path, max_path, floor)``.

    Paths are relative to the sheet-data root (the ``sheet`` namespace), so any
    leading ``sheet.`` is stripped. Resolution is system-agnostic:

    * ``sheet.<path>``   → that explicit path (no implicit cap; floor ``0``).
    * ``resource.<id>``  → the named resource from the system's combat
      ``resources`` config (its ``path`` / ``maxPath`` / ``min``).
    Returns ``None`` for undeclared resources and semantic/empty targets. A system
    that supports shorthand targets resolves those in its own provider.
    """
    target = (target or "").strip()
    resources = resources if isinstance(resources, dict) else {}

    if target.startswith("sheet."):
        path = _strip_sheet(target)
        return (path, "", 0) if _valid_path(path) else None
    if target.startswith("resource."):
        entry = resources.get(target[len("resource.") :])
        return _resource_paths(entry) if isinstance(entry, dict) else None
    return None


def apply_resource_delta(
    sheet_data: dict, value_path: str, max_path: str, floor: int, delta: int
) -> int | None:
    """Apply ``delta`` to ``value_path`` clamped to ``[floor, max]`` in place.

    A cap is used only when ``max_path`` is explicit. Returns the resulting value,
    or ``None`` for invalid paths/values. No particular field name means a limit.
    """
    if not isinstance(sheet_data, dict) or not _valid_path(value_path) or (max_path and not _valid_path(max_path)):
        return None
    if isinstance(delta, bool) or isinstance(floor, bool):
        return None
    try:
        delta, floor = int(delta), int(floor)
    except (TypeError, ValueError, OverflowError):
        return None
    try:
        raw = _get_path(sheet_data, value_path)
        current = int(raw) if not isinstance(raw, bool) else 0
    except (TypeError, ValueError, OverflowError):
        current = 0
    new_value = max(floor, current + delta)
    cap = _resolve_max(sheet_data, value_path, max_path)
    if cap is not None and new_value > cap:
        new_value = max(floor, cap)
    _set_path(sheet_data, value_path, new_value)
    return new_value


def _resource_paths(entry: dict) -> tuple[str, str, int] | None:
    value_path = _strip_sheet(str(entry.get("path") or ""))
    max_path = _strip_sheet(str(entry.get("maxPath") or ""))
    if not _valid_path(value_path) or (max_path and not _valid_path(max_path)):
        return None
    try:
        floor = int(entry.get("min", 0))
    except (TypeError, ValueError, OverflowError):
        floor = 0
    return value_path, max_path, floor


def _strip_sheet(path: str) -> str:
    return path[len("sheet.") :] if path.startswith("sheet.") else path


def _valid_path(path: str) -> bool:
    return isinstance(path, str) and len(path) <= 240 and bool(_PATH_RE.fullmatch(path)) and not any(
        segment in {"__proto__", "constructor", "prototype"} for segment in path.split(".")
    )


def _resolve_max(sheet_data: dict, value_path: str, max_path: str) -> int | None:
    raw: Any = None
    if max_path:
        raw = _get_path(sheet_data, max_path)
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
        return None
    return int(raw)


def _roll_amount(value: Any, roller: Any = None) -> int:
    """Resolve one explicitly signed arithmetic value for a tick."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return int(value) if math.isfinite(value) else 0
    if not isinstance(value, str) or not value.strip():
        return 0
    try:
        result = formula_engine.evaluate(value.strip(), roller=roller)
    except formula_engine.FormulaError:
        return 0
    return int(result.total) if math.isfinite(result.total) else 0


def append_formula_part(formula: str, value: Any, *, user_supplied: bool = False) -> str:
    if isinstance(value, bool) or value in (None, ""):
        return formula
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            return formula
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
        path = target[len("sheet.") :]
        return path if _valid_path(path) else ""
    return ""


def _apply_stat_modifier(data: dict, dotted_path: str, modifier: dict) -> None:
    operation = str(modifier.get("operation") or "").strip()
    value = modifier.get("value")
    if operation not in {"add", "subtract", "set"} or isinstance(value, bool):
        return
    try:
        numeric = int(value)
    except (TypeError, ValueError, OverflowError):
        return
    current = _get_path(data, dotted_path)
    try:
        current_number = int(current)
    except (TypeError, ValueError, OverflowError):
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
