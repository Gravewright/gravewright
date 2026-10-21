"""Bounded state graphs for generic intelligent scene objects.

This module validates authored data and evaluates a single event without I/O.
Domain services apply the resulting actions after checking scene permissions.
Door, lever, composed torch and presence region capabilities are available.
Historical version 1 definitions normalize to version 2 with retired events removed.
Version 2 supports typed execution edges and ordered fan-out,
plus data edges from pure value nodes into typed inputs. Pure nodes have no
execution ports and are evaluated only when an executed node reads their value.
"""

from copy import deepcopy
import math
import re
from uuid import UUID

from .services import MapError
from .blueprint_events import removed_event
from .blueprint_memory import CONTROL_TYPES, clean_now, execute_control, reconcile_memory
from .blueprint_context import CONTEXT_TYPES, clean_event_context
from .blueprint_variables import (
    MAX_SIGNAL_GRAPHS, VARIABLE_SCOPES, VARIABLE_TYPES, VALUE_OPERATORS,
    clean_snapshot, definitions, name as variable_name, signal_event, typed_value,
)


DOOR_STATES = ("closed", "open", "locked")
DOOR_EVENTS = ("interact", "destroy")
LEVER_STATES = ("off", "on")
# Each element kind owns its states and supported start events. Actions
# aimed at another element through a Target may name any known state; the
# runtime skips a state the target's kind does not have.
REGION_STATES = ("empty", "occupied")
KIND_STATES = {"door": DOOR_STATES, "lever": LEVER_STATES, "torch": LEVER_STATES, "region": REGION_STATES}
KIND_EVENTS = {kind: DOOR_EVENTS for kind in KIND_STATES}
KIND_EVENTS["lever"] = KIND_EVENTS["torch"] = ("interact", "presence:enter", "presence:exit", "destroy")
KIND_EVENTS["region"] = ("presence:enter", "presence:exit", "destroy")
VERB_EVENTS = DOOR_EVENTS
WRITABLE_STATES = DOOR_STATES + LEVER_STATES
ALL_STATES = WRITABLE_STATES + REGION_STATES
NODE_TYPES = ("event", "light", "sound", "state", "interact", "condition", "sequence", "sprite", "property", "compare",
              "reference", "reveal", "barrier", "soundControl", "flame", "all", "any",
              "getVariable", "setVariable", "compareValue", "emitEvent", "delay", "timer", "switch", "random",
              "elementGroup", "lightReference", "soundReference", "eventContext", "move", "rotate", "setInteraction", "setRegion",
              "setVisibility", "setAppearance", "showMessage", "showHandout", "requestRoll", "setQuestStatus", "cameraFocus", "teleport", *CONTROL_TYPES)
# Node types introduced with version 2; version 1 documents keep their original vocabulary.
VERSION_2_NODE_TYPES = ("interact", "sequence", "sprite", "property", "compare", "reference", "reveal", "barrier", "soundControl", "flame", "all", "any", "getVariable", "setVariable", "compareValue", "emitEvent", "delay", "timer", "switch", "random", "elementGroup", "lightReference", "soundReference", "eventContext", "move", "rotate", "setInteraction", "setRegion", "setVisibility", "setAppearance", "showMessage", "showHandout", "requestRoll", "setQuestStatus", "cameraFocus", "teleport", *CONTROL_TYPES)
BARRIER_CHANNELS = ("movement", "vision", "light", "sound")
SOUND_CONTROLS = ("stop", "volume")
PURE_NODE_TYPES = ("property", "compare", "reference", "all", "any", "getVariable", "compareValue", "elementGroup", "lightReference", "soundReference", "eventContext")
APPEARANCES = ("inherit", "hidden", "asset")
DOOR_PROPERTIES = ("state", "previous")
SEQUENCE_OUTPUTS = ("then1", "then2", "then3", "then4")
BOOLEAN_INPUTS = ("a", "b", "c", "d")
EXECUTION_OUTPUTS = {"condition": ("true", "false"), "sequence": SEQUENCE_OUTPUTS,
                     **{kind: ("true", "false") for kind in CONTROL_TYPES}}
# Typed data ports: outputs of pure nodes and the inputs that may read them.
# The reference output keeps its original "door" port ID; its type is any element.
DATA_OUTPUTS = {"property": {"value": "state"}, "compare": {"result": "boolean"}, "reference": {"door": "element"},
                "all": {"result": "boolean"}, "any": {"result": "boolean"}, "compareValue": {"result": "boolean"}}
# A connected Target replaces "Self" with a referenced element.
DATA_INPUTS = {"compare": {"value": "state"}, "condition": {"test": "boolean"},
               "state": {"target": "element"}, "interact": {"target": "element"}, "sprite": {"target": "element"},
               "reveal": {"target": "element"}, "property": {"target": "element"},
               "barrier": {"target": "element"}, "flame": {"target": "element"}, "emitEvent": {"target": "element"},
               "all": {port: "boolean" for port in BOOLEAN_INPUTS},
               "any": {port: "boolean" for port in BOOLEAN_INPUTS}}
