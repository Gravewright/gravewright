"""GM views of existing element-owned rules; no second executable graph store."""

from copy import deepcopy
import uuid

from django.db import transaction

from gravewright.audio.models import Track
from gravewright.campaigns.models import Campaign
from gravewright.journals.services import identifier, member

from . import services
from .blueprint_actions import intelligent, live_objects
from .blueprint_runtime import door_point, element_kind, element_state
from .blueprints import clean_blueprint
from .models import MapAsset, MapBuilderProject, Receipt, SceneObject


def _ownership(scene):
    result = {}
    for project in MapBuilderProject.objects.filter(scene=scene):
        for entry in project.generation.get("objects", []):
            result[entry["id"]] = (project, entry)
    return result


def state(campaign_id, user_id, scene_id):
    who = member(campaign_id, user_id)
    services.manage(who)
    scene = services.scene(scene_id, who)
    ownership = _ownership(scene)
    elements, lights = [], []
    counters = {}
    for row in live_objects(scene):
        if row.kind == "lights":
            lights.append({"id": str(row.pk), "name": row.data.get("name") or "", "ordinal": len(lights) + 1,
                           "x": row.data["x"], "y": row.data["y"], "point": door_point(row.data),
                           "version": row.version, "nativeKind": "lights", "nativeData": deepcopy(row.data)})
            continue
        if row.data.get("surfacePlane") and not row.data.get("surface"):
            continue
        editable = intelligent(row)
        kind = element_kind(row) if editable else "image"
        counters[kind] = counters.get(kind, 0) + 1
        asset = row.data.get("asset_id")
        name = (row.data.get("region") or {}).get("name") or row.data.get("name") or ""
        project, record = ownership.get(str(row.pk), (None, None))
        elements.append({"id": str(row.pk), "kind": kind, "name": name, "ordinal": counters[kind], "version": row.version,
                         "state": element_state(row) if editable else None, "editable": editable,
                         "point": door_point(row.data), "assetId": asset,
                         "blueprint": clean_blueprint(row.data["blueprint"]) if row.data.get("blueprint") is not None else None,
                         "projectId": str(project.pk) if project else None,
                         "projectVersion": project.version if project else None})
        entry = elements[-1]
        if row.data.get("empty") is True:
            entry["empty"] = True
        if kind in ("door", "lever", "torch"):
            entry["interactionEnabled"] = row.data.get("interactionEnabled", True)
        if kind == "image" or kind in ("lever", "torch"):
            entry["visible"] = row.data.get("layer") not in ("gm", "gm-image-layer")
        if kind == "torch":
            entry["lit"] = row.data["torch"]["lit"]
        if kind == "region":
            entry.update(enabled=row.data.get("enabled", True), count=len(row.data["region"]["occupants"]))
        if "surface" in row.data:
            entry.update(surfaceKind=row.data["surface"]["kind"], materialId=row.data["surface"].get("materialId"))
        elif kind in ("door", "lever", "torch"):
            sprite = row.data.get("sprite", {})
            entry["materialId"] = sprite.get("assetId") if sprite.get("appearance") == "asset" else None
            entry["appearanceOverride"] = bool(sprite)
    from .blueprint_world import presentation_catalog
    from .blueprint_clocks import catalog as clock_catalog
    from .blueprint_clues import catalog as clue_catalog
    from gravewright.tokens.models import Token
    return {"campaignId": str(who.campaign_id), "sceneId": str(scene.pk), "sceneName": scene.name, "sceneVersion": scene.version,
            "elements": elements, "lights": lights,
            "effects": [{"id": str(row.pk), "name": row.data.get("name") or "", "ordinal": index + 1,
                         "point": door_point(row.data), "version": row.version,
                         "nativeKind": row.kind, "nativeData": deepcopy(row.data)}
                        for index, row in enumerate(SceneObject.objects.filter(scene=scene, kind__in=("particles", "shaders")))],
            "tokens": [{"id": str(row.pk), "name": row.actor.name, "actorId": str(row.actor_id)}
                       for row in Token.objects.filter(scene=scene).select_related("actor").order_by("id")],
            "sounds": [{"id": str(row.pk), "name": row.name} for row in Track.objects.filter(campaign_id=campaign_id).order_by("name", "id")],
            "clocks": clock_catalog(who, scene.pk),
            "clues": clue_catalog(who, scene.pk),
            "assets": [{"id": str(row.pk), "name": row.name, "url": f"/game/map-assets/{row.pk}",
                        "width": row.width, "height": row.height}
                       for row in MapAsset.objects.filter(campaign_id=campaign_id, generated_for__isnull=True).order_by("name", "id")],
            **presentation_catalog(who)}


