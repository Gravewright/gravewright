from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ThresholdDamageResult:
    damage: int
    toughness: int
    armor: int
    armor_piercing: int
    effective_toughness: int
    raises: int
    wounds: int
    shaken: bool
    incapacitated: bool


def _read(data: dict, dotted: str, default: Any = None) -> Any:
    cursor: Any = data
    for segment in dotted.split("."):
        if not isinstance(cursor, dict):
            return default
        cursor = cursor.get(segment)
    return default if cursor is None else cursor


def _write(data: dict, dotted: str, value: Any) -> None:
    cursor = data
    parts = dotted.split(".")
    for segment in parts[:-1]:
        cursor = cursor.setdefault(segment, {})
    cursor[parts[-1]] = value


def resolve_threshold_damage(
    data: dict, damage: int, policy: dict, *, actor_type: str, armor_piercing: int = 0
) -> ThresholdDamageResult:
    toughness_path = str(policy.get("thresholdPath") or "stats.toughness.value")
    shaken_path = str(policy.get("shakenPath") or "conditions.shaken")
    wounds_path = str(policy.get("woundsPath") or "wounds.value")
    max_wounds_path = str(policy.get("maxWoundsPath") or "wounds.max")
    incapacitated_path = str(policy.get("incapacitatedPath") or "conditions.incapacitated")
    armor_path = str(policy.get("armorPath") or "stats.toughness.armor")
    step = max(1, int(policy.get("raiseStep") or 4))
    toughness = max(0, int(_read(data, toughness_path, 0) or 0))
    armor = max(0, int(_read(data, armor_path, 0) or 0))
    applied_ap = min(armor, max(0, int(armor_piercing)))
    effective_toughness = max(0, toughness - applied_ap)
    amount = max(0, int(damage))
    was_shaken = bool(_read(data, shaken_path, False))
    margin = amount - effective_toughness
    raises = max(0, margin // step) if margin >= 0 else 0
    wounds = raises + (1 if margin >= 0 and was_shaken else 0)
    shaken = was_shaken
    if margin >= 0:
        shaken = True
        _write(data, shaken_path, True)
    current_wounds = max(0, int(_read(data, wounds_path, 0) or 0))
    next_wounds = current_wounds + wounds
    if wounds:
        _write(data, wounds_path, next_wounds)
    extra_types = {str(value) for value in policy.get("extraActorTypes", ["extra"])}
    max_wounds = max(0, int(_read(data, max_wounds_path, 0) or 0))
    incapacitated = bool(_read(data, incapacitated_path, False))
    if wounds and (actor_type in extra_types or next_wounds > max_wounds):
        incapacitated = True
        _write(data, incapacitated_path, True)
    return ThresholdDamageResult(
        amount, toughness, armor, applied_ap, effective_toughness,
        raises, wounds, shaken, incapacitated,
    )