SUPPORTED_VERSIONS = (1, 2)
DOOR_CAPABILITY = {
    "kind": "door",
    "states": DOOR_STATES,
    "events": KIND_EVENTS["door"],
    "nodeTypes": NODE_TYPES,
    "connectionKinds": ("execution", "data"),
}
MAX_GRAPH_NODES = 32
MAX_GRAPH_EDGES = 64
MAX_BLUEPRINT_NODES = 128
MAX_LAYOUT_COORDINATE = 5000
_NODE_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
_NODE_FIELDS = {
    "event": {"event"},
    "light": {"targetId", "enabled"},
    "sound": {"trackId", "volume"},
    "state": {"targetState"},
    "interact": set(),
    "condition": {"state"},
    "sequence": set(),
    "sprite": {"appearance"},
    "property": {"property"},
    "compare": {"state"},
    "reference": {"targetId"},
    "reveal": set(),
    "barrier": {"channel", "mode"},
    "soundControl": {"trackId", "action", "volume"},
    "flame": {"enabled"},
    "all": set(),
    "any": set(),
    "getVariable": {"scope", "name", "valueType", "default"},
    "setVariable": {"scope", "name", "valueType", "value"},
    "compareValue": {"valueType", "operator", "expected"},
    "emitEvent": {"scope", "name"},
    "counter": {"target"},
    "once": set(),
    "cooldown": {"seconds"},
    "delay": {"seconds"},
    "timer": {"name", "action"},
    "switch": {"valueType", "value", "cases"},
    "random": {"weights"},
    "elementGroup": {"name", "memberType", "targetIds"},
    "lightReference": {"targetId"},
    "soundReference": {"trackId"},
    "eventContext": {"property"},
    "move": {"dx", "dy"},
    "rotate": {"degrees"},
    "setInteraction": {"enabled"},
    "setRegion": {"enabled"},
    "setVisibility": {"visible"},
    "setAppearance": {"assetId"},
    "showMessage": {"text", "audience"},
    "showHandout": {"journalId", "audience"},
    "requestRoll": {"expression", "label", "visibility", "audience"},
    "setQuestStatus": {"journalId", "status"},
    "cameraFocus": {"focusX", "focusY", "audience"},
    "teleport": {"destinationId"},
}
# Optional fields: a Change state "players" flag explicitly lets a player-started
# chain lock or unlock with that action; it is omitted when false.
_OPTIONAL_FIELDS = {"sprite": ("assetId",), "state": ("players",), "timer": ("seconds",)}


def default_blueprint(kind="door"):
    """Return an independent current definition retaining native appearance."""
    return {
        "version": 2,
        "kind": kind,
        "states": {state: {"appearance": "inherit"} for state in KIND_STATES[kind]},
        "graphs": {},
    }


def has_event_path(blueprint, event):
    """Whether a root event has an authored execution path, including version 1.

    An empty draft or disconnected nodes must not override a native interaction.
    Callers validate the blueprint before execution; this also accepts its raw
    stored shape when deciding whether a locked door has an interaction handler.
    """
    graph = (blueprint or {}).get("graphs", {}).get(event)
    if not isinstance(graph, dict):
        return False
    root = next((node.get("id") for node in graph.get("nodes", []) if node.get("type") == "event"), None)
    return root is not None and any(edge.get("from") == root and edge.get("kind") != "data"
                                   for edge in graph.get("edges", []))


def _fields(raw, required, optional=(), *, label):
    if not isinstance(raw, dict) or not required <= raw.keys():
        raise MapError(f"Invalid blueprint {label}.")
    if raw.keys() - required - set(optional):
        raise MapError(f"Unknown blueprint {label} field.")


def _number(value, low, high, *, label):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not low <= value <= high
        or not math.isfinite(value)
    ):
        raise MapError(f"Invalid blueprint {label}.")
    return round(value, 3)


def _identifier(value):
    if not isinstance(value, str) or not _NODE_IDENTIFIER.fullmatch(value):
        raise MapError("Invalid blueprint node identifier.")
    return value


def _references(values):
    return None if values is None else {str(value) for value in values}


def _reference(value, allowed, *, label):
    if not isinstance(value, str):
        raise MapError(f"Invalid blueprint {label} reference.")
    try:
        identifier = str(UUID(value))
    except (ValueError, AttributeError):
        raise MapError(f"Invalid blueprint {label} reference.") from None
    if allowed is not None and identifier not in allowed:
        raise MapError(f"Blueprint {label} not found.")
    return identifier


def _state(value, states=ALL_STATES):
    if not isinstance(value, str) or value not in states:
        raise MapError("Invalid blueprint door state.")
    return value


def _appearance(raw, assets):
    """Validate a state or sprite appearance; only image appearances name an asset."""
    appearance = raw.get("appearance")
    if not isinstance(appearance, str) or appearance not in APPEARANCES:
        raise MapError("Invalid blueprint appearance.")
    result = {"appearance": appearance}
    if appearance == "asset":
        result["assetId"] = _reference(raw.get("assetId"), assets, label="asset")
    elif "assetId" in raw:
        raise MapError("Only asset appearances can reference a blueprint asset.")
    return result