def remap(blueprint, records):
    """Translate only typed native references back to authored source identities."""
    mapping = {}
    for record in records:
        try:
            source_id = str(uuid.UUID(record.get("sourceId", "")))
        except (ValueError, AttributeError, TypeError):
            continue
        mapping[record["id"]] = source_id
    result = deepcopy(blueprint)
    for graph in result["graphs"].values():
        for node in graph["nodes"]:
            if node["type"] in ("reference", "light", "lightReference"):
                node["targetId"] = mapping.get(node["targetId"], node["targetId"])
            elif node["type"] == "elementGroup" and node["memberType"] != "sound":
                node["targetIds"] = [mapping.get(value, value) for value in node["targetIds"]]
            elif node["type"] == "teleport":
                node["destinationId"] = mapping.get(node["destinationId"], node["destinationId"])
    return result


def _source_document(project):
    document = deepcopy(project.document)
    if document["schemaVersion"] != 3:
        document["schemaVersion"] = 3
        layer_id = str(uuid.uuid5(project.pk, "network-layer"))
        document["layers"] = [{"id": layer_id, "name": "Layer 1", "visible": True, "locked": False}]
        for kind in ("floors", "walls", "doors"):
            for item in document[kind]:
                item["layerId"] = layer_id
        document.update(decorations=[], lights=[])
    return document


def save(campaign_id, user_id, scene_id, element_id, payload):
    from .builder_services import fingerprint, replay
    if (not isinstance(payload, dict) or set(payload) != {"request_id", "expected_version", "expected_project_version", "blueprint"}
            or type(payload["expected_version"]) is not int or payload["expected_version"] < 1
            or not isinstance(payload["blueprint"], dict)):
        raise services.MapError("Invalid scene network command.")
    request_id = identifier(payload["request_id"])
    element_id, scene_id = identifier(element_id), identifier(scene_id)
    digest = fingerprint(f"scene-network:{scene_id}", element_id, payload)
    with transaction.atomic():
        Campaign.objects.select_for_update().get(pk=campaign_id)
        who = member(campaign_id, user_id)
        services.manage(who)
        scene = services.scene(scene_id, who)
        cached = replay(campaign_id, user_id, request_id, digest)
        if cached is not None:
            return cached
        row = SceneObject.objects.select_for_update().filter(scene=scene, pk=element_id).first()
        if row is None or not intelligent(row):
            raise services.MapError("Choose an editable element from this scene.", "not_found")
        if row.version != payload["expected_version"]:
            raise services.MapError("The object changed. Refresh the scene network before editing.", "conflict")
        project, record = _ownership(scene).get(str(row.pk), (None, None))
        if project and (type(payload["expected_project_version"]) is not int or payload["expected_project_version"] != project.version):
            raise services.MapError("The map project changed. Refresh the scene network before editing.", "conflict")
        if not project and payload["expected_project_version"] is not None:
            raise services.MapError("The map project changed. Refresh the scene network before editing.", "conflict")
        if row.kind == "walls":
            data = {"wall_id": str(row.pk), "version": row.version, "blueprint": payload["blueprint"]}
        elif row.kind == "zones":
            data = {"zone_id": str(row.pk), "expected_version": row.version, "patch": {"blueprint": payload["blueprint"]}}
        else:
            data = {"placement_id": str(row.pk), "expected_version": row.version, "blueprint": payload["blueprint"]}
        result = services.command(campaign_id, user_id, "objects",
                                  {"mapId": str(scene.pk), "area": row.kind, "action": "update", "data": data}, request_id)
        row.refresh_from_db()
        if project:
            from .builder_services import clean_document
            document = _source_document(project)
            item = next((item for kind in ("doors", "decorations", "regions") for item in document.get(kind, [])
                         if item["id"] == record["sourceId"]), None)
            if item is None:
                raise services.MapError("The map project changed. Refresh the scene network before editing.", "conflict")
            item["blueprint"] = remap(row.data["blueprint"], project.generation["objects"])
            project.document = clean_document(document, who)
            project.version += 1
            # Only this authored field is adopted. Pre-existing manual geometry
            # or other edits retain their generated-snapshot conflict protection.
            for entry in project.generation["objects"]:
                if entry["id"] == str(row.pk):
                    entry["data"]["blueprint"] = deepcopy(row.data["blueprint"])
            project.save(update_fields=["document", "version", "generation", "updated_at"])
        result = {**result, "elementId": str(row.pk), "version": row.version,
                  "projectVersion": project.version if project else None}
        Receipt.objects.filter(campaign_id=campaign_id, user_id=user_id, request_id=request_id).update(
            result={"builderFingerprint": digest, "response": result})
        return result
