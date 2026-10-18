"""Bounded private progress for executed Blueprint control nodes."""

import math
import re

from .blueprint_variables import signal_event
from .blueprint_events import removed_event
from .services import MapError


CONTROL_TYPES = ("counter", "once", "cooldown")
MAX_MEMORY_ROWS = 128
MAX_COUNT = 1_000_000
MAX_TIMESTAMP = 9_007_199_254_740_991
MAX_NOW = MAX_TIMESTAMP - 86_400_000
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")


def clean_now(value):
    if type(value) is not int or not 0 <= value <= MAX_NOW:
        raise MapError("Invalid blueprint control time.")
    return value


def clean_entry(raw):
    if not isinstance(raw, dict) or set(raw) != {"type", "value"}:
        raise MapError("Invalid blueprint control memory.")
    kind, value = raw["type"], raw["value"]
    valid = ((kind == "counter" and type(value) is int and 0 <= value <= MAX_COUNT)
             or (kind == "once" and value is True)
             or (kind == "cooldown" and type(value) is int and 0 <= value <= MAX_TIMESTAMP))
    if not valid:
        raise MapError("Invalid blueprint control memory.")
    return {"type": kind, "value": value}


def clean_memory(raw):
    """Validate stored rows before dropping progress belonging to deleted nodes."""
    if not isinstance(raw, dict) or len(raw) > MAX_MEMORY_ROWS:
        raise MapError("Invalid blueprint control memory.")
    result, count = {}, 0
    for event, rows in raw.items():
        if removed_event(event):
            continue
        if (not isinstance(event, str) or not (
                event in ("interact", "destroy", "presence:enter", "presence:exit") or signal_event(event))
                or not isinstance(rows, dict)):
            raise MapError("Invalid blueprint control memory.")
        cleaned = {}
        for identifier, entry in rows.items():
            if not isinstance(identifier, str) or not _IDENTIFIER.fullmatch(identifier):
                raise MapError("Invalid blueprint control memory.")
            cleaned[identifier] = clean_entry(entry)
            count += 1
            if count > MAX_MEMORY_ROWS:
                raise MapError("Invalid blueprint control memory.")
        if cleaned:
            result[event] = cleaned
    return result


def reconcile_memory(blueprint, raw):
    """Keep a node's progress across parameter, position and connection edits."""
    memory = clean_memory(raw)
    result = {}
    for event, graph in blueprint.get("graphs", {}).items():
        rows = memory.get(event, {})
        retained = {node["id"]: rows[node["id"]] for node in graph["nodes"]
                    if node["type"] in CONTROL_TYPES and node["id"] in rows
                    and rows[node["id"]]["type"] == node["type"]}
        if retained:
            result[event] = retained
    return result


def execute_control(memory, event, node, now):
    """Update only the evaluator's cloned memory and return the selected branch."""
    rows = memory.setdefault(event, {})
    previous = rows.get(node["id"])
    kind = node["type"]
    if kind == "counter":
        value = min(MAX_COUNT, (previous["value"] if previous else 0) + 1)
        passed = value >= node["target"]
    elif kind == "once":
        value, passed = True, previous is None
    else:
        passed = previous is None or now >= previous["value"]
        value = now + math.ceil(node["seconds"] * 1000) if passed else previous["value"]
    rows[node["id"]] = {"type": kind, "value": value}
    return passed
