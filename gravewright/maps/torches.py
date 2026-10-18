"""Validated composed torches, private ownership and atomic native transforms."""

from copy import deepcopy
import math
import uuid

from django.conf import settings

from gravewright.journals.services import identifier

from .models import SceneObject
from .services import MapError

COMPONENTS = {"lightId": "lights", "particleId": "particles", "shaderId": "shaders"}


def clean_source(raw):
    from .objects import boolean
    if (not isinstance(raw, dict) or not {"state", "lit", "lightId"} <= raw.keys()
            or raw.keys() - {"state", "lit", *COMPONENTS}
            or raw.get("state") not in ("off", "on")):
        raise MapError("Invalid torch.")
    return {"state": raw["state"], "lit": boolean(raw["lit"]),
            **{key: str(identifier(raw[key])) for key in COMPONENTS if key in raw}}


def validate_sources(document):
    """Resolve exact kind, layer and exclusive ownership after all rows exist."""
    seen = set()
    by_kind = {kind: {row["id"]: row for row in document.get(kind, [])} for kind in COMPONENTS.values()}
    for parent in document.get("decorations", []):
        if parent.get("torch", {}).get("state") == "on":
            angle = math.radians(parent["rotation"] + 90)
            half_x = (abs(math.cos(angle)) * parent["width"] + abs(math.sin(angle)) * parent["height"]) / 2
            half_y = (abs(math.sin(angle)) * parent["width"] + abs(math.cos(angle)) * parent["height"]) / 2
            cx, cy = parent["x"] + parent["width"] / 2, parent["y"] + parent["height"] / 2
            if (min(cx - half_x, cy - half_y) < -1e-7 or cx + half_x > document["columns"] + 1e-7
                    or cy + half_y > document["rows"] + 1e-7):
                raise MapError("A decoration lies outside the map.")
        for field, kind in COMPONENTS.items():
            target = parent.get("torch", {}).get(field)
            if target is None:
                continue
            child = by_kind[kind].get(target)
            if child is None or child["layerId"] != parent["layerId"] or target in seen:
                raise MapError("Choose an unlinked torch component from the same layer.")
            if parent["torch"]["state"] == "on":
                cx, cy = parent["x"] + parent["width"] / 2, parent["y"] + parent["height"] / 2
                x, y = cx - (child["y"] - cy), cy + (child["x"] - cx)
                if min(x, y) < -1e-7 or x > document["columns"] + 1e-7 or y > document["rows"] + 1e-7:
                    raise MapError("A torch component lies outside the map.")
            seen.add(target)


def clean_native(raw):
    from .blueprint_runtime import clean_lever
    from .objects import boolean, number
    base = clean_lever(raw)
    if not isinstance(raw.get("components"), dict) or "lights" not in raw["components"]:
        raise MapError("Invalid torch.")
    if raw["components"].keys() - set(COMPONENTS.values()):
        raise MapError("Invalid torch.")
    children = {}
    for kind, child in raw["components"].items():
        if not isinstance(child, dict) or set(child) != {"id", "enabled"}:
            raise MapError("Invalid torch.")
        children[kind] = {"id": str(identifier(child["id"])), "enabled": boolean(child["enabled"])}
    if len({child["id"] for child in children.values()}) != len(children):
        raise MapError("Invalid torch.")
    return {**base, "lit": boolean(raw.get("lit")),
            "baseRotation": number(raw.get("baseRotation"), -36000, 36000) % 360,
            "components": children}


def owners(scene, component_id=None):
    rows = SceneObject.objects.filter(scene=scene, kind="images", data__torch__isnull=False)
    if component_id is None:
        return rows
    return [row for row in rows if any(child["id"] == str(component_id)
            for child in row.data.get("torch", {}).get("components", {}).values())]


