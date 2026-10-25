"""Authoritative effects and recipient-safe presentation for object blueprints."""

from copy import deepcopy
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import hmac
import json
import random
from uuid import UUID

from django.conf import settings

from .models import AutomationRun, MapAsset, MapBuilderProject, SceneObject
from .services import MapError
from .blueprint_world import world_operation


MIN_LEVER_DIMENSION = 0.001
MAX_LEVER_DIMENSION = 1_000_000
_rehearsal_scene = ContextVar("blueprint_rehearsal_scene", default=None)
_event_resources = ContextVar("blueprint_event_resources", default=None)


class _EventResources:
    """Immutable resource inventories reused only during one committed command.

    Actions can change object state, transforms, variables and membership. Those
    mutable rows still reload normally. They cannot edit Blueprint definitions,
    create assets/tracks or change their ownership inside an event chain.
    """

    def __init__(self, scene):
        self.scene = scene
        self.assets = None
        self.lights = None
        self.tracks = None
        self.blueprints = None
        self.appearances = {}
        self.notified = False
        self.shaders = None

    def shader_ids(self):
        if self.shaders is None:
            self.shaders = list(SceneObject.objects.filter(scene=self.scene, kind="shaders").values_list("pk", flat=True))
        return self.shaders

    def references(self):
        from gravewright.audio.models import Track
        if self.assets is None:
            self.assets = list(MapAsset.objects.filter(campaign_id=self.scene.campaign_id,
                generated_for__isnull=True).values_list("pk", flat=True))
            self.lights = list(SceneObject.objects.filter(scene=self.scene, kind="lights")
                               .values_list("pk", flat=True))
            self.tracks = {str(pk): label for pk, label in Track.objects.filter(
                campaign_id=self.scene.campaign_id).values_list("pk", "name")}
        return self.assets, self.lights, self.tracks

    def definitions(self):
        if self.blueprints is None:
            self.blueprints = [value for value in SceneObject.objects.filter(scene=self.scene,
                data__blueprint__isnull=False).values_list("data__blueprint", flat=True)
                if isinstance(value, dict)]
        return self.blueprints

    def asset(self, identifier):
        if identifier not in self.appearances:
            self.appearances[identifier] = MapAsset.objects.filter(pk=identifier,
                campaign_id=self.scene.campaign_id).first()
        return self.appearances[identifier]


def _resources_for(campaign_id, scene_id):
    active = _event_resources.get()
    return active if (active is not None and str(active.scene.pk) == str(scene_id)
                     and str(active.scene.campaign_id) == str(campaign_id)) else None


@contextmanager
def event_resources(scene):
    """Share read-only validation work until this presence pass or chain ends."""
    active = _resources_for(scene.campaign_id, scene.pk)
    if active is not None:
        yield active
        return
    marker = _event_resources.set(_EventResources(scene))
    try:
        yield _event_resources.get()
    finally:
        _event_resources.reset(marker)


@contextmanager
def rehearsal_scene(scene):
    """Evaluate a paused scene only inside the GM's rolled-back rehearsal."""
    marker = _rehearsal_scene.set(str(scene.pk))
    try:
        yield
    finally:
        _rehearsal_scene.reset(marker)


def clean_sprite(raw):
    """Return a valid live appearance chosen by Change Sprite, or ``None``."""
    if not isinstance(raw, dict) or raw.get("appearance") not in ("inherit", "hidden", "asset"):
        return None
    if raw["appearance"] != "asset":
        return None if set(raw) != {"appearance"} else {"appearance": raw["appearance"]}
    try:
        return {"appearance": "asset", "assetId": str(UUID(raw.get("assetId")))} if set(raw) == {"appearance", "assetId"} else None
    except (ValueError, TypeError, AttributeError):
        return None


def appearance(data):
    """Project only the active image, never another state's settings.

    A live ``sprite`` set by an explicit action replaces configured appearance
    until another visual action or the GM restores it.
    """
    state = data.get("door_state", "closed")
    blueprint = data.get("blueprint")
    config = {}
    if blueprint is not None:
        if not isinstance(blueprint, dict) or not isinstance(blueprint.get("states"), dict):
            return {"visible": False, "assetId": None}
        config = clean_sprite(data.get("sprite")) or blueprint["states"].get(state)
        if not isinstance(config, dict):
            return {"visible": False, "assetId": None}
    mode = config.get("appearance", "inherit")
    if mode not in ("hidden", "inherit", "asset"):
        return {"visible": False, "assetId": None}
    if mode == "hidden" or mode == "inherit" and state == "open" and "rotationAnchor" not in data:
        return {"visible": False, "assetId": None}
    asset_id = config.get("assetId") if mode == "asset" else data.get("asset_id")
    if asset_id is not None:
        try:
            asset_id = str(UUID(asset_id))
        except (ValueError, TypeError, AttributeError):
            return {"visible": False, "assetId": None}
    return {"visible": True, "assetId": asset_id}


def clean_native_blueprint(raw, campaign_id=None, scene_id=None, *, kind=None):
    """Validate native references and the capability of their owning element."""
    from gravewright.audio.models import Track
    from .blueprints import clean_blueprint

    resources = _resources_for(campaign_id, scene_id)
    if resources is not None:
        asset_ids, light_ids, track_ids = resources.references()
    else:
        asset_ids = (MapAsset.objects.filter(campaign_id=campaign_id, generated_for__isnull=True)
                     .values_list("pk", flat=True)) if campaign_id is not None else None
        light_ids = (SceneObject.objects.filter(scene_id=scene_id, kind="lights")
                     .values_list("pk", flat=True)) if scene_id is not None else None
        track_ids = Track.objects.filter(campaign_id=campaign_id).values_list("pk", flat=True) if campaign_id is not None else None
    uses_shaders = isinstance(raw, dict) and isinstance(raw.get("graphs"), dict) and any(
        isinstance(graph, dict) and isinstance(graph.get("nodes"), list)
        and any(isinstance(node, dict) and node.get("type") == "shaderControl" for node in graph["nodes"])
        for graph in raw["graphs"].values())
    shader_ids = (resources.shader_ids() if resources is not None else
                  SceneObject.objects.filter(scene_id=scene_id, kind="shaders").values_list("pk", flat=True)) if uses_shaders and scene_id is not None else None
    result = clean_blueprint(raw, asset_ids=asset_ids, light_ids=light_ids, track_ids=track_ids, shader_ids=shader_ids)
    if kind is not None and result["kind"] != kind:
        raise MapError("Unsupported blueprint version or object kind.")
    validate_reference_ownership(result, campaign_id=campaign_id, scene_id=scene_id)
    if scene_id is not None:
        from .blueprint_variables import validate_definitions
        from .models import Scene
        scene = resources.scene if resources is not None else Scene.objects.get(pk=scene_id)
        other = resources.definitions() if resources is not None else [value for value in SceneObject.objects.filter(scene_id=scene_id,
                 data__blueprint__isnull=False).values_list("data__blueprint", flat=True)
                 if isinstance(value, dict)]
        validate_definitions([result, *other], scene.settings.get("automationVariables", {}))
    return result