def clean_audience(raw):
    """Validate an explicit authored audience without accepting caller identities."""
    _fields(raw, {"scope"}, ("userIds",), label="audience")
    scope = raw["scope"]
    if not isinstance(scope, str) or scope not in ("trigger", "players", "users"):
        raise MapError("Invalid blueprint audience.")
    result = {"scope": scope}
    if scope == "users":
        identifiers = raw.get("userIds")
        if not isinstance(identifiers, list) or not 1 <= len(identifiers) <= 64:
            raise MapError("Invalid blueprint audience.")
        result["userIds"] = [_reference(value, None, label="audience") for value in identifiers]
        if len(set(result["userIds"])) != len(identifiers):
            raise MapError("Invalid blueprint audience.")
    elif "userIds" in raw:
        raise MapError("Invalid blueprint audience.")
    return result


def _clean_node(raw, event, *, version, assets, lights, tracks, appearance_assets):
    if not isinstance(raw, dict) or raw.get("type") not in NODE_TYPES:
        raise MapError("Invalid blueprint node type.")
    kind = raw["type"]
    if version == 1 and kind in VERSION_2_NODE_TYPES:
        raise MapError("Invalid blueprint node type.")
    fields = {"id", "type", "x", "y"} | _NODE_FIELDS[kind]
    _fields(raw, fields, _OPTIONAL_FIELDS.get(kind, ()), label="node")
    if kind == "state" and "players" in raw and (version == 1 or raw["players"] is not True):
        raise MapError("Invalid blueprint player authorization.")
    result = {
        "id": _identifier(raw["id"]),
        "type": kind,
        "x": _number(raw["x"], 0, MAX_LAYOUT_COORDINATE, label="node position"),
        "y": _number(raw["y"], 0, MAX_LAYOUT_COORDINATE, label="node position"),
    }
    if kind == "event":
        if raw["event"] != event:
            raise MapError("Blueprint event does not match its graph.")
        result["event"] = event
    elif kind in ("light", "flame"):
        if kind == "light":
            result["targetId"] = _reference(raw["targetId"], lights, label="light")
        if not isinstance(raw["enabled"], bool):
            raise MapError("Invalid blueprint light state.")
        result["enabled"] = raw["enabled"]
    elif kind == "sound":
        result["trackId"] = _reference(raw["trackId"], tracks, label="sound")
        result["volume"] = _number(raw["volume"], 0, 1, label="sound volume")
    elif kind == "state":
        result["targetState"] = _state(raw["targetState"], DOOR_STATES if version == 1 else WRITABLE_STATES)
        if raw.get("players") is True:
            result["players"] = True
    elif kind in ("condition", "compare"):
        result["state"] = _state(raw["state"], DOOR_STATES if version == 1 else ALL_STATES)
    elif kind == "sprite":
        result.update(_appearance(raw, appearance_assets))
    elif kind == "property":
        if not isinstance(raw["property"], str) or raw["property"] not in DOOR_PROPERTIES:
            raise MapError("Invalid blueprint property.")
        result["property"] = raw["property"]
    elif kind == "barrier":
        channel, mode = raw["channel"], raw["mode"]
        allowed = ("block", "pass", "attenuate") if channel == "sound" else ("block", "pass")
        if not isinstance(channel, str) or channel not in BARRIER_CHANNELS or not isinstance(mode, str) or mode not in allowed:
            raise MapError("Invalid blueprint barrier.")
        result.update(channel=channel, mode=mode)
    elif kind == "soundControl":
        if not isinstance(raw["action"], str) or raw["action"] not in SOUND_CONTROLS:
            raise MapError("Invalid blueprint sound control.")
        result.update(trackId=_reference(raw["trackId"], tracks, label="sound"), action=raw["action"],
                      volume=_number(raw["volume"], 0, 1, label="sound volume"))
    elif kind == "reference":
        # Door references may outlive their target; the runtime skips and logs
        # actions whose door is missing instead of rejecting the whole blueprint.
        result["targetId"] = _reference(raw["targetId"], None, label="element")
    elif kind in ("lightReference", "soundReference"):
        key, allowed, label = ("targetId", lights, "light") if kind == "lightReference" else ("trackId", tracks, "sound")
        result[key] = _reference(raw[key], None, label=label)
    elif kind == "elementGroup":
        name, member_type, targets = raw["name"], raw["memberType"], raw["targetIds"]
        if (not isinstance(name, str) or not name.strip() or len(name) > 80 or "\x00" in name
                or member_type not in ("element", "light", "sound")
                or not isinstance(targets, list) or not 1 <= len(targets) <= 32):
            raise MapError("Invalid blueprint element group.")
        targets = [_reference(target, None, label=member_type) for target in targets]
        if len(set(targets)) != len(targets):
            raise MapError("Invalid blueprint element group.")
        result.update(name=name, memberType=member_type, targetIds=targets)
    elif kind == "eventContext":
        if not isinstance(raw["property"], str) or raw["property"] not in CONTEXT_TYPES:
            raise MapError("Invalid blueprint event context.")
        result["property"] = raw["property"]
    elif kind == "move":
        result.update(dx=_number(raw["dx"], -1000, 1000, label="movement"),
                      dy=_number(raw["dy"], -1000, 1000, label="movement"))
    elif kind == "rotate":
        result["degrees"] = _number(raw["degrees"], -36000, 36000, label="rotation")
    elif kind in ("setInteraction", "setRegion"):
        if type(raw["enabled"]) is not bool:
            raise MapError("Invalid blueprint interaction state.")
        result["enabled"] = raw["enabled"]
    elif kind == "setVisibility":
        if type(raw["visible"]) is not bool:
            raise MapError("Invalid blueprint visibility.")
        result["visible"] = raw["visible"]
    elif kind == "setAppearance":
        result["assetId"] = _reference(raw["assetId"], appearance_assets, label="asset")
    elif kind == "setQuestStatus":
        from gravewright.journals.data import QUEST_STATUSES
        result["journalId"] = _reference(raw["journalId"], None, label="quest")
        if not isinstance(raw["status"], str) or raw["status"] not in QUEST_STATUSES:
            raise MapError("Invalid blueprint quest status.")
        result["status"] = raw["status"]
    elif kind in ("showMessage", "showHandout", "requestRoll", "cameraFocus"):
        result["audience"] = clean_audience(raw["audience"])
        if kind == "showMessage":
            text = raw["text"]
            if not isinstance(text, str) or not text.strip() or len(text) > 2000 or "\x00" in text:
                raise MapError("Invalid blueprint message.")
            result["text"] = text
        elif kind == "showHandout":
            result["journalId"] = _reference(raw["journalId"], None, label="handout")
        elif kind == "requestRoll":
            from gravewright.dice.engine import RollError
            from gravewright.dice.grammar.compiler import compile_expression
            from gravewright.dice.grammar.parser import Parser
            expression, label, visibility = raw["expression"], raw["label"], raw["visibility"]
            if (not isinstance(expression, str) or not expression.strip() or len(expression) > 512
                    or not isinstance(label, str) or len(label) > 48 or "\x00" in label
                    or not isinstance(visibility, str) or visibility not in ("public", "gm")):
                raise MapError("Invalid blueprint roll request.")
            try:
                compile_expression(Parser(expression).parse())
            except RollError:
                raise MapError("Invalid blueprint roll expression.") from None
            result.update(expression=expression, label=label, visibility=visibility)
        else:
            result.update(focusX=_number(raw["focusX"], 0, 1000, label="camera focus"),
                          focusY=_number(raw["focusY"], 0, 1000, label="camera focus"))
    elif kind == "teleport":
        result["destinationId"] = _reference(raw["destinationId"], None, label="destination")
    elif kind == "counter":
        if type(raw["target"]) is not int or not 1 <= raw["target"] <= 1_000_000:
            raise MapError("Invalid blueprint counter target.")
        result["target"] = raw["target"]
    elif kind in ("cooldown", "delay"):
        seconds = raw["seconds"]
        if type(seconds) not in (int, float) or not .1 <= seconds <= 86400 or not math.isfinite(seconds):
            raise MapError("Invalid blueprint delay duration." if kind == "delay" else "Invalid blueprint cooldown duration.")
        result["seconds"] = seconds
    elif kind == "timer":
        action = raw["action"]
        if (not isinstance(action, str) or action not in ("start", "stop", "restart")
                or (action == "stop") == ("seconds" in raw)):
            raise MapError("Invalid blueprint timer.")
        result.update(name=variable_name(raw["name"]), action=action)
        if action != "stop":
            seconds = raw["seconds"]
            if type(seconds) not in (int, float) or not .1 <= seconds <= 86400 or not math.isfinite(seconds):
                raise MapError("Invalid blueprint timer.")
            result["seconds"] = seconds
    elif kind == "switch":
        value_type, cases = raw["valueType"], raw["cases"]
        if value_type not in VARIABLE_TYPES or not isinstance(cases, list) or not 1 <= len(cases) <= 4:
            raise MapError("Invalid blueprint switch.")
        result.update(valueType=value_type, value=typed_value(raw["value"], value_type), cases=[])
        identifiers, values = set(), []
        for entry in cases:
            _fields(entry, {"id", "value"}, label="switch case")
            identifier, value = entry["id"], typed_value(entry["value"], value_type)
            if (not isinstance(identifier, str) or identifier not in ("case1", "case2", "case3", "case4")
                    or identifier in identifiers or value in values):
                raise MapError("Invalid blueprint switch.")
            identifiers.add(identifier)
            values.append(value)
            result["cases"].append({"id": identifier, "value": value})
    elif kind == "random":
        weights = raw["weights"]
        if (not isinstance(weights, list) or not 2 <= len(weights) <= 4
                or any(type(weight) is not int or not 0 <= weight <= 1000 for weight in weights)
                or not any(weights)):
            raise MapError("Invalid blueprint random weights.")
        result["weights"] = list(weights)
    elif kind in ("getVariable", "setVariable", "compareValue", "emitEvent"):
        if kind != "compareValue":
            if raw["scope"] not in VARIABLE_SCOPES:
                raise MapError("Invalid blueprint variable scope.")
            result.update(scope=raw["scope"], name=variable_name(raw["name"]))
        if kind != "emitEvent":
            value_type = raw["valueType"]
            if value_type not in VARIABLE_TYPES:
                raise MapError("Invalid blueprint variable type.")
            field = "default" if kind == "getVariable" else "expected" if kind == "compareValue" else "value"
            result.update(valueType=value_type, **{field: typed_value(raw[field], value_type)})
        if kind == "compareValue":
            operator = raw["operator"]
            if operator not in VALUE_OPERATORS or value_type != "number" and operator not in ("eq", "ne"):
                raise MapError("Invalid blueprint value comparison.")
            result["operator"] = operator
    return result


