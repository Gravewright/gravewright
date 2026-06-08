"""Pure helpers that enforce a system's declared schema + validation on writes.

Sheet Data is stored as the ``sheet`` namespace (no ``sheet.`` prefix), e.g. the
patch key ``hp.value`` writes ``data["hp"]["value"]``. The JSON Schema
(``*.schema.json``) describes those same paths under ``properties``; the
``rules/validation`` map keys them with a leading ``sheet.`` which we normalize
away here.

Everything is tolerant: a system without a schema/validation behaves exactly as
before (writes pass through untouched). Unknown paths (e.g. into array items) are
allowed — only explicit ``readOnly`` leaves are rejected, and only declared
``min``/``max`` bounds clamp.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


                                                                                


def apply_schema_defaults(schema: dict | None) -> dict:
    """Build the initial Sheet Data tree from a JSON Schema's ``default`` values."""
    if not isinstance(schema, dict):
        return {}
    props = schema.get("properties")
    if not isinstance(props, dict):
        return {}
    out: dict[str, Any] = {}
    for key, child in props.items():
        has, value = _node_default(child)
        if has:
            out[key] = value
    return out


def _node_default(node: object) -> tuple[bool, Any]:
    if not isinstance(node, dict):
        return False, None
    if "default" in node:
        return True, deepcopy(node["default"])
    if node.get("type") == "object" and isinstance(node.get("properties"), dict):
        nested: dict[str, Any] = {}
        for key, child in node["properties"].items():
            has, value = _node_default(child)
            if has:
                nested[key] = value
        if nested:
            return True, nested
    return False, None


def merge_defaults(defaults: dict, data: dict) -> dict:
    """Deep-merge ``data`` over ``defaults`` (data wins); used on full replaces/imports."""
    if not isinstance(defaults, dict):
        return deepcopy(data) if isinstance(data, dict) else {}
    if not isinstance(data, dict):
        return deepcopy(defaults)
    out = deepcopy(defaults)
    for key, value in data.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = merge_defaults(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


                                                                                


def sanitize_write(
    schema: dict | None, validation: dict | None, patch: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Coerce types, drop ``readOnly`` paths, and clamp ``min``/``max``.

    Returns ``(clean_patch, rejected_paths)``. ``clean_patch`` only contains the
    paths that are safe to write, with values already coerced/clamped.
    """
    constraints_by_path = _normalize_validation(validation)
    clean: dict[str, Any] = {}
    rejected: list[str] = []

    for path, value in patch.items():
        node = _schema_node_for_path(schema, str(path))

        if isinstance(node, dict) and node.get("readOnly") is True:
            rejected.append(str(path))
            continue

        coerced = _coerce(node.get("type") if isinstance(node, dict) else None, value)
        if coerced is _INVALID:
            rejected.append(str(path))
            continue

        bounds = constraints_by_path.get(str(path))
        if (
            bounds is not None
            and isinstance(coerced, (int, float))
            and not isinstance(coerced, bool)
        ):
            coerced = _clamp(coerced, bounds)

        clean[str(path)] = coerced

    return clean, rejected


_INVALID = object()


def _coerce(declared_type: object, value: Any) -> Any:
    """Best-effort coercion to the declared scalar type; ``_INVALID`` to reject."""
    if declared_type in ("number", "integer"):
        if isinstance(value, bool):
            return _INVALID
        if isinstance(value, (int, float)):
            return int(value) if declared_type == "integer" else value
        if isinstance(value, str):
            text = value.strip()
            try:
                number = float(text)
            except ValueError:
                return _INVALID
            return int(number) if declared_type == "integer" else number
        return _INVALID
    if declared_type == "string":
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value)
        return _INVALID
                                                                 
    return value


def _clamp(value: int | float, bounds: dict) -> int | float:
    low = bounds.get("min")
    high = bounds.get("max")
    if isinstance(low, (int, float)) and not isinstance(low, bool) and value < low:
        value = low
    if isinstance(high, (int, float)) and not isinstance(high, bool) and value > high:
        value = high
    return value


def _schema_node_for_path(schema: dict | None, dotted: str) -> dict | None:
    """Resolve a dotted Sheet Data path to its schema node (None if undeclared)."""
    node: Any = schema
    for segment in dotted.split("."):
        if not segment:
            continue
        if not isinstance(node, dict):
            return None
        props = node.get("properties")
        if not isinstance(props, dict) or segment not in props:
            return None
        node = props[segment]
    return node if isinstance(node, dict) else None


def _normalize_validation(validation: dict | None) -> dict[str, dict]:
    """Strip the leading ``sheet.`` so keys match stored Sheet Data paths."""
    if not isinstance(validation, dict):
        return {}
    out: dict[str, dict] = {}
    for key, bounds in validation.items():
        if not isinstance(bounds, dict):
            continue
        normalized = key[len("sheet.") :] if str(key).startswith("sheet.") else str(key)
        out[normalized] = bounds
    return out