def validate_reference_ownership(blueprint, *, campaign_id=None, scene_id=None):
    """Missing authored bindings remain inert; existing foreign resources are rejected."""
    from gravewright.audio.models import Track
    from .blueprint_actions import movable
    ids = {"element": set(), "light": set(), "sound": set()}
    for graph in blueprint.get("graphs", {}).values():
        for node in graph["nodes"]:
            if node["type"] == "elementGroup":
                ids[node["memberType"]].update(node["targetIds"])
            elif node["type"] == "lightReference":
                ids["light"].add(node["targetId"])
            elif node["type"] == "soundReference":
                ids["sound"].add(node["trackId"])
    for kind in ("element", "light"):
        for row in SceneObject.objects.filter(pk__in=ids[kind]).select_related("scene"):
            if (campaign_id is not None and str(row.scene.campaign_id) != str(campaign_id)
                    or scene_id is not None and str(row.scene_id) != str(scene_id)
                    or (row.kind == "lights") != (kind == "light") or not movable(row)):
                raise MapError("Choose a blueprint reference from this scene.")
    if campaign_id is not None and Track.objects.filter(pk__in=ids["sound"]).exclude(campaign_id=campaign_id).exists():
        raise MapError("Choose a sound from this campaign.")
    nodes = [node for graph in blueprint.get("graphs", {}).values() for node in graph["nodes"]]
    for shader in SceneObject.objects.filter(pk__in=[node["targetId"] for node in nodes if node["type"] == "shaderControl"]).select_related("scene"):
        if (shader.kind != "shaders" or campaign_id is not None and str(shader.scene.campaign_id) != str(campaign_id)
                or scene_id is not None and str(shader.scene_id) != str(scene_id)):
            raise MapError("Choose a shader from this scene.")
    from .blueprint_clocks import validate_clock_references
    validate_clock_references([node['clockId'] for node in nodes if node['type'] == 'clockControl'],
                              campaign_id=campaign_id, scene_id=scene_id)
    from .blueprint_clues import validate_clue_references
    validate_clue_references([node['clueId'] for node in nodes if node['type'] == 'clueControl'],
                             campaign_id=campaign_id, scene_id=scene_id)
    from .blueprint_mindmaps import validate_mindmap_references
    validate_mindmap_references([node for node in nodes if node['type'] in ('openMindMap', 'mindMapNode')],
                                campaign_id=campaign_id, scene_id=scene_id)
    destinations = [node["destinationId"] for node in nodes if node["type"] == "teleport"]
    for row in SceneObject.objects.filter(pk__in=destinations).select_related("scene"):
        if (campaign_id is not None and str(row.scene.campaign_id) != str(campaign_id)
                or scene_id is not None and str(row.scene_id) != str(scene_id)
                or row.kind != "zones" or not isinstance(row.data.get("region"), dict)):
            raise MapError("Choose a teleport destination from this scene.")
    if campaign_id is not None:
        from gravewright.journals.models import Journal
        handouts = [node["journalId"] for node in nodes if node["type"] == "showHandout"]
        if Journal.objects.filter(pk__in=handouts).exclude(campaign_id=campaign_id).exists():
            raise MapError("Choose a handout from this campaign.")
        quests = [node["journalId"] for node in nodes if node["type"] == "setQuestStatus"]
        if Journal.objects.filter(pk__in=quests).exclude(campaign_id=campaign_id, type="quest").exists():
            raise MapError("Choose a quest from this campaign.")


def detach_blueprint_art(blueprint, asset_id):
    """Drop a deleted image from states and Change Sprite nodes, keeping graphs."""
    if not isinstance(blueprint, dict):
        return False
    from .blueprints import clean_blueprint
    normalized = clean_blueprint(blueprint)
    changed = normalized != blueprint
    if changed:
        blueprint.clear()
        blueprint.update(normalized)
    entries = list(blueprint.get("states", {}).values())
    for graph in blueprint.get("graphs", {}).values():
        entries.extend(node for node in graph.get("nodes", []) if node.get("type") == "sprite")
    for entry in entries:
        if entry.get("appearance") == "asset" and entry.get("assetId") == str(asset_id):
            entry.pop("assetId", None)
            entry["appearance"] = "inherit"
            changed = True
    changed = _detach_action(blueprint, ("setAppearance",), "assetId", asset_id) or changed
    return changed


def replacement_lever_asset(blueprint, asset_id, available):
    """Choose an existing state image when a lever's authored image is deleted."""
    states = blueprint.get("states", {}) if isinstance(blueprint, dict) else {}
    return next((state["assetId"] for state in states.values()
                 if state.get("appearance") == "asset" and state.get("assetId") != str(asset_id)
                 and state.get("assetId") in available), None)


def detach_scene_art(campaign_id, asset_id):
    """Clean native state, node and live sprite images before the file is removed."""
    from django.db.models import Q
    scenes = set()
    available = {str(pk) for pk in MapAsset.objects.filter(campaign_id=campaign_id).exclude(pk=asset_id)
                 .values_list("pk", flat=True)}
    for obj in SceneObject.objects.filter(scene__campaign_id=campaign_id, kind__in=("walls", "images", "zones")).filter(
            Q(data__blueprint__isnull=False) | Q(kind="images", data__surface__materialId=str(asset_id))
            | Q(kind="images", data__sprite__isnull=False) | Q(kind="images", data__spriteBase__isnull=False)):
        changed = detach_blueprint_art(obj.data.get("blueprint"), asset_id)
        if isinstance(obj.data.get("surface"), dict) and obj.data["surface"].get("materialId") == str(asset_id):
            obj.data["surface"].pop("materialId", None)
            obj.data["surface"].pop("materialCrop", None)
            changed = True
        if isinstance(obj.data.get("sprite"), dict) and obj.data["sprite"].get("assetId") == str(asset_id):
            if "spriteBase" in obj.data and obj.data["spriteBase"]["assetId"] != str(asset_id):
                from .blueprint_actions import change_sprite
                change_sprite(obj.scene, obj, {"appearance": "inherit"})
            else:
                obj.data.pop("sprite")
            changed = True
        element_key = "torch" if "torch" in obj.data else "lever"
        if isinstance(obj.data.get(element_key), dict) and obj.data[element_key].get("baseAssetId") == str(asset_id):
            replacement = replacement_lever_asset(obj.data.get("blueprint"), asset_id, available)
            if replacement is not None:
                obj.data[element_key]["baseAssetId"] = replacement
                changed = True
        if (isinstance(obj.data.get(element_key), dict) and obj.data[element_key].get("baseAssetId") != str(asset_id)
                and (changed or obj.data.get("asset_id") == str(asset_id))):
            # A lever showing the deleted state image returns to its authored image
            # instead of being removed with the image's placements.
            before = obj.data.get("asset_id")
            apply_lever_appearance(obj)
            changed = changed or obj.data.get("asset_id") != before
        if changed:
            obj.version += 1
            obj.save(update_fields=["data", "version"])
            scenes.add(obj.scene_id)
    return scenes


def _detach_action(blueprint, kinds, target_key, target_id):
    """Remove deleted actions of the given types and reconnect their continuations."""
    if not isinstance(blueprint, dict):
        return False
    from .blueprints import clean_blueprint
    normalized = clean_blueprint(blueprint)
    normalized_changed = normalized != blueprint
    if normalized_changed:
        blueprint.clear()
        blueprint.update(normalized)
    if blueprint.get("version") == 2:
        from .blueprints import MAX_GRAPH_EDGES
        candidate = deepcopy(blueprint)
        changed = normalized_changed
        for graph in candidate.get("graphs", {}).values():
            removed = [node["id"] for node in graph["nodes"]
                       if node.get("type") in kinds and node.get(target_key) == str(target_id)]
            for node_id in removed:
                outgoing = [edge for edge in graph["edges"] if edge["from"] == node_id and edge.get("kind") != "data"]
                kept = []
                for edge in graph["edges"]:
                    if edge["from"] == node_id:
                        continue
                    replacement = ([{**edge, "to": after["to"]} for after in outgoing] if edge.get("kind") != "data" else []) if edge["to"] == node_id else [edge]
                    for bridge in replacement:
                        if bridge not in kept:
                            kept.append(bridge)
                graph["edges"] = kept
                graph["nodes"] = [node for node in graph["nodes"] if node["id"] != node_id]
                changed = True
            if len(graph["edges"]) > MAX_GRAPH_EDGES:
                raise MapError("The blueprint has too many nodes or connections.")
        if changed:
            blueprint.clear()
            blueprint.update(candidate)
        return changed
    changed = False
    for graph in blueprint.get("graphs", {}).values():
        removed = [node["id"] for node in graph["nodes"]
                   if node.get("type") in kinds and node.get(target_key) == str(target_id)]
        for node_id in removed:
            incoming = [edge for edge in graph["edges"] if edge["to"] == node_id]
            outgoing = [edge for edge in graph["edges"] if edge["from"] == node_id]
            kept = [edge for edge in graph["edges"] if node_id not in (edge["from"], edge["to"])]
            for before in incoming:
                for after in outgoing:
                    bridge = {"from": before["from"], "to": after["to"], "output": before["output"]}
                    if bridge not in kept:
                        kept.append(bridge)
            graph["edges"] = kept
            graph["nodes"] = [node for node in graph["nodes"] if node["id"] != node_id]
            changed = True
    return changed