def data_outputs(node):
    kind = node["type"]
    if kind == "getVariable":
        return {"value": node["valueType"]}
    if kind == "elementGroup":
        return {"targets": node["memberType"] + "set"}
    if kind == "eventContext":
        return {"value": CONTEXT_TYPES[node["property"]]}
    if kind in ("lightReference", "soundReference"):
        return {"light": "light"} if kind == "lightReference" else {"sound": "sound"}
    return DATA_OUTPUTS.get(kind, {})


def data_inputs(node):
    if node["type"] in ("setVariable", "compareValue", "switch"):
        return {"value": node["valueType"]}
    if node["type"] in ("move", "rotate", "setInteraction", "setRegion", "setVisibility", "setAppearance"):
        return {"target": "element"}
    if node["type"] in ("light", "sound", "soundControl"):
        return {"target": "light" if node["type"] == "light" else "sound"}
    return DATA_INPUTS.get(node["type"], {})


def accepts_data_type(node, port, produced):
    accepted = data_inputs(node).get(port)
    if accepted is None:
        return False
    if port == "target" and node["type"] != "property":
        choices = ("element", "elementset", "light", "lightset") if node["type"] in ("move", "rotate") else (accepted, accepted + "set")
        return produced in choices
    return accepted == produced


def execution_outputs(node):
    if node["type"] in PURE_NODE_TYPES:
        return ()
    if node["type"] == "switch":
        return (*[entry["id"] for entry in node["cases"]], "default")
    if node["type"] == "random":
        return tuple(f"branch{index + 1}" for index in range(len(node["weights"])))
    return EXECUTION_OUTPUTS.get(node["type"], ("next",))


