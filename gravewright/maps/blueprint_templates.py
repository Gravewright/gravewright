"""GM-owned reusable snapshots with explicit typed instance bindings.

Only reference fields in the blueprint vocabulary become binding slots. Authored
text, variable values and logical node IDs keep their exact meaning. Applying a
template produces a new independent draft; ordinary project saves authorize its
resolved resources. There is no live link from an instance to the library.
"""

from copy import deepcopy
import json
import math
import re
from uuid import UUID, uuid5, NAMESPACE_URL

from django.db import transaction

from gravewright.campaigns.models import Campaign
from gravewright.journals.services import identifier

from . import builder_services, services
from .blueprints import clean_blueprint
from .blueprint_events import removed_event
from .models import BlueprintTemplate


MAX_TEMPLATES = 128
MAX_BINDINGS = 256
MAX_PARAMETERS = 64
MAX_DEFINITION_BYTES = 262144
BINDING_TYPES = ("asset", "element", "light", "sound", "handout", "user")
_IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise services.MapError("Invalid blueprint template.")


def _text(value, limit, *, empty=False):
    if not isinstance(value, str) or "\0" in value or len(value) > limit or not empty and not value.strip():
        raise services.MapError("Invalid blueprint template text.")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise services.MapError("Invalid blueprint template text.") from None
    return value


def resource_slots(blueprint):
    """Yield exact mutable resource positions; never search arbitrary JSON text."""
    if not isinstance(blueprint, dict):
        raise services.MapError("Invalid blueprint template.")
    states = blueprint.get("states", {})
    if not isinstance(states, dict):
        raise services.MapError("Invalid blueprint template.")
    for entry in states.values():
        if isinstance(entry, dict) and entry.get("appearance") == "asset":
            yield entry, "assetId", "asset"
    graphs = blueprint.get("graphs", {})
    if not isinstance(graphs, dict):
        raise services.MapError("Invalid blueprint template.")
    for graph in graphs.values():
        if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
            raise services.MapError("Invalid blueprint template.")
        for node in graph["nodes"]:
            if not isinstance(node, dict):
                raise services.MapError("Invalid blueprint template.")
            kind = node.get("type")
            if not isinstance(kind, str):
                raise services.MapError("Invalid blueprint template.")
            slot = {"reference": ("targetId", "element"), "lightReference": ("targetId", "light"),
                    "soundReference": ("trackId", "sound"), "light": ("targetId", "light"),
                    "sound": ("trackId", "sound"), "soundControl": ("trackId", "sound"),
                    "showHandout": ("journalId", "handout"), "teleport": ("destinationId", "element"),
                    "setAppearance": ("assetId", "asset")}.get(kind)
            if slot:
                yield node, *slot
            if kind == "sprite" and node.get("appearance") == "asset":
                yield node, "assetId", "asset"
            if kind == "elementGroup":
                ids = node.get("targetIds")
                if node.get("memberType") not in ("element", "light", "sound") or not isinstance(ids, list):
                    raise services.MapError("Invalid blueprint template.")
                for index in range(len(ids)):
                    yield ids, index, node["memberType"]
            audience = node.get("audience")
            if isinstance(audience, dict) and audience.get("scope") == "users":
                ids = audience.get("userIds")
                if not isinstance(ids, list):
                    raise services.MapError("Invalid blueprint template.")
                for index in range(len(ids)):
                    yield ids, index, "user"


def parameter_options(blueprint):
    """Return scalar positions that can be configured without changing topology."""
    options = []
    for event, graph in blueprint.get("graphs", {}).items():
        for index, node in enumerate(graph.get("nodes", [])):
            kind = node.get("type")
            fields = {
                "light": ("enabled",), "sound": ("volume",), "soundControl": ("volume",),
                "flame": ("enabled",), "setInteraction": ("enabled",), "setRegion": ("enabled",),
                "setVisibility": ("visible",),
                "counter": ("target",), "cooldown": ("seconds",), "delay": ("seconds",),
                "timer": (() if node.get("action") == "stop" else ("seconds",)),
                "move": ("dx", "dy"), "rotate": ("degrees",),
                "getVariable": ("default",), "setVariable": ("value",), "compareValue": ("expected",),
                "switch": ("value",), "showMessage": ("text",), "cameraFocus": ("focusX", "focusY"),
            }.get(kind, ())
            paths = [[field] for field in fields]
            if kind == "switch" and isinstance(node.get("cases"), list):
                paths += [["cases", position, "value"] for position in range(len(node["cases"]))]
            if kind == "random" and isinstance(node.get("weights"), list):
                paths += [["weights", position] for position in range(len(node["weights"]))]
            for tail in paths:
                value = node
                for part in tail:
                    value = value[part]
                scalar = "boolean" if isinstance(value, bool) else "number" if isinstance(value, (int, float)) else "text" if isinstance(value, str) else None
                if scalar:
                    options.append({"path": ["graphs", event, "nodes", index, *tail], "type": scalar,
                                    "default": deepcopy(value)})
    return options


def _at(document, path):
    for part in path[:-1]:
        document = document[part]
    return document, path[-1]