def detach_blueprint_sound(blueprint, track_id):
    return _detach_action(blueprint, ("sound", "soundControl"), "trackId", track_id)


def detach_blueprint_light(blueprint, light_id):
    return _detach_action(blueprint, ("light",), "targetId", light_id)


def detach_scene_shaders(scene_id, shader_ids):
    """Remove deleted shader actions while retaining execution continuations."""
    for row in SceneObject.objects.filter(scene_id=scene_id,data__blueprint__isnull=False):
        changed=False
        for shader_id in shader_ids:
            changed=_detach_action(row.data["blueprint"],("shaderControl",),"targetId",str(shader_id)) or changed
        if changed:
            row.version+=1
            row.save(update_fields=["data","version"])


def detach_scene_sound(campaign_id, track_id):
    for obj in SceneObject.objects.filter(scene__campaign_id=campaign_id, kind__in=("walls", "images", "zones"),
                                          data__blueprint__isnull=False):
        if detach_blueprint_sound(obj.data.get("blueprint"), track_id):
            obj.version += 1
            obj.save(update_fields=["data", "version"])


def detach_scene_lights(scene_id, light_ids):
    """Remove targets before native deletion; the deleted owned row still conflicts.

    Only known reference cleanup is mirrored in builder snapshots. The source
    document is untouched, so a manual deletion cannot silently redefine it.
    """
    light_ids = {str(pk) for pk in light_ids}
    if not light_ids:
        return
    for obj in SceneObject.objects.filter(scene_id=scene_id, kind__in=("walls", "images", "zones"),
                                          data__blueprint__isnull=False):
        changed = False
        for light_id in light_ids:
            changed = detach_blueprint_light(obj.data.get("blueprint"), light_id) or changed
        if changed:
            obj.version += 1
            obj.save(update_fields=["data", "version"])
    for source in MapBuilderProject.objects.filter(scene_id=scene_id):
        if not isinstance(source.generation, dict) or not isinstance(source.generation.get("objects"), list):
            continue
        changed = False
        for row in source.generation.get("objects", []):
            if not isinstance(row, dict):
                continue
            for light_id in light_ids:
                changed = detach_blueprint_light(row.get("data", {}).get("blueprint"), light_id) or changed
        if changed:
            source.save(update_fields=["generation"])


def _remember_effects(scene, changes):
    """Acknowledge only effects whose prior snapshot still matches the scene.

    A manual edit before an effect must remain a regeneration conflict; changing
    one known enabled flag cannot adopt unrelated edits into builder ownership.
    """
    if not changes:
        return
    for source in MapBuilderProject.objects.filter(scene=scene):
        manifest = deepcopy(source.generation)
        if (not isinstance(manifest, dict) or manifest.get("sceneId") != str(scene.pk)
                or not isinstance(manifest.get("objects"), list)):
            continue
        changed = False
        for row in manifest.get("objects", []):
            if not isinstance(row, dict):
                continue
            before_after = changes.get(row.get("id"))
            if before_after and row.get("kind") in ("lights", "shaders") and row.get("data") == before_after[0]:
                row["data"] = deepcopy(before_after[1])
                changed = True
        if changed:
            source.generation = manifest
            source.save(update_fields=["generation"])


RUN_HISTORY = 50


def _random_draw(request_id, ordinal, element_id, event, node_id, total, root_ordinal=0):
    """Stable private draws across retries, without revealing the server seed."""
    identity = json.dumps([str(request_id), root_ordinal, ordinal, element_id, event, node_id],
                          separators=(",", ":"), ensure_ascii=True).encode("ascii")
    seed = hmac.new(settings.SECRET_KEY.encode("utf-8"), identity, hashlib.sha256).digest()
    return random.Random(seed).randrange(total)


def _steps(graph, result, sound_names):
    """Summarize executed nodes with the parameters and outcomes a GM needs."""
    nodes = {node["id"]: node for node in graph["nodes"]}
    event = next(node["event"] for node in graph["nodes"] if node["type"] == "event")
    steps = []
    for identifier in result["trace"]:
        node = nodes[identifier]
        step = {"id": identifier, "type": node["type"]}
        if node["type"] == "state":
            step["state"] = node["targetState"]
        elif node["type"] == "sound":
            step.update(sound=sound_names.get(node["trackId"], ""), volume=node["volume"])
        elif node["type"] == "shaderControl":
            action=next((action for action in result["actions"] if action["id"]==identifier),node)
            step.update(targetIds=[node["targetId"]], property=node["property"], value=action["value"])
        elif node["type"] in ("light", "flame"):
            step["enabled"] = node["enabled"]
        elif node["type"] == "sprite":
            step["appearance"] = node["appearance"]
        elif node["type"] == "condition":
            step["result"] = result["decisions"][identifier]
        elif node["type"] in ("counter", "once", "cooldown"):
            step["result"] = result["decisions"][identifier]
            step["value"] = result["memory"][event][identifier]["value"]
            for key in ("target", "seconds"):
                if key in node:
                    step[key] = node[key]
        elif node["type"] == "delay":
            step["seconds"] = node["seconds"]
        elif node["type"] == "timer":
            step.update(name=node["name"], action=node["action"])
            if "seconds" in node:
                step["seconds"] = node["seconds"]
        elif node["type"] == "switch":
            source = next((edge["from"] for edge in graph["edges"] if edge.get("kind") == "data"
                           and edge["to"] == identifier and edge["input"] == "value"), None)
            step.update(output=result["decisions"][identifier], valueType=node["valueType"],
                        value=result["values"][source] if source else node["value"])
        elif node["type"] == "random":
            output = result["decisions"][identifier]
            step.update(output=output, weight=node["weights"][int(output[6:]) - 1], total=sum(node["weights"]))
        elif node["type"] == "elementGroup":
            step.update(name=node["name"], memberType=node["memberType"], count=len(node["targetIds"]))
        elif node["type"] == "eventContext":
            step.update(property=node["property"], value=result["values"][identifier])
        elif node["type"] in ("move", "rotate"):
            step.update({key: node[key] for key in ("dx", "dy", "degrees") if key in node})
        elif node["type"] in ("setInteraction", "setRegion"):
            step["enabled"] = node["enabled"]
        elif node["type"] == "setVisibility":
            step["visible"] = node["visible"]
        elif node["type"] == "setAppearance":
            step["assetId"] = node["assetId"]
        elif node["type"] in ("showMessage", "showHandout", "requestRoll", "cameraFocus", "openMindMap"):
            step["audience"] = deepcopy(node["audience"])
            step.update({key: node[key] for key in ("text", "journalId", "expression", "label", "visibility", "focusX", "focusY", "mindMapId", "nodeId") if key in node})
        elif node["type"] == "setQuestStatus":
            step.update(journalId=node["journalId"], status=node["status"])
        elif node['type'] == 'mindMapNode':
            step.update(mindMapId=node['mindMapId'], nodeId=node['nodeId'], action=node['action'])
        elif node['type'] == 'clockControl':
            action = next(action for action in result['actions'] if action['id'] == identifier)
            step.update(clockId=action['clockId'], action=action['action'], amount=action['amount'])
        elif node['type'] == 'clueControl':
            action = next(action for action in result['actions'] if action['id'] == identifier)
            step.update(clueId=action['clueId'], action=action['action'], amount=action['amount'])
        elif node["type"] == "teleport":
            step["destinationId"] = node["destinationId"]
        elif node["type"] in ("lightReference", "soundReference"):
            step["targetIds"] = [node["targetId"] if node["type"] == "lightReference" else node["trackId"]]
            if node["type"] == "soundReference":
                step["sound"] = sound_names.get(node["trackId"], "")
        elif node["type"] in ("property", "compare", "all", "any", "getVariable", "compareValue"):
            step["value"] = result["values"][identifier]
            if node["type"] == "getVariable":
                step.update(scope=node["scope"], name=node["name"], valueType=node["valueType"])
        elif node["type"] == "setVariable":
            action = next(action for action in result["actions"] if action["id"] == identifier)
            step.update(scope=node["scope"], name=node["name"], valueType=node["valueType"], value=action["value"])
        elif node["type"] == "emitEvent":
            step.update(scope=node["scope"], name=node["name"])
        elif node["type"] == "reference":
            step["doorId"] = node["targetId"]
        elif node["type"] == "barrier":
            step.update(channel=node["channel"], mode=node["mode"])
        elif node["type"] == "soundControl":
            step.update(sound=sound_names.get(node["trackId"], ""), action=node["action"], volume=node["volume"])
        if node.get("players"):
            step["players"] = True
        steps.append(step)
    return steps