def _clean_graph(raw, event, *, version, assets, lights, tracks, appearance_assets):
    _fields(raw, {"nodes", "edges"}, label="graph")
    if (
        not isinstance(raw["nodes"], list)
        or not 1 <= len(raw["nodes"]) <= MAX_GRAPH_NODES
        or not isinstance(raw["edges"], list)
        or len(raw["edges"]) > MAX_GRAPH_EDGES
    ):
        raise MapError("Blueprint graph limit reached.")
    nodes = [
        _clean_node(node, event, version=version, assets=assets, lights=lights, tracks=tracks, appearance_assets=appearance_assets)
        for node in raw["nodes"]
    ]
    by_id = {node["id"]: node for node in nodes}
    if len(by_id) != len(nodes):
        raise MapError("Duplicate blueprint node identifier.")
    if sum(node["type"] == "event" for node in nodes) != 1:
        raise MapError("Use exactly one event node in each blueprint graph.")

    edges = []
    outputs = set()
    connections = set()
    inputs = set()
    incoming = {node["id"]: 0 for node in nodes}
    successors = {node["id"]: [] for node in nodes}
    for raw_edge in raw["edges"]:
        data = version == 2 and isinstance(raw_edge, dict) and raw_edge.get("kind") == "data"
        fields = {"from", "to", "output"}
        if version == 2:
            fields.add("kind")
        if data:
            fields.add("input")
        _fields(raw_edge, fields, label="connection")
        if version == 2 and raw_edge["kind"] not in DOOR_CAPABILITY["connectionKinds"]:
            raise MapError("Unsupported blueprint connection kind.")
        origin = _identifier(raw_edge["from"])
        target = _identifier(raw_edge["to"])
        if origin not in by_id or target not in by_id:
            raise MapError("Blueprint connection references a missing node.")
        output = raw_edge["output"]
        source_type, target_type = by_id[origin]["type"], by_id[target]["type"]
        if data:
            # A data edge joins a pure node's typed output to one typed input.
            port = raw_edge["input"]
            produced = data_outputs(by_id[origin])
            accepted = data_inputs(by_id[target])
            if not isinstance(output, str) or output not in produced:
                raise MapError("Invalid blueprint connection output.")
            if not isinstance(port, str) or port not in accepted or not accepts_data_type(by_id[target], port, produced[output]):
                raise MapError("Invalid blueprint connection input.")
            if (target, port) in inputs:
                raise MapError("Use one blueprint connection per input.")
            inputs.add((target, port))
        else:
            allowed = execution_outputs(by_id[origin])
            if not isinstance(output, str) or output not in allowed:
                raise MapError("Invalid blueprint connection output.")
            if target_type == "event":
                raise MapError("Blueprint events cannot have incoming connections.")
            if target_type in PURE_NODE_TYPES:
                raise MapError("Invalid blueprint connection input.")
            if version == 1 and (origin, output) in outputs:
                raise MapError("Use one blueprint connection per output.")
            outputs.add((origin, output))
        connection = (origin, output, target, raw_edge["input"] if data else None)
        if connection in connections:
            raise MapError("Duplicate blueprint connection.")
        connections.add(connection)
        successors[origin].append(target)
        incoming[target] += 1
        edge = {"from": origin, "to": target, "output": output}
        if version == 2:
            edge["kind"] = "data" if data else "execution"
        if data:
            edge["input"] = raw_edge["input"]
        edges.append(edge)

    # Check every node, including disconnected draft branches. The bounded graph
    # makes a nonrecursive topological walk cheap and prevents authored loops.
    pending = [node_id for node_id, count in incoming.items() if count == 0]
    visited = 0
    while pending:
        origin = pending.pop()
        visited += 1
        for target in successors[origin]:
            incoming[target] -= 1
            if incoming[target] == 0:
                pending.append(target)
    if visited != len(nodes):
        raise MapError("Blueprint connections cannot contain a cycle.")
    return {"nodes": nodes, "edges": edges}