def _scalar(kind, value):
    return (isinstance(value, bool) if kind == "boolean" else
            type(value) in (int, float) and math.isfinite(value) if kind == "number" else
            isinstance(value, str) and "\0" not in value and len(value) <= 2000 if kind == "text" else False)


def clean_definition(raw):
    """Validate ID-free library data, including default parameter combinations."""
    _fields(raw, ("version", "blueprint", "bindings", "parameters"))
    try:
        size = len(json.dumps(raw, allow_nan=False, ensure_ascii=False).encode("utf-8"))
    except (ValueError, TypeError, RecursionError, OverflowError, UnicodeError):
        raise services.MapError("Invalid blueprint template.") from None
    if type(raw["version"]) is not int or raw["version"] != 1 or size > MAX_DEFINITION_BYTES:
        raise services.MapError("Invalid blueprint template.")
    pending = [(raw, 0)]
    visited = 0
    while pending:
        value, depth = pending.pop()
        visited += 1
        if depth > 32 or visited > 20000:
            raise services.MapError("Invalid blueprint template.")
        if isinstance(value, dict):
            pending.extend((entry, depth + 1) for entry in value.values())
        elif isinstance(value, list):
            pending.extend((entry, depth + 1) for entry in value)
    raw = deepcopy(raw)
    blueprint = raw["blueprint"]
    if isinstance(blueprint, dict) and isinstance(blueprint.get("graphs"), dict):
        retired = {key: value for key, value in blueprint["graphs"].items() if removed_event(key)}
        if retired:
            blueprint["graphs"] = {key: value for key, value in blueprint["graphs"].items() if not removed_event(key)}
            def binding_ids(value):
                return {parent[field]["binding"] for parent, field, _ in resource_slots(value)
                        if isinstance(parent[field], dict) and isinstance(parent[field].get("binding"), str)}
            retired_ids = set()
            for event, graph in retired.items():
                # Retired bodies are discarded even if their old nodes are malformed.
                # Discover only well-formed typed binding markers for orphan cleanup.
                if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list):
                    continue
                for node in graph["nodes"]:
                    try:
                        slots = resource_slots({"states": {}, "graphs": {event: {"nodes": [node]}}})
                        for parent, field, _ in slots:
                            marker = parent[field]
                            if isinstance(marker, dict) and isinstance(marker.get("binding"), str):
                                retired_ids.add(marker["binding"])
                    except (services.MapError, KeyError, TypeError):
                        continue
            active_ids = binding_ids(blueprint)
            if isinstance(raw["bindings"], list):
                raw["bindings"] = [row for row in raw["bindings"]
                    if not isinstance(row, dict) or row.get("id") not in retired_ids - active_ids]
            if isinstance(raw["parameters"], list):
                raw["parameters"] = [row for row in raw["parameters"]
                    if not isinstance(row, dict) or not isinstance(row.get("path"), list)
                    or len(row["path"]) < 2 or row["path"][0] != "graphs" or not removed_event(row["path"][1])]
    rows = raw["bindings"]
    if not isinstance(rows, list) or len(rows) > MAX_BINDINGS:
        raise services.MapError("Invalid blueprint template bindings.")
    bindings = {}
    for row in rows:
        _fields(row, ("id", "type", "label"), ("self",))
        key = row["id"]
        if not isinstance(key, str) or not _IDENTIFIER.fullmatch(key) or key in bindings or row["type"] not in BINDING_TYPES:
            raise services.MapError("Invalid blueprint template binding.")
        _text(row["label"], 120)
        if "self" in row and (row["self"] is not True or row["type"] != "element"):
            raise services.MapError("Invalid blueprint template Self binding.")
        bindings[key] = deepcopy(row)
    original, used = deepcopy(raw["blueprint"]), set()
    for parent, field, kind in resource_slots(original):
        marker = parent.get(field) if isinstance(parent, dict) else parent[field]
        _fields(marker, ("binding",))
        key = marker["binding"]
        if not isinstance(key, str) or key not in bindings or bindings[key]["type"] != kind:
            raise services.MapError("Invalid blueprint template binding.")
        used.add(key)
        parent[field] = str(uuid5(NAMESPACE_URL, "gravewright-template:" + key))
    if used != bindings.keys():
        raise services.MapError("Unused blueprint template binding.")
    cleaned = clean_blueprint(original)
    # The validator may normalize resources but must not rewrite parameter values.
    parameters = raw["parameters"]
    if not isinstance(parameters, list) or len(parameters) > MAX_PARAMETERS:
        raise services.MapError("Invalid blueprint template parameters.")
    allowed = {json.dumps(row["path"]): row for row in parameter_options(cleaned)}
    ids, paths = set(bindings), set()
    for row in parameters:
        _fields(row, ("id", "label", "path", "type", "default"))
        key, path = row["id"], row["path"]
        if not isinstance(key, str) or not _IDENTIFIER.fullmatch(key) or key in ids or not isinstance(path, list):
            raise services.MapError("Invalid blueprint template parameter.")
        path_key = json.dumps(path)
        option = allowed.get(path_key)
        if option is None or path_key in paths or option["type"] != row["type"] or not _scalar(row["type"], row["default"]):
            raise services.MapError("Invalid blueprint template parameter.")
        if type(option["default"]) is not type(row["default"]) and row["type"] != "number" or option["default"] != row["default"]:
            raise services.MapError("Invalid blueprint template parameter default.")
        _text(row["label"], 120)
        ids.add(key)
        paths.add(path_key)
    slots = list(resource_slots(raw["blueprint"]))
    for (parent, field, _), (source, source_field, _) in zip(resource_slots(cleaned), slots, strict=True):
        parent[field] = deepcopy(source[source_field])
    return {"version": 1, "blueprint": cleaned, "bindings": list(bindings.values()), "parameters": deepcopy(parameters)}