def door_point(data):
    """Scene point of an element: a door's midpoint or an image's centre."""
    if "region" in data:
        g = data["geometry"]
        if g["shape"] == "rect":
            return {"x": round(g["x"] + g["width"] / 2, 2), "y": round(g["y"] + g["height"] / 2, 2)}
        if g["shape"] == "circle":
            return {"x": round(g["x"], 2), "y": round(g["y"], 2)}
        return {axis: round(sum(p[axis] for p in g["points"]) / len(g["points"]), 2) for axis in ("x", "y")}
    if "x1" not in data:
        return {"x": round(data["x"], 2), "y": round(data["y"], 2)}
    return {"x": round((data["x1"] + data["x2"]) / 2, 2), "y": round((data["y1"] + data["y2"]) / 2, 2)}


def element_kind(row):
    return "door" if row.kind == "walls" else "region" if row.kind == "zones" else "torch" if "torch" in row.data else "lever"


def element_state(row):
    return row.data["door_state"] if row.kind == "walls" else row.data[element_kind(row)]["state"]


def set_element_state(row, state):
    if row.kind == "walls":
        row.data["door_state"] = state
    else:
        row.data[element_kind(row)]["state"] = state


def elements(scene):
    """Doors and levers of a scene; references and chains can target either."""
    from django.db.models import Q
    return SceneObject.objects.filter(scene=scene).filter(
        Q(kind="walls", data__kind="door") | Q(kind="images", data__lever__isnull=False)
        | Q(kind="images", data__torch__isnull=False) | Q(kind="zones", data__region__isnull=False))


def clean_lever(raw, *, empty=False):
    """Validate a native lever's live state and the authored box it keeps."""
    if not isinstance(raw, dict) or raw.get("state") not in ("off", "on"):
        raise MapError("Invalid lever.")
    from .objects import number
    from gravewright.journals.services import identifier
    layer = raw.get("baseLayer", "map")
    if layer not in ("map", "gm-image-layer"):
        raise MapError("Invalid lever.")
    if empty and raw.get("baseAssetId") is not None:
        raise MapError("An empty object cannot receive images.")
    return {"state": raw["state"], "baseAssetId": None if empty else str(identifier(raw.get("baseAssetId"))), "baseLayer": layer,
            "width": number(raw.get("width"), MIN_LEVER_DIMENSION, MAX_LEVER_DIMENSION),
            "height": number(raw.get("height"), MIN_LEVER_DIMENSION, MAX_LEVER_DIMENSION)}


def apply_lever_appearance(row):
    """Show a lever's active image: Change sprite, then the state's appearance.

    ``inherit`` keeps the authored image, ``hidden`` moves it to the GM layer and
    ``asset`` swaps the image while keeping the authored box, so players only
    ever receive the active image's asset.
    """
    lever = row.data[element_kind(row)]
    if row.data.get("empty") is True:
        # Visual actions cannot turn image-free controllers into visible art.
        row.data.update(asset_id=None, src="", natural_width=lever["width"],
                        natural_height=lever["height"], scale=1, layer="gm-image-layer")
        lever["baseLayer"] = "gm-image-layer"
        row.data.pop("sprite", None)
        return
    blueprint = row.data.get("blueprint") or {}
    config = clean_sprite(row.data.get("sprite")) or (blueprint.get("states") or {}).get(lever["state"]) or {}
    mode = config.get("appearance", "inherit")
    asset_id = config.get("assetId") if mode == "asset" else lever["baseAssetId"]
    resources = _event_resources.get()
    resources = resources if resources is not None and resources.scene.pk == row.scene_id else None

    def asset_for(identifier):
        return (resources.asset(identifier) if resources is not None else
                MapAsset.objects.filter(pk=identifier, campaign_id=row.scene.campaign_id).first())

    asset = asset_for(asset_id) if asset_id else None
    if asset is None:
        asset = asset_for(lever["baseAssetId"])
    if asset is not None:
        row.data.update(asset_id=str(asset.pk), src=f"/game/map-assets/{asset.pk}",
                        natural_width=asset.width, natural_height=asset.height,
                        scale=min(lever["width"] / asset.width, lever["height"] / asset.height))
    row.data["layer"] = "gm-image-layer" if mode == "hidden" else lever["baseLayer"]
    if "torch" in row.data:
        row.data["rotation"] = (lever["baseRotation"] + (90 if lever["state"] == "on" else 0)) % 360


def record_run(scene, who, door, outcome, run):
    """Store one run for the scene's GMs and keep only the most recent ones."""
    AutomationRun.objects.create(scene=scene, door_id=door.pk, outcome=outcome, data={
        **run, "actor": {"name": who.user.name, "role": who.role}, "point": door_point(door.data)})
    stale = list(AutomationRun.objects.filter(scene=scene).values_list("pk", flat=True)[RUN_HISTORY:])
    if stale:
        AutomationRun.objects.filter(pk__in=stale).delete()
    from django.db import transaction
    from gravewright.realtime.dispatch import send
    resources = _resources_for(scene.campaign_id, scene.pk)
    if resources is not None:
        if resources.notified:
            return
        resources.notified = True
    event = {"type": "room.automation", "sceneId": str(scene.pk)}
    transaction.on_commit(lambda: send(scene.campaign_id, event), robust=True)


def automation_runs(scene):
    """GM projection of recent runs, newest first."""
    return [{"id": str(row.pk), "doorId": str(row.door_id), "outcome": row.outcome,
             "createdAt": row.created_at.isoformat(), **row.data}
            for row in AutomationRun.objects.filter(scene=scene)[:RUN_HISTORY]]


def automation_paused(scene):
    """Suppress authored events outside a scene-scoped, rolled-back rehearsal."""
    return (_rehearsal_scene.get() != str(scene.pk)
            and isinstance(scene.settings, dict) and scene.settings.get("automationPaused") is True)


def automation_doors(scene):
    """GM summary of every door and lever in creation order; references can target any of them."""
    from .blueprints import clean_blueprint
    return [{"id": str(row.pk), "kind": element_kind(row), "state": element_state(row), "point": door_point(row.data),
             "automated": isinstance(row.data.get("blueprint"), dict),
             "sprite": clean_sprite(row.data.get("sprite")) is not None,
             **({"name": row.data["name"]} if row.data.get("name") else {}),
             **({"name": row.data["region"]["name"], "count": len(row.data["region"]["occupants"])}
                if element_kind(row) == "region" else {}),
             "events": sorted(clean_blueprint(row.data["blueprint"])["graphs"]) if row.data.get("blueprint") is not None else []}
            for row in elements(scene)]