def clean_blueprint(raw, *, asset_ids=None, light_ids=None, track_ids=None, appearance_asset_ids=None):
    """Validate a door graph, optionally restricting references to owned IDs.

    Passing an empty set rejects every reference of that resource type. ``None``
    skips ownership resolution for already validated data, never UUID validation.
    The returned document shares no mutable data with the authored input.
    """
    _fields(raw, {"version", "kind", "states", "graphs"}, label="document")
    if (
        type(raw["version"]) is not int
        or raw["version"] not in SUPPORTED_VERSIONS
        or not isinstance(raw["kind"], str)
        or raw["kind"] not in KIND_STATES
        or raw["kind"] != "door" and raw["version"] == 1
    ):
        raise MapError("Unsupported blueprint version or object kind.")
    version, kind = raw["version"], raw["kind"]
    assets = _references(asset_ids)
    appearance_assets = assets if appearance_asset_ids is None else _references(appearance_asset_ids)
    lights = _references(light_ids)
    tracks = _references(track_ids)
    _fields(raw["states"], set(KIND_STATES[kind]), label="states")
    states = {}
    for state in KIND_STATES[kind]:
        entry = raw["states"][state]
        _fields(entry, {"appearance"}, {"assetId"}, label="appearance")
        states[state] = _appearance(entry, assets)
        if kind == "region" and states[state]["appearance"] != "inherit":
            raise MapError("Regions do not have state images.")

    raw_graphs = raw["graphs"]
    if not isinstance(raw_graphs, dict) or any(
            event not in KIND_EVENTS[kind] and not signal_event(event) and not removed_event(event)
            for event in raw_graphs):
        raise MapError("Invalid blueprint event.")
    if sum(event.startswith("signal:") for event in raw_graphs) > MAX_SIGNAL_GRAPHS:
        raise MapError("The blueprint has too many signal events.")
    graphs = {}
    total_nodes = 0
    for event, graph in raw_graphs.items():
        if removed_event(event):
            continue
        graphs[event] = _clean_graph(
            graph, event, version=version, assets=assets, lights=lights, tracks=tracks, appearance_assets=appearance_assets
        )
        total_nodes += len(graphs[event]["nodes"])
        if total_nodes > MAX_BLUEPRINT_NODES:
            raise MapError("Blueprint node limit reached.")
        if version == 1:
            for edge in graphs[event]["edges"]:
                edge["kind"] = "execution"
    result = {"version": 2, "kind": kind, "states": states, "graphs": graphs}
    definitions(result)
    return result


def convert_blueprint(raw, *, version=2, asset_ids=None, light_ids=None, track_ids=None, appearance_asset_ids=None):
    """Normalize a definition into the current base-event format."""
    if type(version) is not int or version != 2:
        raise MapError("Unsupported blueprint conversion version.")
    result = clean_blueprint(
        raw, asset_ids=asset_ids, light_ids=light_ids, track_ids=track_ids, appearance_asset_ids=appearance_asset_ids
    )
    if result["version"] == version:
        return result
    result["version"] = version
    for graph in result["graphs"].values():
        for edge in graph["edges"]:
            edge["kind"] = "execution"
    return result


