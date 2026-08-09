"""Derives a compact TokenView from a system's token mappings (§12).

    Actor Core + Sheet Data + token mappings  ->  TokenView

Mapping values are dotted paths (``core.name``, ``sheet.hp.value``) resolved
against the actor context. The caller should apply derived fields to the sheet
data first so mapped derived values (initiative, defense) resolve.

``bars`` is the one part with a fixed shape. A token draws exactly two bars —
``bar_1`` under it and ``bar_2`` above it — and the system decides what each one
reads. Their ``value``/``max`` are paths; ``color`` is a literal hex and is
never path-resolved.
"""

from __future__ import annotations

from typing import Any


BAR_SLOTS = ("bar_1", "bar_2")


DEFAULT_BAR_COLORS = {"bar_1": "#4caf50", "bar_2": "#3b82f6"}


LEGACY_BAR_ALIASES = {"hp": "bar_1", "health": "bar_1", "primary": "bar_1", "secondary": "bar_2"}

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


def _slot_for(key: str) -> str:
    key = str(key or "").strip().lower()
    if key in BAR_SLOTS:
        return key
    return LEGACY_BAR_ALIASES.get(key, "")


def resolve_bars(raw_bars: Any, context: dict) -> dict:
    """Resolve the declared bars into the two slots the token can draw.

    A slot with no readable ``value`` is dropped rather than drawn empty, so a
    system that only tracks one resource simply gets one bar.
    """
    if not isinstance(raw_bars, dict):
        return {}
    out: dict[str, dict] = {}
    for key, declared in raw_bars.items():
        slot = _slot_for(key)
        if not slot or slot in out or not isinstance(declared, dict):
            continue
        value = _resolve_path(context, str(declared.get("value") or ""))
        if value is None:
            continue
        max_path = str(declared.get("max") or "")
        maximum = _resolve_path(context, max_path) if max_path else None
        out[slot] = {
            "value": value,
            "max": maximum if maximum is not None else value,
            "color": _safe_color(declared.get("color")) or DEFAULT_BAR_COLORS[slot],
            "visibility": "everyone",
        }
    return out


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
    view = {key: _resolve(value, context) for key, value in mapping.items() if key != "bars"}
    view["bars"] = resolve_bars(mapping.get("bars"), context)
    return view


def _safe_color(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text.startswith("#"):
        return None
    hex_part = text[1:]
    if len(hex_part) not in {3, 6}:
        return None
    if not all(ch in "0123456789abcdefABCDEF" for ch in hex_part):
        return None
    return f"#{hex_part}"


__all__ = [
    "BAR_SLOTS",
    "DEFAULT_BAR_COLORS",
    "LEGACY_BAR_ALIASES",
    "resolve_bars",
    "resolve_token_view",
]
