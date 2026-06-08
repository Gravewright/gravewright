"""Derives a compact TokenView from a system's token mappings (§12).

    Actor Core + Sheet Data + token mappings  ->  TokenView

Mapping values are dotted paths (``core.name``, ``sheet.hp.value``) resolved
against the actor context. The caller should apply derived fields to the sheet
data first so mapped derived values (initiative, defense) resolve. The mapping
structure is preserved (e.g. ``bars.hp.{value,max}``).
"""

from __future__ import annotations

from typing import Any


def _resolve_path(context: dict, dotted: str) -> Any:
    cursor: Any = context
    for segment in dotted.split("."):
        if isinstance(cursor, dict):
            cursor = cursor.get(segment)
        else:
            return None
    return cursor


def _resolve(node: Any, context: dict) -> Any:
    if isinstance(node, dict):
        return {key: _resolve(value, context) for key, value in node.items()}
    if isinstance(node, str):
        return _resolve_path(context, node)
    return node


def resolve_token_view(
    *,
    actor_type: str,
    sheet_data: dict,
    core: dict,
    token_mappings: dict,
) -> dict:
    mapping = token_mappings.get(actor_type)
    if not isinstance(mapping, dict):
        return {}
    context = {"core": core or {}, "sheet": sheet_data or {}, "item": {}}
    return _resolve(mapping, context)