def evaluate_graph(blueprint, event, current_state, previous_state=None, doors=None, *, variables=None,
                   memory=None, now=0, continuation=None, random_draw=None, event_context=None):
    """Return the executed path and actions without modifying data or resources.

    Conditions and properties observe the state at the beginning of this event.
    ``previous_state`` is optional trigger metadata; without it, Previous state
    equals the current state. Event roots never compare or change either value.
    The domain service applies state and visual actions in authored order.
    Their effects do not change this event's condition and property snapshots.
    Version 2 follows each output's edges depth-first in their authored order,
    a sequence runs its outputs in order, and a shared descendant executes once
    per event, even when branches reconverge. Pure nodes are evaluated once,
    when an executed node reads them, and are added to the trace at that point.
    A graph's result also lists those ``values`` and each condition's ``decisions``.
    All/Any read every connected Boolean input in a fixed port order. Fewer than
    two connections are a valid draft and yield false; unconnected inputs are ignored.
    ``doors`` maps door IDs to their state at the start of the event; a property
    with a connected Target reads it, and an action with a connected Target
    carries the referenced door ID as ``target`` for the runtime to resolve.
    Control nodes update a cloned per-event/node memory and choose a Boolean
    execution branch. ``now`` is explicit UTC milliseconds; its deterministic
    default is only useful for local simulation. The server supplies its clock.
    """
    blueprint = clean_blueprint(blueprint)
    variables = clean_snapshot({} if variables is None else variables)
    now = clean_now(now)
    has_memory = memory is not None or any(node["type"] in CONTROL_TYPES
        for graph in blueprint["graphs"].values() for node in graph["nodes"])
    control_memory = reconcile_memory(blueprint, {} if memory is None else memory)
    if (not isinstance(event, str) or blueprint["version"] == 1 and event in VERB_EVENTS
            or event not in KIND_EVENTS[blueprint["kind"]] and not (blueprint["version"] == 2 and signal_event(event))):
        raise MapError("Invalid blueprint event.")
    current_state = _state(current_state)
    previous_state = current_state if previous_state is None else _state(previous_state)
    if continuation is not None:
        _clean_continuation(blueprint, event, continuation)
        current_state = _state(continuation["currentState"])
        previous_state = _state(continuation["previousState"])
        variables = clean_snapshot(continuation["variables"])
        doors = continuation["doors"]
        event_context = continuation.get("eventContext", event_context)
    event_context = clean_event_context(event_context, event=event, state=current_state, previous=previous_state)
    graph = blueprint["graphs"].get(event)
    result = {"trace": [], "actions": []}
    if has_memory:
        result["memory"] = control_memory
    if graph is None:
        return result
    nodes = {node["id"]: node for node in graph["nodes"]}
    connections, sources = {}, {}
    for edge in graph["edges"]:
        if edge.get("kind") == "data":
            sources[(edge["to"], edge["input"])] = edge["from"]
        else:
            connections.setdefault((edge["from"], edge["output"]), []).append(edge["to"])
    values = deepcopy(continuation["values"]) if continuation is not None else {}
    decisions = deepcopy(continuation["decisions"]) if continuation is not None else {}
    result["values"], result["decisions"] = values, decisions

    def value(identifier):
        # Validation guarantees an acyclic graph with at most 32 nodes.
        if identifier not in values:
            node = nodes[identifier]
            if node["type"] == "reference":
                values[identifier] = node["targetId"]
            elif node["type"] == "elementGroup":
                values[identifier] = list(node["targetIds"])
            elif node["type"] in ("lightReference", "soundReference"):
                values[identifier] = node["targetId"] if node["type"] == "lightReference" else node["trackId"]
            elif node["type"] == "eventContext":
                values[identifier] = event_context[node["property"]]
            elif node["type"] == "property":
                source = sources.get((identifier, "target"))
                if source:
                    # Another door has no transition here: both properties read its state.
                    values[identifier] = (doors or {}).get(value(source))
                else:
                    values[identifier] = current_state if node["property"] == "state" else previous_state
            elif node["type"] in ("all", "any"):
                inputs = [value(source) for port in BOOLEAN_INPUTS
                          if (source := sources.get((identifier, port))) is not None]
                values[identifier] = len(inputs) >= 2 and (all(inputs) if node["type"] == "all" else any(inputs))
            elif node["type"] == "getVariable":
                entry = (variables or {}).get(node["scope"], {}).get(node["name"])
                if entry is not None and entry.get("type") != node["valueType"]:
                    raise MapError("A blueprint variable must keep the same type.")
                values[identifier] = typed_value(entry["value"], node["valueType"]) if entry is not None else node["default"]
            elif node["type"] == "compareValue":
                source = sources.get((identifier, "value"))
                actual = value(source) if source else {"boolean": False, "number": 0, "text": ""}[node["valueType"]]
                expected, operator = node["expected"], node["operator"]
                values[identifier] = ({"eq": lambda: actual == expected, "ne": lambda: actual != expected,
                    "lt": lambda: actual < expected, "lte": lambda: actual <= expected,
                    "gt": lambda: actual > expected, "gte": lambda: actual >= expected}[operator])()
            else:
                source = sources.get((identifier, "value"))
                values[identifier] = (value(source) if source else current_state) == node["state"]
            result["trace"].append(identifier)
        return values[identifier]

    first = next(node for node in nodes.values() if node["type"] == "event")
    pending = list(continuation["pending"]) if continuation is not None else [first["id"]]
    visited = set(continuation["visited"]) if continuation is not None else set()
    while pending:
        identifier = pending.pop()
        if identifier in visited:
            continue
        visited.add(identifier)
        node = nodes[identifier]
        result["trace"].append(node["id"])
        kind = node["type"]
        if kind in ("light", "sound", "state", "interact", "sprite", "reveal", "barrier", "soundControl", "flame", "setVariable", "emitEvent", "timer", "move", "rotate", "setInteraction", "setRegion", "setVisibility", "setAppearance", "showMessage", "showHandout", "requestRoll", "setQuestStatus", "cameraFocus", "teleport"):
            action = deepcopy(node)
            source = sources.get((identifier, "target"))
            if source:
                action["target"] = value(source)
            if kind == "setVariable" and (source := sources.get((identifier, "value"))):
                action["value"] = value(source)
            result["actions"].append(action)
        if kind == "switch":
            source = sources.get((identifier, "value"))
            actual = value(source) if source else node["value"]
            selected = next((entry["id"] for entry in node["cases"] if entry["value"] == actual), "default")
            decisions[identifier] = selected
            ports = (selected,)
        elif kind == "random":
            total = sum(node["weights"])
            draw = random_draw(identifier, total) if random_draw is not None else 0
            if type(draw) is not int or not 0 <= draw < total:
                raise MapError("Invalid blueprint random draw.")
            cumulative = 0
            for index, weight in enumerate(node["weights"]):
                cumulative += weight
                if draw < cumulative:
                    selected = f"branch{index + 1}"
                    break
            decisions[identifier] = selected
            ports = (selected,)
        elif kind in CONTROL_TYPES:
            passed = execute_control(control_memory, event, node, now)
            decisions[identifier] = passed
            ports = ("true" if passed else "false",)
        elif kind == "condition":
            source = sources.get((identifier, "test"))
            passed = value(source) if source else node["state"] == current_state
            decisions[identifier] = passed
            ports = ("true" if passed else "false",)
        else:
            ports = SEQUENCE_OUTPUTS if kind == "sequence" else ("next",)
        targets = [target for port in ports for target in connections.get((identifier, port), ())]
        pending.extend(reversed(targets))
        if kind == "delay":
            result["delay"] = {"nodeId": identifier, "seconds": node["seconds"], "continuation": {
                "pending": pending, "visited": sorted(visited), "values": deepcopy(values),
                "decisions": deepcopy(decisions), "currentState": current_state, "previousState": previous_state,
                "doors": deepcopy(doors or {}), "variables": deepcopy(variables), "eventContext": deepcopy(event_context)}}
            break
    return result


