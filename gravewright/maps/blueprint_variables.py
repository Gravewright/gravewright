"""Bounded, private variable values and named Blueprint signal contracts."""

from copy import deepcopy
import math
import re

from .services import MapError
from .blueprint_events import removed_event


VARIABLE_TYPES = ("boolean", "number", "text")
VARIABLE_SCOPES = ("element", "scene")
VALUE_OPERATORS = ("eq", "ne", "lt", "lte", "gt", "gte")
MAX_VARIABLES = 64
MAX_SIGNAL_GRAPHS = 16
_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}\Z")


def name(value):
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise MapError("Use a variable or signal name with 1 to 64 ASCII characters.")
    return value


def typed_value(value, value_type):
    valid = ((value_type == "boolean" and type(value) is bool)
             or (value_type == "number" and type(value) in (int, float)
                 and abs(value) <= 1_000_000 and math.isfinite(value))
             or (value_type == "text" and isinstance(value, str) and len(value) <= 256))
    if not valid:
        raise MapError("Invalid blueprint variable value.")
    return value


def clean_store(raw):
    if not isinstance(raw, dict) or len(raw) > MAX_VARIABLES:
        raise MapError("Invalid blueprint variable store.")
    result = {}
    for key, entry in raw.items():
        name(key)
        if not isinstance(entry, dict) or set(entry) != {"type", "value"}:
            raise MapError("Invalid blueprint variable store.")
        result[key] = {"type": entry["type"], "value": typed_value(entry["value"], entry["type"])}
    return result


def clean_snapshot(raw):
    if not isinstance(raw, dict) or set(raw) - set(VARIABLE_SCOPES):
        raise MapError("Invalid blueprint variable snapshot.")
    return {scope: clean_store(store) for scope, store in raw.items()}


def signal_event(event):
    if not isinstance(event, str) or not event.startswith("signal:"):
        return False
    name(event[7:])
    return True


def definitions(blueprint):
    """Validate a consistent type for each authored variable in this element."""
    if not isinstance(blueprint, dict) or not isinstance(blueprint.get("graphs"), dict):
        raise MapError("Invalid blueprint document.")
    result = {scope: {} for scope in VARIABLE_SCOPES}
    for event, graph in blueprint["graphs"].items():
        if removed_event(event):
            continue
        if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
            raise MapError("Invalid blueprint graph.")
        for node in graph["nodes"]:
            if not isinstance(node, dict):
                raise MapError("Invalid blueprint node type.")
            if node.get("type") not in ("getVariable", "setVariable"):
                continue
            scope, key, value_type = node.get("scope"), name(node.get("name")), node.get("valueType")
            if scope not in VARIABLE_SCOPES or value_type not in VARIABLE_TYPES:
                raise MapError("Invalid blueprint variable type.")
            if key in result[scope] and result[scope][key] != value_type:
                raise MapError("A blueprint variable must keep the same type.")
            result[scope][key] = value_type
            if len(result[scope]) > MAX_VARIABLES:
                raise MapError("The blueprint has too many variables.")
    return result


def validate_definitions(blueprints, scene_store=None):
    """Scene declarations agree across elements; element declarations stay local."""
    scene_types = {key: entry["type"] for key, entry in clean_store(scene_store or {}).items()}
    for blueprint in blueprints:
        for key, value_type in definitions(blueprint)["scene"].items():
            if key in scene_types and scene_types[key] != value_type:
                raise MapError("A blueprint variable must keep the same type.")
            scene_types[key] = value_type
            if len(scene_types) > MAX_VARIABLES:
                raise MapError("The blueprint has too many variables.")


def validate_element_store(blueprint, store):
    store = clean_store(store)
    for key, value_type in definitions(blueprint)["element"].items():
        if key in store and store[key]["type"] != value_type:
            raise MapError("A blueprint variable must keep the same type.")
    return store


def snapshot(element, scene):
    return {"element": clean_store(element.data.get("automationVariables", {})),
            "scene": clean_store(scene.settings.get("automationVariables", {}))}


def assign(store, key, value_type, value):
    if key in store and store[key]["type"] != value_type:
        raise MapError("A blueprint variable must keep the same type.")
    if key not in store and len(store) >= MAX_VARIABLES:
        raise MapError("The blueprint has too many variables.")
    store[key] = {"type": value_type, "value": typed_value(value, value_type)}


def copy_runtime(previous, result):
    """Only server-owned prior state survives an authored native edit."""
    if previous and "automationVariables" in previous and "blueprint" in result:
        result["automationVariables"] = deepcopy(validate_element_store(
            result["blueprint"], previous["automationVariables"]))
    if previous and "automationMemory" in previous and "blueprint" in result:
        from .blueprint_memory import reconcile_memory
        memory = reconcile_memory(result["blueprint"], previous["automationMemory"])
        if memory:
            result["automationMemory"] = memory
    return result