def automation_variables(scene):
    """GM-only inspector; public scene and layer projections never include this."""
    from .blueprint_variables import clean_store
    return {"scene": clean_store(scene.settings.get("automationVariables", {})),
            "elements": {str(row.pk): clean_store(row.data["automationVariables"])
                         for row in elements(scene) if row.data.get("automationVariables")}}


def automation_memory(scene):
    """GM-only progress for nodes that still exist in the owning blueprint."""
    from .blueprint_memory import reconcile_memory
    result = {}
    for row in elements(scene):
        if row.data.get("automationMemory"):
            memory = reconcile_memory(row.data.get("blueprint") or {}, row.data["automationMemory"])
            if memory:
                result[str(row.pk)] = memory
    return {"elements": result}


def record_paused(scene, who, door, target):
    """Log an ignored event without executing any state or visual action."""
    before = element_state(door)
    record_run(scene, who, door, "paused",
               {"requested": target, "stateBefore": before, "stateAfter": target, "events": []})


def automation_command(scene, action, data):
    """GM controls for the scene's automation; the caller checks GM permission."""
    from django.db import transaction
    from gravewright.journals.services import identifier
    from gravewright.realtime.dispatch import send
    if action == "pause":
        paused = data.get("paused")
        if type(paused) is not bool:
            raise MapError("Invalid automation state.")
        settings_value = dict(scene.settings or {})
        if paused:
            settings_value["automationPaused"] = True
        else:
            settings_value.pop("automationPaused", None)
        scene.settings = settings_value
        scene.save(update_fields=["settings"])
        result = {"automationPaused": paused}
    elif action == "reset-variable":
        from .blueprint_variables import VARIABLE_SCOPES, clean_store, name
        scope, key = data.get("scope"), name(data.get("name"))
        if scope not in VARIABLE_SCOPES:
            raise MapError("Invalid blueprint variable scope.")
        expected = clean_store({key: data.get("expected")})[key]
        if scope == "scene":
            owner, field = scene, "settings"
        else:
            owner = elements(scene).filter(pk=identifier(data.get("elementId"))).first()
            if owner is None:
                raise MapError("Choose an element from this scene.")
            field = "data"
        state = deepcopy(getattr(owner, field))
        store = clean_store(state.get("automationVariables", {}))
        if key not in store or store[key] != expected:
            raise MapError("This variable changed. Refresh before resetting it.", "conflict")
        store.pop(key)
        if store:
            state["automationVariables"] = store
        else:
            state.pop("automationVariables", None)
        setattr(owner, field, state)
        if scope == "element":
            owner.version += 1
        owner.save(update_fields=[field, *(["version"] if scope == "element" else [])])
        result = {"variables": automation_variables(scene)}
    elif action == "cancel-delay":
        from .blueprint_delays import cancel_delay
        return cancel_delay(scene, data)
    elif action == "restart-timer":
        from .blueprint_delays import restart_timer
        return restart_timer(scene, data)
    elif action == "reset-memory":
        from .blueprint_memory import clean_memory, reconcile_memory
        event, node_id = data.get("event"), data.get("nodeId")
        if not isinstance(event, str) or not isinstance(node_id, str):
            raise MapError("Invalid blueprint control memory.")
        expected = clean_memory({event: {node_id: data.get("expected")}})[event][node_id]
        owner = elements(scene).filter(pk=identifier(data.get("elementId"))).first()
        if owner is None:
            raise MapError("Choose an element from this scene.")
        memory = reconcile_memory(owner.data.get("blueprint") or {}, owner.data.get("automationMemory", {}))
        if memory.get(event, {}).get(node_id) != expected:
            raise MapError("This control changed. Refresh before resetting it.", "conflict")
        del memory[event][node_id]
        if not memory[event]:
            del memory[event]
        if memory:
            owner.data["automationMemory"] = memory
        else:
            owner.data.pop("automationMemory", None)
        owner.version += 1
        owner.save(update_fields=["data", "version"])
        result = {"memory": automation_memory(scene)}
    elif action == "clear-sprite":
        door = elements(scene).filter(pk=identifier(data.get("wall_id"))).first()
        if door is None:
            raise MapError("Choose a door.")
        if "sprite" in door.data:
            previous = deepcopy(door.data)
            door.data.pop("sprite")
            if door.kind == "images":
                apply_lever_appearance(door)
                if "torch" in door.data:
                    from .torches import sync_components
                    sync_components(door, previous, remember=True)
            door.version += 1
            door.save(update_fields=["data", "version"])
        result = {"wallId": str(door.pk), "sprite": False}
    else:
        raise MapError("Unknown automation command.")
    event = {"type": "room.automation", "sceneId": str(scene.pk)}
    transaction.on_commit(lambda: send(scene.campaign_id, event), robust=True)
    return result


MAX_CHAIN_OPERATIONS = 32
# Scene-scope signal receivers use their own budget: one broadcast may reach
# many listeners without repeating anything. The per-element bound still
# detects repetition and the action bound still caps total work.
MAX_BROADCAST_DELIVERIES = 256
MAX_ELEMENT_OPERATIONS = 4
REFUSED = "This door cannot be operated."


@world_operation
def operate(scene, who, obj, target, *, interact=True, presence_event=None, context=None, resume=None,
            trigger_event=None, skip_unbound_teleport=False):
    """Run an authoritative event chain with disposable validation resources."""
    with event_resources(scene):
        return _operate(scene, who, obj, target, interact=interact, presence_event=presence_event,
                        context=context, resume=resume, trigger_event=trigger_event,
                        skip_unbound_teleport=skip_unbound_teleport)