def resolve_definition(raw, bindings, parameters=None, *, owner_id):
    """Create a detached draft. Project persistence checks the resolved ownership."""
    definition = clean_definition(raw)
    if not isinstance(bindings, dict) or parameters is not None and not isinstance(parameters, dict):
        raise services.MapError("Invalid blueprint template values.")
    parameters = parameters or {}
    expected = {row["id"] for row in definition["bindings"] if not row.get("self")}
    if bindings.keys() != expected or parameters.keys() - {row["id"] for row in definition["parameters"]}:
        raise services.MapError("Resolve every blueprint template binding.")
    resolved = {}
    for row in definition["bindings"]:
        raw_value = owner_id if row.get("self") else bindings[row["id"]]
        try:
            resolved[row["id"]] = str(UUID(raw_value)) if isinstance(raw_value, str) else None
        except (ValueError, AttributeError):
            resolved[row["id"]] = None
        if resolved[row["id"]] is None:
            raise services.MapError("Invalid blueprint template binding value.")
    blueprint = deepcopy(definition["blueprint"])
    for parent, field, _ in resource_slots(blueprint):
        parent[field] = resolved[parent[field]["binding"]]
    for row in definition["parameters"]:
        value = parameters.get(row["id"], row["default"])
        if not _scalar(row["type"], value):
            raise services.MapError("Invalid blueprint template parameter value.")
        parent, field = _at(blueprint, row["path"])
        parent[field] = deepcopy(value)
    return clean_blueprint(blueprint)


def summary(row):
    return {"id": str(row.pk), "name": row.name, "description": row.description,
            "kind": row.definition["blueprint"]["kind"], "version": row.version,
            "updatedAt": int(row.updated_at.timestamp() * 1000)}


def catalog(campaign_id, user_id):
    who = builder_services.authority(campaign_id, user_id)
    return {"templates": [summary(row) for row in BlueprintTemplate.objects.filter(campaign=who.campaign)],
            "limits": {"templates": MAX_TEMPLATES, "bindings": MAX_BINDINGS, "parameters": MAX_PARAMETERS}}


def detail(campaign_id, user_id, template_id):
    who = builder_services.authority(campaign_id, user_id)
    row = BlueprintTemplate.objects.filter(pk=identifier(template_id), campaign=who.campaign).first()
    if row is None:
        raise services.MapError("Blueprint template not found.", "not_found")
    return {"template": {**summary(row), "definition": clean_definition(row.definition)}}


def mutate(campaign_id, user_id, template_id, payload, *, delete=False):
    required = ("request_id", "expected_version") if delete else ("request_id", "expected_version", "name", "description", "definition")
    _fields(payload, required)
    if type(payload["expected_version"]) is not int or payload["expected_version"] < 0:
        raise services.MapError("Invalid blueprint template revision.")
    template_id, request_id = identifier(template_id), identifier(payload["request_id"])
    digest = builder_services.fingerprint("template-delete" if delete else "template-save", template_id, payload)
    with transaction.atomic():
        who = builder_services.authority(campaign_id, user_id)
        Campaign.objects.select_for_update().get(pk=who.campaign_id)
        who = builder_services.authority(campaign_id, user_id)
        cached = builder_services.replay(campaign_id, user_id, request_id, digest)
        if cached is not None:
            return cached
        row = BlueprintTemplate.objects.filter(pk=template_id).first()
        if row is not None and row.campaign_id != who.campaign_id:
            raise services.MapError("Blueprint template not found.", "not_found")
        if delete and row is None:
            raise services.MapError("Blueprint template not found.", "not_found")
        builder_services.expected(payload["expected_version"], row)
        if delete:
            row.delete()
            result = {"deleted": str(template_id)}
        else:
            name = _text(payload["name"], 120)
            description = _text(payload["description"], 2000, empty=True)
            definition = clean_definition(payload["definition"])
            if row is None:
                if BlueprintTemplate.objects.filter(campaign=who.campaign).count() >= MAX_TEMPLATES:
                    raise services.MapError("Blueprint template library limit reached.")
                row = BlueprintTemplate(id=template_id, campaign=who.campaign)
            else:
                row.version += 1
            row.name, row.description, row.definition = name, description, definition
            row.save()
            result = {"template": {**summary(row), "definition": deepcopy(row.definition)}}
        builder_services.record(campaign_id, user_id, request_id, digest, result)
    return result