def sync_components(parent, before=None, *, rows=None, remember=False):
    """Move native children once with their owner and gate authored enable flags.

    ``rows`` is the not-yet-persisted generation batch. No native writes happen
    during generation preparation; runtime callers already hold a transaction.
    """
    torch = parent.data.get("torch")
    if not isinstance(torch, dict):
        return
    clean_native(torch)
    if not settings.DYNAMIC_LIGHTING_ENABLED:
        raise MapError("Dynamic lighting is disabled.", "forbidden")
    before = before or parent.data
    old_torch = before.get("torch", torch)
    delta = math.radians(parent.data["rotation"] - before["rotation"])
    cosine, sine = math.cos(delta), math.sin(delta)
    ratio = torch["width"] / old_torch["width"]
    batch = {str(row.pk): row for row in rows} if rows is not None else None
    changes = {}
    for kind, link in torch["components"].items():
        child = (batch.get(link["id"]) if batch is not None else
                 SceneObject.objects.filter(scene=parent.scene, pk=link["id"], kind=kind).first())
        if child is None or child.kind != kind:
            raise MapError("A torch component is missing from this scene.")
        previous = deepcopy(child.data)
        dx, dy = (child.data["x"] - before["x"]) * ratio, (child.data["y"] - before["y"]) * ratio
        from .objects import number
        child.data["x"] = number(parent.data["x"] + dx * cosine - dy * sine)
        child.data["y"] = number(parent.data["y"] + dx * sine + dy * cosine)
        child.data["rotation"] = (child.data.get("rotation", 0) + math.degrees(delta)) % 360
        child.data["enabled"] = torch["lit"] and link["enabled"] and parent.data.get("layer") != "gm-image-layer"
        if rows is None and child.data != previous:
            changes[str(child.pk)] = (previous, deepcopy(child.data))
            child.version += 1
            child.save(update_fields=["data", "version"])
    if remember and changes:
        from .builder_services import strip_live
        from .models import MapBuilderProject
        for source in MapBuilderProject.objects.filter(scene=parent.scene):
            manifest = deepcopy(source.generation)
            changed = False
            for record in manifest.get("objects", []):
                if record.get("id") not in changes:
                    continue
                old, new = changes[record["id"]]
                stored, actual = deepcopy(record["data"]), deepcopy(old)
                strip_live(stored, actual, kind=record["kind"])
                if stored == actual:
                    record["data"] = deepcopy(new)
                    changed = True
            if changed:
                source.generation = manifest
                source.save(update_fields=["generation"])


def gate_edit(scene, child, raw):
    """Native component editors keep their full controls without bypassing Off."""
    for parent in owners(scene, child.pk):
        link = parent.data["torch"]["components"][child.kind]
        previous = SceneObject.objects.filter(pk=child.pk, scene=scene).values_list("data", flat=True).first()
        if "enabled" in raw and previous is not None and child.data["enabled"] != previous.get("enabled"):
            link["enabled"] = child.data["enabled"]
            parent.version += 1
            parent.save(update_fields=["data", "version"])
        child.data["enabled"] = (parent.data["torch"]["lit"] and link["enabled"]
                                 and parent.data.get("layer") != "gm-image-layer")


def delete_group(parent):
    """Delete only the owner's exact scene-local component IDs."""
    light = parent.data.get("torch", {}).get("components", {}).get("lights")
    if light:
        from .blueprint_runtime import detach_scene_lights
        detach_scene_lights(parent.scene_id, [light["id"]])
    for kind, link in parent.data.get("torch", {}).get("components", {}).items():
        SceneObject.objects.filter(scene=parent.scene, kind=kind, pk=link["id"]).delete()


def detach_component(scene, component_id):
    """Deleting a required light dissolves ownership; optional effects detach."""
    for parent in owners(scene, component_id):
        kind = next(kind for kind, child in parent.data["torch"]["components"].items()
                    if child["id"] == str(component_id))
        if kind == "lights":
            delete_group(parent)
            parent.data.pop("torch")
            parent.data.pop("blueprint", None)
            parent.data.pop("automationVariables", None)
            parent.data.pop("automationMemory", None)
            parent.data.pop("sprite", None)
        else:
            parent.data["torch"]["components"].pop(kind)
        parent.version += 1
        parent.save(update_fields=["data", "version"])


def duplicate(parent, raw):
    """Clone a configured native group without accepting client ownership data."""
    from .extra_objects import image
    from .objects import number
    previous = deepcopy(parent.data)
    old_parent = str(parent.pk)
    clone = SceneObject(scene=parent.scene, kind="images", data=image(parent.scene, {
        "x": number(raw.get("x", parent.data["x"])), "y": number(raw.get("y", parent.data["y"])),
    }, previous))
    clone.pk = uuid.uuid4()
    clone.data.pop("automationVariables", None)
    clone.data.pop("automationMemory", None)
    mapping = {old_parent: str(clone.pk)}
    children = []
    for kind, link in clone.data["torch"]["components"].items():
        child = SceneObject.objects.filter(scene=parent.scene, pk=link["id"], kind=kind).first()
        if child is None:
            raise MapError("A torch component is missing from this scene.")
        old = str(child.pk)
        child.pk, child.version, child.data = uuid.uuid4(), 1, deepcopy(child.data)
        mapping[old] = str(child.pk)
        link["id"] = str(child.pk)
        children.append(child)
    if parent.scene.elements.count() + len(children) + 1 > 5000:
        raise MapError("Scene object limit reached.")
    for graph in clone.data.get("blueprint", {}).get("graphs", {}).values():
        for node in graph["nodes"]:
            if node.get("targetId") in mapping:
                node["targetId"] = mapping[node["targetId"]]
            if node["type"] == "elementGroup" and node["memberType"] in ("element", "light"):
                node["targetIds"] = [mapping.get(identifier, identifier) for identifier in node["targetIds"]]
    sync_components(clone, previous, rows=children)
    from .regions import rebaseline_object
    rebaseline_object(parent.scene, clone)
    clone.save(force_insert=True)
    SceneObject.objects.bulk_create(children)
    return clone
