"""Turns a system's declared conditions into Active Effect instances.

A ruleset declares its conditions once (``rules/conditions.gw.json``) and the
sheet stores each as a boolean under ``sheet.conditions.<id>``. On its own that
flag is inert: it colours a checkbox and nothing else.

This module is the bridge to the machinery that already exists for effects.
Ticking a condition writes a real entry into ``sheet.effects`` — the same list
a dropped Active Effect item lands in — so a condition immediately gets, for
free, everything an effect already has:

* :mod:`app.engine.effects.active_effects` applies its ``modifiers`` to rolls
  and to derived stats,
* :class:`ActorTokenProjector` publishes it to the board's effects HUD,
* the tooltip on that HUD lists what it is doing and why.

Entries are rebuilt from the flags on every write and tagged with
``source: "condition"``. Rebuilding rather than patching is what keeps the two
representations from drifting: the flags are the truth, the effects are their
projection. Anything in ``sheet.effects`` without that tag is somebody else's —
a dropped effect item, a GM-authored buff — and is never touched.
"""

from __future__ import annotations

from typing import Any

SOURCE = "condition"
MAX_CONDITIONS = 64


def _is_ours(effect: object) -> bool:
    if not isinstance(effect, dict):
        return False
    payload = effect.get("data") if isinstance(effect.get("data"), dict) else {}
    return payload.get("source") == SOURCE or effect.get("source") == SOURCE


def _instance(condition: dict, labels: dict[str, str]) -> dict:
    label_key = str(condition.get("labelKey") or "")
    name = labels.get(label_key) or label_key or condition["id"]
    modifiers = []
    for modifier in condition.get("modifiers") or []:
        resolved = dict(modifier)


        modifier_key = str(resolved.pop("labelKey", "") or "")
        resolved.setdefault("label", labels.get(modifier_key) or modifier_key or name)
        modifiers.append(resolved)
    return {


        "id": f"{SOURCE}:{condition['id']}",
        "name": name,
        "img": "",
        "data": {
            "source": SOURCE,
            "conditionId": condition["id"],
            "category": str(condition.get("category") or "condition"),
            "kind": condition.get("kind") or "neutral",
            "duration": {"type": "permanent"},
            "modifiers": modifiers,
        },
    }


def sync_condition_effects(
    sheet_data: dict, declared: list[dict], labels: dict[str, str] | None = None
) -> bool:
    """Rebuild the condition-sourced entries of ``sheet_data['effects']``.

    Mutates ``sheet_data`` in place. Returns whether anything actually changed,
    so a caller can skip persisting a write that would be a no-op.
    """
    if not isinstance(sheet_data, dict) or not declared:
        return False

    flags = sheet_data.get("conditions")
    flags = flags if isinstance(flags, dict) else {}
    labels = labels if isinstance(labels, dict) else {}

    existing = sheet_data.get("effects")
    existing = existing if isinstance(existing, list) else []



    wanted: list[dict] = [
        _instance(condition, labels)
        for condition in declared[:MAX_CONDITIONS]
        if flags.get(condition["id"])
    ]

    kept: list[Any] = [effect for effect in existing if not _is_ours(effect)]
    current: list[Any] = [effect for effect in existing if _is_ours(effect)]
    if current == wanted:
        return False

    sheet_data["effects"] = kept + wanted
    return True