def _clean_continuation(blueprint, event, raw):
    """Validate private persisted checkpoints before trusting their traversal state."""
    fields = {"pending", "visited", "values", "decisions", "currentState", "previousState", "doors", "variables"}
    _fields(raw, fields, ("eventContext",), label="continuation")
    graph = blueprint["graphs"].get(event)
    if graph is None:
        raise MapError("The delayed blueprint changed.")
    nodes = {node["id"]: node for node in graph["nodes"]}
    for key, limit in (("pending", MAX_GRAPH_EDGES), ("visited", MAX_GRAPH_NODES)):
        if (not isinstance(raw[key], list) or len(raw[key]) > limit
                or any(not isinstance(identifier, str) or identifier not in nodes
                       or nodes[identifier]["type"] in PURE_NODE_TYPES for identifier in raw[key])):
            raise MapError("Invalid blueprint continuation.")
    if not isinstance(raw["values"], dict) or not isinstance(raw["decisions"], dict):
        raise MapError("Invalid blueprint continuation.")
    for key, result in raw["values"].items():
        node = nodes.get(key, {})
        kind = node.get("type")
        if kind not in PURE_NODE_TYPES:
            raise MapError("Invalid blueprint continuation.")
        if kind in ("reference", "lightReference", "soundReference"):
            _reference(result, None, label="element")
        elif kind == "elementGroup":
            if (not isinstance(result, list) or not 1 <= len(result) <= 32
                    or len({_reference(item, None, label="element") for item in result}) != len(result)):
                raise MapError("Invalid blueprint continuation.")
        elif kind == "eventContext":
            if CONTEXT_TYPES[node["property"]] == "state":
                _state(result)
            else:
                typed_value(result, CONTEXT_TYPES[node["property"]])
        elif kind == "property":
            if result is not None:
                _state(result)
        else:
            typed_value(result, node["valueType"] if kind == "getVariable" else "boolean")
    for key, result in raw["decisions"].items():
        node = nodes.get(key, {})
        if node.get("type") in ("switch", "random"):
            if not isinstance(result, str) or result not in execution_outputs(node):
                raise MapError("Invalid blueprint continuation.")
            if node["type"] == "random" and node["weights"][int(result[6:]) - 1] == 0:
                raise MapError("Invalid blueprint continuation.")
        elif node.get("type") not in ("condition", *CONTROL_TYPES) or type(result) is not bool:
            raise MapError("Invalid blueprint continuation.")
    if "eventContext" in raw:
        clean_event_context(raw["eventContext"], event=event, state=raw["currentState"], previous=raw["previousState"])
    if not isinstance(raw["doors"], dict) or len(raw["doors"]) > MAX_GRAPH_NODES:
        raise MapError("Invalid blueprint continuation.")
    for key, state in raw["doors"].items():
        _reference(key, None, label="element")
        _state(state)