def _operate(scene, who, obj, target, *, interact=True, presence_event=None, context=None, resume=None,
             trigger_event=None, skip_unbound_teleport=False):
    """Execute one door command as a bounded chain inside the caller's transaction.

    The base event starts one graph. Actions, including state and visual changes
    to other elements, apply in authored order without implicit state hooks.
    Named signals queue fresh events after that graph. Exceeding a chain bound
    fails the whole command. Player lock changes require an authorized action.
    The completed run is recorded in the same transaction. A failure
    attaches its partial run to the raised error so the caller can record it
    after the rollback without keeping any of the failed effects.
    """
    from collections import deque
    from gravewright.audio.models import Track
    from gravewright.audio.services import control_effects, play_effects
    from .blueprints import KIND_STATES, data_outputs, evaluate_graph
    from .blueprint_actions import change_visual, intelligent, live_objects, transform
    from .blueprint_world import present, teleport
    from .blueprint_context import trigger_context
    from .blueprint_memory import reconcile_memory
    from .blueprint_variables import assign, clean_store, snapshot, validate_element_store
    from django.utils import timezone
    from .blueprint_delays import (MAX_DELAY_RESUMPTIONS, control_timer, current_request_id,
                                   next_chain_ordinal, schedule_delay, update_chain_budget)
    import uuid

    now = int(timezone.now().timestamp() * 1000)

    if automation_paused(scene) and (interact or trigger_event is not None or presence_event is not None or resume is not None):
        record_paused(scene, who, obj, element_state(obj))
        return {"blueprintAudioChanged": False, "blocked": False, "blueprint": {"state": element_state(obj), "trace": []}}

    native = {str(row.pk): row for row in live_objects(scene)}
    for row in native.values():
        row.scene = scene
    obj.scene = scene
    doors = {key: row for key, row in native.items() if intelligent(row)}
    doors[str(obj.pk)] = obj
    native[str(obj.pk)] = obj
    root = str(obj.pk)
    # Audio operations keep their order: a sound can be played and then stopped.
    blueprints, sound_names, light_changes, audio, traces = {}, {}, {}, [], []
    inherited = deepcopy(resume.data["budget"]) if resume is not None else {}
    counters = {"actions": inherited.get("actions", 0), "operations": inherited.get("operations", 0),
                "deliveries": inherited.get("deliveries", 0),
                "delays": inherited.get("delays", 0) + int(resume is not None),
                "randomDraws": inherited.get("randomDraws", 0),
                "randomRoot": inherited.get("randomRoot", 0) if resume is not None else next_chain_ordinal()}
    if any(type(counters[key]) is not int or not 0 <= counters[key] <= 1_000_000
           for key in ("randomDraws", "randomRoot")):
        raise MapError("Invalid blueprint random state.")
    if counters["delays"] > MAX_DELAY_RESUMPTIONS:
        raise MapError("The blueprint exceeded its delay continuation limit.")
    chain_id = resume.chain_id if resume is not None else uuid.uuid4()
    request_id = resume.request_id if resume is not None else current_request_id()
    waits = []
    timers_scheduled = False
    saved_data, torch_synced = {}, {}
    scene_variables = clean_store(scene.settings.get("automationVariables", {}))
    initial_scene_variables = deepcopy(scene_variables)
    per_door, initial, queue = inherited.get("perElement", {}), {}, deque()
    run = {"requested": target, "stateBefore": element_state(obj), "events": []}
    if context is not None:
        run["context"] = deepcopy(context)
    if resume is not None:
        run["delayId"] = str(resume.pk)
        if resume.kind == "timer":
            run["timerName"] = resume.name
        context = deepcopy(resume.data.get("context"))
        if context is not None:
            run["context"] = context
    context = trigger_context(who, root, context, resumed=resume is not None)
    resources = _resources_for(scene.campaign_id, scene.pk)
    torch_lights = None

    def known_track(identifier):
        # The chain's shared inventory already lists every campaign track.
        try:
            return str(uuid.UUID(str(identifier))) in resources.references()[2]
        except ValueError:
            return False

    def light_owner(name):
        # Torch sync moves and gates its children but never relinks them, so
        # one light-to-torch index serves every light action in the chain.
        nonlocal torch_lights
        if torch_lights is None:
            torch_lights = {}
            for candidate in doors.values():
                identifier = candidate.data.get("torch", {}).get("components", {}).get("lights", {}).get("id")
                if identifier is not None:
                    torch_lights.setdefault(identifier, candidate)
        return torch_lights.get(name)

    def shader_owner(name):
        return next((candidate for candidate in doors.values()
                     if candidate.data.get("torch", {}).get("components", {}).get("shaders", {}).get("id") == name), None)

    def blueprint_of(key):
        if key not in blueprints:
            source = doors[key].data.get("blueprint")
            blueprints[key] = clean_native_blueprint(source, scene.campaign_id, scene.pk,
                kind=element_kind(doors[key])) if source is not None else None
            if blueprints[key] is not None:
                validate_element_store(blueprints[key], doors[key].data.get("automationVariables", {}))
                reconcile_memory(blueprints[key], doors[key].data.get("automationMemory", {}))
                sound_names.update(_resources_for(scene.campaign_id, scene.pk).references()[2])
            missing = {node["trackId"] for graph in (blueprints[key] or {}).get("graphs", {}).values()
                       for node in graph["nodes"] if node["type"] in ("sound", "soundControl", "soundReference")} - set(sound_names)
            missing.update(identifier for graph in (blueprints[key] or {}).get("graphs", {}).values()
                           for node in graph["nodes"] if node["type"] == "elementGroup" and node["memberType"] == "sound"
                           for identifier in node["targetIds"] if identifier not in sound_names)
            if missing:
                sound_names.update({str(pk): name for pk, name in Track.objects.filter(
                    campaign_id=scene.campaign_id, pk__in=missing).values_list("pk", "name")})
        return blueprints[key]

    def touch(key):
        initial.setdefault(key, deepcopy(native[key].data))

    def reveal(key):
        door = doors[key]
        if door.kind != "walls":
            return False
        touch(key)
        if door.data.get("presentation") in ("secret", "invisible"):
            door.data["discovered"] = True
        return True

    def set_barrier(key, channel, mode):
        door = doors[key]
        if door.kind != "walls":
            return False
        touch(key)
        door.data[f"{channel}_behavior"] = mode
        if channel == "light":
            door.data["blocks_light"] = int(mode == "block")
        elif channel == "vision":
            door.data["blocks_sight"] = int(mode == "block")
        return True

    def operate_door(key, desired, *, interact, first, allowed=False, signal=None, checkpoint=None,
                     broadcast=False):
        door = doors[key]
        if checkpoint is None:
            budget = "deliveries" if broadcast else "operations"
            counters[budget] += 1
            per_door[key] = per_door.get(key, 0) + 1
            # Repetition is checked first: it is the specific cause of a loop,
            # while the chain bounds describe a long or wide but finite chain.
            if per_door[key] > MAX_ELEMENT_OPERATIONS:
                raise MapError("The object blueprints form a repeating chain: one element ran more than 4 times.")
            if broadcast and counters[budget] > MAX_BROADCAST_DELIVERIES:
                raise MapError("A scene signal reached more than 256 receiving elements in one chain.")
            if not broadcast and counters[budget] > MAX_CHAIN_OPERATIONS:
                raise MapError("The object blueprint chain exceeded 32 element operations.")
        touch(key)
        blueprint = blueprint_of(key)
        kind = element_kind(door)
        # Lock rules belong to doors; levers have no locked state.
        player = who.role != "gm" and kind == "door"
        state, sprite = element_state(door), clean_sprite(door.data.get("sprite"))
        label = {} if first else {"doorId": key}

        def change_state(identifier, target_state, authorized=False):
            nonlocal state
            candidate = doors[identifier]
            before, candidate_kind = element_state(candidate), element_kind(candidate)
            if candidate_kind == "region" or target_state not in KIND_STATES[candidate_kind]:
                return False
            if who.role != "gm" and candidate_kind == "door" and before != target_state and (
                    before == "locked" or target_state == "locked") and not authorized:
                if first and identifier == root:
                    raise MapError(REFUSED)
                run["events"].append({"doorId": identifier, "event": "refused", "message": REFUSED, "steps": []})
                return False
            touch(identifier)
            set_element_state(candidate, target_state)
            if identifier == key:
                state = target_state
            return True

        def graph(event, previous=None, continuation=None):
            nonlocal sprite, timers_scheduled, state
            if blueprint is None:
                return None, False
            states = {name: element_state(row) for name, row in doors.items()}
            states[key] = state
            variables = snapshot(door, scene)
            variables["scene"] = deepcopy(scene_variables)

            def draw(node_id, total):
                ordinal = counters["randomDraws"]
                if ordinal >= 1_000_000:
                    raise MapError("Invalid blueprint random state.")
                counters["randomDraws"] += 1
                return _random_draw(request_id, ordinal, key, event, node_id, total, counters["randomRoot"])

            result = evaluate_graph(blueprint, event, state, previous, states, variables=variables,
                                    memory=door.data.get("automationMemory", {}), now=now,
                                    continuation=continuation, random_draw=draw, event_context=context)
            if "delay" in result:
                waits.append((key, event, result["delay"]))
            if result["memory"]:
                door.data["automationMemory"] = result["memory"]
            else:
                door.data.pop("automationMemory", None)
            traces.append({"event": event, "nodes": result["trace"], **label})
            # Log the event before its actions so a failing action keeps the steps reached.
            steps = _steps(blueprint["graphs"][event], result, sound_names) if event in blueprint["graphs"] else None
            if steps is not None:
                run["events"].append({**label, "event": event, **({"previous": previous} if previous else {}),
                                      "steps": steps})
            requested, authorized, missing, aimed, unsupported = None, False, set(), {}, set()
            applied, missing_ids, unsupported_ids, world_results = {}, {}, {}, {}

            def mark_unsupported(node, identifier):
                unsupported.add(node["id"])
                unsupported_ids.setdefault(node["id"], []).append(identifier)

            authored = {node["id"]: node for node in blueprint["graphs"].get(event, {"nodes": []})["nodes"]}
            target_types = {edge["to"]: data_outputs(authored[edge["from"]])[edge["output"]]
                            for edge in blueprint["graphs"].get(event, {"edges": []})["edges"]
                            if edge.get("kind") == "data" and edge["input"] == "target"}
            actions = []
            for node in result["actions"]:
                if node["type"] == "emitEvent" and node["scope"] == "scene":
                    # Legacy graphs may connect Target here; scene scope still
                    # means one broadcast, regardless of a connected set.
                    actions.append({field: value for field, value in node.items() if field != "target"})
                elif isinstance(node.get("target"), list):
                    actions.extend({**node, "target": identifier} for identifier in node["target"])
                else:
                    actions.append(node)
            for node in actions:
                counters["actions"] += 1
                if counters["actions"] > 1024:
                    raise MapError("The object blueprint executed too many actions.")
                if node["type"] == "shaderControl":
                    from .extra_objects import effect
                    from .shader_controls import clean_value
                    shader = SceneObject.objects.filter(scene=scene, kind="shaders", pk=node["targetId"]).first()
                    if shader is None:
                        missing.add(node["id"])
                        continue
                    name = str(shader.pk)
                    light_changes.setdefault(name, [deepcopy(shader.data), None])
                    value = clean_value(node["property"], node["value"])
                    shader.data = effect("shaders", {node["property"]: value}, shader.data)
                    owner = shader_owner(name)
                    if owner is not None:
                        touch(str(owner.pk))
                        link = owner.data["torch"]["components"]["shaders"]
                        if node["property"] == "enabled":
                            link["enabled"] = value
                        shader.data["enabled"] = owner.data["torch"]["lit"] and link["enabled"] and owner.data.get("layer") != "gm-image-layer"
                    light_changes[name][1] = deepcopy(shader.data)
                    shader.version += 1
                    shader.save(update_fields=["data", "version"])
                    applied.setdefault(node["id"], []).append(name)
                    continue
                aim = node.get("target")
                target_type = target_types.get(node["id"])
                if aim is not None and target_type not in ("sound", "soundset"):
                    candidate = native.get(aim)
                    if candidate is None:
                        missing.add(node["id"])
                        missing_ids.setdefault(node["id"], []).append(aim)
                        continue
                    if (target_type in ("light", "lightset")) != (candidate.kind == "lights"):
                        mark_unsupported(node, aim or key)
                        continue
                if node["type"] in ("showMessage", "showHandout", "requestRoll", "cameraFocus", "openMindMap"):
                    world_results[node["id"]] = {"recipients": present(scene, who, node, context)}
                    continue
                if node["type"] == "setQuestStatus":
                    from .blueprint_world import set_quest_status
                    world_results[node["id"]] = set_quest_status(scene, who, node)
                    continue
                if node['type'] == 'mindMapNode':
                    from .blueprint_mindmaps import control_node
                    world_results[node['id']] = control_node(scene, who, node)
                    continue
                if node['type'] == 'clockControl':
                    from .blueprint_clocks import control_clock
                    world_results[node['id']] = control_clock(scene, who, node)
                    continue
                if node['type'] == 'clueControl':
                    from .blueprint_clues import control_clue
                    world_results[node['id']] = control_clue(scene, who, node)
                    continue
                if node["type"] == "teleport":
                    if skip_unbound_teleport and not context.get("tokenId"):
                        world_results[node["id"]] = {"skipped": "missing-test-token"}
                        continue
                    world_results[node["id"]] = teleport(scene, who, node, context)
                    continue
                if node["type"] in ("sprite", "setVisibility", "setAppearance"):
                    identifier = aim or key
                    candidate = native.get(identifier)
                    if candidate is None:
                        missing.add(node["id"])
                        continue
                    touch(identifier)
                    from .blueprint_actions import change_sprite
                    changed = change_sprite(scene, candidate, node) if node["type"] == "sprite" else change_visual(scene, candidate, node)
                    if changed:
                        applied.setdefault(node["id"], []).append(identifier)
                        if identifier == key:
                            sprite = clean_sprite(candidate.data.get("sprite"))
                    else:
                        mark_unsupported(node, aim or key)
                    continue
                if node["type"] in ("move", "rotate"):
                    identifier = aim or key
                    candidate = native.get(identifier)
                    if candidate is None:
                        missing.add(node["id"])
                        continue
                    touch(identifier)
                    if candidate.kind == "lights":
                        candidate.refresh_from_db()
                    if transform(scene, who, candidate, node):
                        saved_data[identifier] = deepcopy(candidate.data)
                        if "torch" in candidate.data:
                            torch_synced[identifier] = deepcopy(candidate.data)
                        applied.setdefault(node["id"], []).append(identifier)
                        if identifier == key and kind == "region":
                            state = element_state(candidate)
                    else:
                        mark_unsupported(node, aim or key)
                    continue
                if node["type"] in ("setInteraction", "setRegion"):
                    identifier = aim or key
                    candidate = doors.get(identifier)
                    if candidate is None or (node["type"] == "setRegion") != (element_kind(candidate) == "region"):
                        mark_unsupported(node, aim or key)
                        continue
                    touch(identifier)
                    if node["type"] == "setRegion":
                        from .regions import set_enabled
                        set_enabled(scene, candidate, node["enabled"])
                        if identifier == key:
                            state = element_state(candidate)
                    else:
                        candidate.data["interactionEnabled"] = node["enabled"]
                    applied.setdefault(node["id"], []).append(identifier)
                    continue
                if node["type"] == "timer":
                    scheduled = control_timer(scene, who, door, event, node, chain_id=chain_id,
                        request_id=request_id, budget={**counters, "perElement": per_door}, context=context)
                    timers_scheduled = timers_scheduled or scheduled
                    continue
                if node["type"] == "setVariable":
                    if node["scope"] == "scene":
                        store = scene_variables
                    else:
                        store = door.data.setdefault("automationVariables", {})
                    assign(store, node["name"], node["valueType"], node["value"])
                    continue
                if node["type"] == "emitEvent":
                    event_name = "signal:" + node["name"]
                    recipients = ([aim or key] if node["scope"] == "element" else list(doors))
                    for recipient in recipients:
                        if recipient not in doors:
                            if recipient in native:
                                mark_unsupported(node, recipient)
                                continue
                            missing.add(node["id"])
                            continue
                        if node["scope"] == "element" and aim is not None:
                            aimed[node["id"]] = recipient
                        recipient_blueprint = blueprint_of(recipient)
                        applied.setdefault(node["id"], []).append(recipient)
                        if recipient_blueprint is not None and event_name in recipient_blueprint["graphs"]:
                            queue.append((recipient, None, False, event_name, node["scope"] == "scene"))
                    continue
                if node["type"] == "interact":
                    identifier = aim or key
                    candidate = doors.get(identifier)
                    if candidate is None or element_kind(candidate) == "region":
                        mark_unsupported(node, aim or key)
                        continue
                    # This explicit action starts the target's authored handler.
                    # Keep it in this chain's queue, budget and transaction rather
                    # than opening an independent runtime with fresh limits.
                    queue.append((identifier, None, False, "interact", False))
                    aimed[node["id"]] = identifier
                    applied.setdefault(node["id"], []).append(identifier)
                    continue
                if node["type"] in ("state", "reveal", "barrier", "flame") and aim is not None and aim != key:
                    if aim not in doors:
                        mark_unsupported(node, aim or key)
                        continue
                    aimed[node["id"]] = aim
                    if node["type"] == "state":
                        if change_state(aim, node["targetState"], node.get("players", False)):
                            applied.setdefault(node["id"], []).append(aim)
                        else:
                            mark_unsupported(node, aim or key)
                    elif node["type"] == "flame":
                        if element_kind(doors[aim]) != "torch":
                            mark_unsupported(node, aim or key)
                        else:
                            touch(aim)
                            doors[aim].data["torch"]["lit"] = node["enabled"]
                            applied.setdefault(node["id"], []).append(aim)
                    elif (reveal(aim) if node["type"] == "reveal" else set_barrier(aim, node["channel"], node["mode"])):
                        applied.setdefault(node["id"], []).append(aim)
                    else:
                        mark_unsupported(node, aim or key)
                    continue
                if node["type"] == "state":
                    if change_state(key, node["targetState"], node.get("players", False)):
                        applied.setdefault(node["id"], []).append(key)
                    else:
                        mark_unsupported(node, aim or key)
                elif node["type"] == "reveal":
                    if reveal(key):
                        applied.setdefault(node["id"], []).append(key)
                    else:
                        mark_unsupported(node, aim or key)
                elif node["type"] == "barrier":
                    if set_barrier(key, node["channel"], node["mode"]):
                        applied.setdefault(node["id"], []).append(key)
                    else:
                        mark_unsupported(node, aim or key)
                elif node["type"] == "flame":
                    if kind == "torch":
                        door.data["torch"]["lit"] = node["enabled"]
                        applied.setdefault(node["id"], []).append(key)
                    else:
                        mark_unsupported(node, aim or key)
                elif node["type"] == "light":
                    if not settings.DYNAMIC_LIGHTING_ENABLED:
                        raise MapError("Dynamic lighting is disabled.", "forbidden")
                    light_id = aim if aim is not None else node["targetId"]
                    light = SceneObject.objects.filter(scene=scene, kind="lights", pk=light_id).first()
                    if light is None:
                        missing.add(node["id"])
                        missing_ids.setdefault(node["id"], []).append(light_id)
                        continue
                    name = str(light.pk)
                    if name not in light_changes:
                        light_changes[name] = [deepcopy(light.data), None]
                    light.data["enabled"] = node["enabled"]
                    owner = light_owner(name)
                    if owner is not None:
                        owner_key = str(owner.pk)
                        touch(owner_key)
                        owner.data["torch"]["components"]["lights"]["enabled"] = node["enabled"]
                        light.data["enabled"] = (owner.data["torch"]["lit"] and node["enabled"]
                                                 and owner.data.get("layer") != "gm-image-layer")
                    light_changes[name][1] = deepcopy(light.data)
                    light.version += 1
                    light.save(update_fields=["data", "version"])
                    native[name] = light
                    saved_data[name] = deepcopy(light.data)
                    applied.setdefault(node["id"], []).append(name)
                elif node["type"] == "sound":
                    track_id = aim if aim is not None else node["trackId"]
                    if not known_track(track_id):
                        missing.add(node["id"])
                        missing_ids.setdefault(node["id"], []).append(track_id)
                        continue
                    audio.append(("play", {"trackId": track_id, "volume": node["volume"]}))
                    applied.setdefault(node["id"], []).append(track_id)
                elif node["type"] == "soundControl":
                    track_id = aim if aim is not None else node["trackId"]
                    if not known_track(track_id):
                        missing.add(node["id"])
                        missing_ids.setdefault(node["id"], []).append(track_id)
                        continue
                    audio.append(("control", {"trackId": track_id, "action": node["action"], "volume": node["volume"]}))
                    applied.setdefault(node["id"], []).append(track_id)
            for step in steps or ():
                if step["id"] in missing:
                    step["missing"] = True
                if step["id"] in unsupported:
                    step["unsupported"] = True
                    step["unsupportedIds"] = unsupported_ids[step["id"]]
                if step["id"] in aimed:
                    step["doorId"] = aimed[step["id"]]
                target_type = target_types.get(step["id"], "")
                if step["id"] in applied and (step["type"] in ("interact", "sprite", "move", "rotate", "setInteraction", "setRegion", "setVisibility", "setAppearance")
                                              or target_type.endswith("set") or target_type in ("light", "sound")):
                    step.update(targetIds=applied[step["id"]], targetsCount=len(applied[step["id"]]))
                if step["id"] in missing_ids:
                    step["missingIds"] = missing_ids[step["id"]]
                if step["id"] in world_results:
                    step.update(world_results[step["id"]])
            return requested, authorized

        if checkpoint is not None:
            graph(resume.event, continuation=checkpoint)
        elif signal is not None:
            graph(signal)
        elif first and trigger_event is not None:
            graph(trigger_event)
        elif interact:
            if blueprint is None:
                # Native controls remain available through an explicit action.
                # An authored empty handler deliberately does nothing.
                desired = ("closed" if state == "open" else "open") if kind == "door" else ("off" if state == "on" else "on")
                change_state(key, desired, allowed)
            else:
                graph("interact")
        elif desired is not None:
            # An explicit GM control changes state; it does not emit another event.
            change_state(key, desired, allowed)
        if first and presence_event is not None:
            from .regions import presence_suppressed
            if not presence_suppressed(door):
                if kind == "region":
                    set_element_state(door, desired)
                    state = desired
                graph(presence_event)
        if sprite is None:
            door.data.pop("sprite", None)
        else:
            door.data["sprite"] = sprite
        return False

    try:
        blocked = operate_door(root, target, interact=interact, first=True,
                               signal=resume.event if resume is not None and resume.kind == "timer" else None,
                               checkpoint=resume.data["continuation"] if resume is not None and resume.kind == "delay" else None)
        while queue:
            key, desired, allowed, signal, broadcast = queue.popleft()
            interaction = signal == "interact"
            operate_door(key, desired, interact=interaction, first=False, allowed=allowed,
                         signal=None if interaction else signal, broadcast=broadcast)
    except MapError as error:
        error.automation_run = {**run, "stateAfter": run["stateBefore"], "message": str(error)}
        raise
    audio_changed = False
    while audio:
        kind = audio[0][0]
        batch = []
        while audio and audio[0][0] == kind:
            batch.append(audio.pop(0)[1])
        if kind == "play":
            play_effects(scene, batch)
            audio_changed = True
        else:
            audio_changed = control_effects(scene, batch) or audio_changed
    _remember_effects(scene, light_changes)
    if scene_variables != initial_scene_variables:
        scene.settings = {**scene.settings, "automationVariables": scene_variables}
        scene.save(update_fields=["settings"])
    for key, before in initial.items():
        door = native[key]
        if key in doors and door.kind == "images":
            apply_lever_appearance(door)
            from .regions import object_area, object_shape, rebaseline_object
            if object_area(door) and object_shape(door.data) != object_shape(before):
                rebaseline_object(scene, door)
        if "torch" in door.data:
            from .torches import sync_components
            try:
                sync_components(door, torch_synced.get(key, before), remember=True)
            except MapError as error:
                error.automation_run = {**run, "stateAfter": run["stateBefore"], "message": str(error)}
                raise
        if door.data != saved_data.get(key, before):
            door.version += 1
            door.save(update_fields=["data", "version"])
    budget = {**counters, "perElement": per_door}
    for key, event, delay in waits:
        schedule_delay(scene, who, doors[key], event, delay, chain_id=chain_id,
                       request_id=request_id, budget=budget, context=context)
    if waits or timers_scheduled or resume is not None:
        update_chain_budget(chain_id, budget)
    record_run(scene, who, obj, "blocked" if blocked else "waiting" if waits else "completed",
               {**run, "stateAfter": element_state(obj)})
    return {"blueprintAudioChanged": audio_changed,
            "blocked": blocked,
            "blueprint": {"state": element_state(obj), "trace": traces}}
