"""Computes derived fields (§9.2).

Given an actor's stored data and the system's ``derived`` rules for that actor
type, evaluates each derived expression and writes the result back. Derived
fields may depend on each other, so we iterate to a fixed point (bounded).
Derived expressions are deterministic — they must not roll dice.
"""

from __future__ import annotations

import copy
from typing import Any

from app.engine.rules.formula_engine import FormulaError, evaluate

MAX_PASSES = 6


def _set_path(data: dict, dotted: str, value: Any) -> bool:
    segments = [segment for segment in dotted.split(".") if segment]
    if not segments:
        return False
    cursor = data
    for segment in segments[:-1]:
        nxt = cursor.get(segment)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[segment] = nxt
        cursor = nxt
    leaf = segments[-1]
    changed = cursor.get(leaf) != value
    cursor[leaf] = value
    return changed


def _numeric(value: float) -> Any:
    return int(value) if float(value).is_integer() else value


def apply_derived(
    *,
    actor_type: str,
    data: dict,
    derived_rules: dict,
    helpers: dict | None = None,
    core: dict | None = None,
) -> dict:
    type_rules = derived_rules.get(actor_type)
    if not isinstance(type_rules, dict) or not type_rules:
        return data

    working = copy.deepcopy(data) if isinstance(data, dict) else {}
    context = {"core": core or {}, "sheet": working, "item": {}}

    for _ in range(MAX_PASSES):
        changed = False
        for path, expression in type_rules.items():
            if not isinstance(expression, str):
                continue
            try:
                value = evaluate(expression, context=context, helpers=helpers or {}).total
            except FormulaError:
                continue
            target = path[len("sheet.") :] if path.startswith("sheet.") else path
            if _set_path(working, target, _numeric(value)):
                changed = True
        if not changed:
            break

    return working
