"""GM-owned map sources, bounded validation and transactional scene generation."""

from copy import deepcopy
import hashlib
import json
import math
import threading
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q

from gravewright.campaigns.models import Campaign
from gravewright.journals.services import identifier, member

from . import objects, services, tiling
from .models import MapAsset, MapBuilderProject, Receipt, Scene, SceneNavigation, SceneObject, SceneState, Tile
from .terrain_brush import clean_floor_brush, terrain_brush_cost
from .element_names import clean_name, copy_name
from .builder_geometry import canvas_size, scene_options


LIMITS = {
    "maxColumns": 200, "maxRows": 200,
    "minCellSize": 16, "maxCellSize": 256,
    "maxPixels": 16_777_216, "maxObjects": 2000, "maxAssets": 256,
    "maxNativeObjects": 5000,
    "maxLayers": 32,
    "maxFloorShapeRings": 128, "maxFloorRingPoints": 256,
    "maxFloorShapePoints": 4096, "maxFloorDocumentPoints": 16384,
    "maxFloorShapeWork": 8_388_608,
    "minWallThickness": 0.05, "maxWallThickness": 2,
    "minDoorWidth": 0.25, "maxDoorWidth": 20,
    "maxPaintPixels": 67_108_864,
    "maxTerrainBrushDabs": 2048, "maxTerrainDocumentDabs": 8192,
    "maxTerrainBrushPixels": 67_108_864,
}
MAX_DOCUMENT_BYTES = 1_000_000
NATIVE_EFFECT_FIELDS = {
    "particles": ("kind", "scale", "density", "color", "enabled", "rotation", "light_response", "light_emission"),
    "shaders": ("name", "source", "radius", "scale", "intensity", "opacity", "speed", "color", "rotation",
                "blend_mode", "enabled", "light_response", "light_emission"),
}
LIVE_ENABLED_KINDS = ("lights", "particles", "shaders")
WALL_PROPERTY_FIELDS = ("presentation", "behavior", "vertical", "discovered")
_preparing = threading.RLock()


def authority(campaign_id, user_id):
    who = member(campaign_id, user_id)
    services.manage(who)
    return who


def project(project_id, who):
    row = MapBuilderProject.objects.filter(
        pk=identifier(project_id), campaign_id=who.campaign_id
    ).first()
    if row is None:
        raise services.MapError("Map project not found.", "not_found")
    return row


def summary(row, who):
    can_update = bool(row.scene_id and isinstance(row.generation, dict)
                      and row.generation.get("sceneId") == str(row.scene_id)
                      and row.generation.get("objects") is not None)
    if not can_update:
        can_update = legacy_generation(row, who) is not None
    return {
        "id": str(row.pk), "name": row.name, "version": row.version,
        "folderId": str(row.folder_id) if row.folder_id else None,
        "sceneId": str(row.scene_id) if row.scene_id else None,
        "sceneVersion": row.scene.version if row.scene_id else None,
        "canUpdate": can_update,
        **({"importWarnings": row.generation["importWarnings"]}
           if isinstance(row.generation, dict) and row.generation.get("importWarnings") else {}),
        "updatedAt": int(row.updated_at.timestamp() * 1000),
    }


def view(row, who):
    document = deepcopy(row.document)
    from .blueprints import clean_blueprint
    for kind in ("doors", "decorations", "regions"):
        for item in document.get(kind, []):
            if item.get("blueprint") is not None:
                item["blueprint"] = clean_blueprint(item["blueprint"])
    return {**summary(row, who), "document": document}


def catalog(campaign_id, user_id):
    who = authority(campaign_id, user_id)
    from gravewright.audio.models import Track
    from .blueprint_world import presentation_catalog
    from .blueprint_clocks import catalog as clock_catalog
    from .blueprint_clues import catalog as clue_catalog
    from .blueprint_mindmaps import catalog as mindmap_catalog
    return {
        "projects": [summary(row, who) for row in MapBuilderProject.objects.filter(campaign=who.campaign).select_related("scene")],
        "assets": [
            {"id": str(row.pk), "name": row.name,
             "url": f"/game/map-assets/{row.pk}", "width": row.width, "height": row.height}
            for row in MapAsset.objects.filter(campaign=who.campaign, generated_for__isnull=True).order_by("name", "id")
        ],
        "sounds": [{"id": str(row.pk), "name": row.name,
                    "url": f"/game/audio/{row.pk}", "duration": row.duration}
                   for row in Track.objects.filter(campaign=who.campaign).order_by("name", "id")],
        **presentation_catalog(who),
        "clocks": clock_catalog(who, all_scenes=True),
        "clues": clue_catalog(who, all_scenes=True),
        "mindmaps": mindmap_catalog(who, all_scenes=True),
        "limits": {**LIMITS, "maxPixels": min(LIMITS["maxPixels"], settings.GRAVEWRIGHT_MAP_MAX_PIXELS)},
    }


def detail(campaign_id, user_id, project_id):
    who = authority(campaign_id, user_id)
    return {"project": view(project(project_id, who), who)}


def sync(campaign_id, user_id, project_id, payload):
    """Import authored VTT changes using the normal revision and retry contract."""
    fields(payload, ("request_id", "expected_version", "expected_scene_version", "expected_scene_id"), "map synchronization command")
    project_id, request_id = identifier(project_id), identifier(payload.get("request_id"))
    digest = fingerprint("sync", project_id, payload)
    with transaction.atomic():
        who = authority(campaign_id, user_id)
        Campaign.objects.select_for_update().get(pk=who.campaign_id)
        who = authority(campaign_id, user_id)
        cached = replay(campaign_id, user_id, request_id, digest)
        if cached is not None:
            return cached
        source = project(project_id, who)
        expected(payload.get("expected_version"), source)
        expected_scene(source, payload)
        if not source.scene_id:
            raise services.MapError("Generate a scene before updating it.", "conflict")
        scene = services.scene(source.scene_id, who, write=True)
        if type(payload.get("expected_scene_version")) is not int or payload["expected_scene_version"] != scene.version:
            raise services.MapError("The scene changed. Reload the project before updating it.", "conflict")
        from .builder_sync import reconcile
        document, generation, synchronized = reconcile(source, scene, who)
        if synchronized:
            source.document, source.generation = document, generation
            source.version += 1
            source.save(update_fields=["document", "generation", "version", "updated_at"])
        response = {"project": view(source, who), "scene": services.view(scene), "synchronized": synchronized}
        record(campaign_id, user_id, request_id, digest, response)
    return response


def detach_project_art(campaign_id, asset_id):
    """Remove deleted material references while preserving editable geometry.

    The caller holds the campaign write transaction. Incrementing the revision
    makes open editors refresh rather than restore a deleted asset on save.
    """
    asset_id = str(asset_id)
    available = {str(pk) for pk in MapAsset.objects.filter(campaign_id=campaign_id).exclude(pk=asset_id)
                 .values_list("pk", flat=True)}
    for row in MapBuilderProject.objects.filter(campaign_id=campaign_id).filter(
        Q(document__icontains=asset_id) | Q(generation__icontains=asset_id)
    ):
        document = row.document
        if not isinstance(document, dict):
            continue
        changed = detach_document_art(document, asset_id, available)
        history_changed = detach_generation_art(row, asset_id)
        if changed or history_changed:
            row.version += 1
            row.save(update_fields=["document", "generation", "version", "updated_at"])


def detach_document_art(document, asset_id, available):
    """Apply the same deletion to current source and its private generation recipe."""
    from .blueprint_runtime import detach_blueprint_art, detach_blueprint_light, replacement_lever_asset
    removed_components, changed = set(), False
    if isinstance(document.get("backgroundImage"), dict) and document["backgroundImage"].get("assetId") == asset_id:
        document.pop("backgroundImage")
        changed = True
    classified = document.get("assets")
    if isinstance(classified, list):
        kept = [entry for entry in classified if not isinstance(entry, dict) or entry.get("assetId") != asset_id]
        changed = len(kept) != len(classified) or changed
        document["assets"] = kept
    for key in ("floors", "walls", "doors", "decorations", "regions"):
        entries = document.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("assetId") == asset_id:
                element_key = "torch" if "torch" in entry else "lever"
                replacement = (replacement_lever_asset(entry.get("blueprint"), asset_id, available)
                               if key == "decorations" and element_key in entry else None)
                entry["assetId"] = replacement
                if key == "decorations" and element_key in entry and replacement is None:
                    if element_key == "torch":
                        from .torches import COMPONENTS
                        removed_components.update(entry["torch"][field] for field in COMPONENTS if field in entry["torch"])
                        entry["rotation"] = (entry["rotation"] + (90 if entry["torch"]["state"] == "on" else 0)) % 360
                    entry.pop(element_key, None)
                    entry.pop("blueprint", None)
                changed = True
            changed = detach_blueprint_art(entry.get("blueprint"), asset_id) or changed
    if removed_components:
        from .torches import COMPONENTS
        for kind in COMPONENTS.values():
            document[kind] = [child for child in document.get(kind, []) if child["id"] not in removed_components]
        for entry in (*document.get("doors", []), *document.get("decorations", []), *document.get("regions", [])):
            for component_id in removed_components:
                detach_blueprint_light(entry.get("blueprint"), component_id)
    return changed


def detach_generation_art(source, asset_id):
    """Mirror only the asset deletion's known native cleanup in its snapshot.

    Image placements have already been removed by the caller. Door art is
    removed next, in the same campaign transaction. Preserve every other field
    so geometry and behavior changes made in the VTT still cause a conflict.
    """
    history = deepcopy(source.generation)
    if (not isinstance(history, dict) or history.get("formatVersion") != 1
            or history.get("sceneId") != str(source.scene_id)
            or not isinstance(history.get("objects"), list)):
        return False
    available = {str(pk) for pk in MapAsset.objects.filter(campaign_id=source.campaign_id)
                 .exclude(pk=asset_id).values_list("pk", flat=True)}
    candidates, seen, sources = {}, set(), set()
    for index, previous in enumerate(history["objects"]):
        if (not isinstance(previous, dict) or not isinstance(previous.get("data"), dict)
                or not isinstance(previous.get("sourceId"), str) or not previous["sourceId"]
                or len(previous["sourceId"]) > 256 or previous["sourceId"] in sources):
            return False
        try:
            previous_id = uuid.UUID(previous.get("id"))
        except (TypeError, ValueError, AttributeError):
            return False
        if previous_id in seen:
            return False
        seen.add(previous_id)
        sources.add(previous["sourceId"])
        if previous.get("kind") in ("walls", "images") and (previous["data"].get("asset_id") == asset_id
                or previous["data"].get("lever", {}).get("baseAssetId") == asset_id
                or previous["data"].get("torch", {}).get("baseAssetId") == asset_id
                or previous["data"].get("spriteBase", {}).get("assetId") == asset_id):
            candidates[index] = previous_id
    current = {row.pk: row for row in SceneObject.objects.filter(scene_id=source.scene_id, pk__in=candidates.values())}
    deleted_children = {child["id"] for index, pk in candidates.items() if pk not in current
                        for child in history["objects"][index]["data"].get("torch", {}).get("components", {}).values()}
    kept, changed = [], False
    for index, previous in enumerate(history["objects"]):
        if previous["id"] in deleted_children:
            changed = True
            continue
        if index in candidates:
            actual = current.get(candidates[index])
            if previous["kind"] == "images" and actual is None:
                changed = True
                continue
            if (previous["kind"] == "walls" and actual and actual.kind == "walls"
                    and isinstance(actual.data, dict) and actual.data.get("asset_id") == asset_id):
                previous["data"].pop("asset_id", None)
                if "blueprint" not in previous["data"]:
                    previous["data"].pop("thickness", None)
                changed = True
        if previous.get("kind") in ("walls", "images", "zones"):
            from .blueprint_runtime import apply_lever_appearance, detach_blueprint_art, replacement_lever_asset
            data = previous["data"]
            before = deepcopy(data)
            if data.get("surface", {}).get("materialId") == asset_id:
                data["surface"].pop("materialId", None)
                data["surface"].pop("materialCrop", None)
            detach_blueprint_art(data.get("blueprint"), asset_id)
            if isinstance(data.get("sprite"), dict) and data["sprite"].get("assetId") == asset_id:
                if previous["kind"] == "images" and isinstance(data.get("spriteBase"), dict):
                    from .blueprint_actions import change_sprite
                    change_sprite(source.scene, SceneObject(scene=source.scene, kind="images", data=data),
                                  {"appearance": "inherit"})
                else:
                    data.pop("sprite")
            element_key = "torch" if "torch" in data else "lever"
            if previous["kind"] == "images" and isinstance(data.get(element_key), dict):
                if data[element_key].get("baseAssetId") == asset_id:
                    replacement = replacement_lever_asset(data.get("blueprint"), asset_id, available)
                    if replacement is not None:
                        data[element_key]["baseAssetId"] = replacement
                if before != data:
                    apply_lever_appearance(SceneObject(scene=source.scene, kind="images", data=data))
            changed = before != data or changed
        kept.append(previous)
    for key in ("dynamicDocument", "sourceDocument"):
        if isinstance(history.get(key), dict):
            changed = detach_document_art(history[key], asset_id, available) or changed
    if changed:
        history["objects"] = kept
        source.generation = history
    return changed


def detach_project_sound(campaign_id, track_id):
    """Remove deleted audio actions without invalidating the remaining graph."""
    from .blueprint_runtime import detach_blueprint_sound

    for row in MapBuilderProject.objects.filter(campaign_id=campaign_id).filter(
        Q(document__icontains=str(track_id)) | Q(generation__icontains=str(track_id))
    ):
        changed = False
        documents = [row.document]
        for key in ("dynamicDocument", "sourceDocument"):
            if isinstance(row.generation.get(key), dict):
                documents.append(row.generation[key])
        for document in documents:
            for kind in ("doors", "decorations", "regions"):
                for element in document.get(kind, []):
                    changed = detach_blueprint_sound(element.get("blueprint"), track_id) or changed
        for obj in row.generation.get("objects", []):
            changed = detach_blueprint_sound(obj.get("data", {}).get("blueprint"), track_id) or changed
        if changed:
            row.version += 1
            row.save(update_fields=["document", "generation", "version", "updated_at"])


def fields(value, allowed, label):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise services.MapError(f"Invalid {label} fields.")
    return value


def number(value, low, high, label, *, integer=False):
    if (type(value) not in ((int,) if integer else (int, float))
            or not low <= value <= high or not math.isfinite(value)):
        raise services.MapError(f"Invalid {label}.")
    return value


def clean_wall_properties(item, row):
    """Keep optional authored barrier settings in the native validator's format."""
    properties = {key: item[key] for key in WALL_PROPERTY_FIELDS if key in item}
    if not properties:
        return
    if "behavior" in properties:
        fields(properties["behavior"], ("movement", "vision", "light", "sound"), "wall behavior")
    if "vertical" in properties:
        fields(properties["vertical"], ("bottom", "top"), "elevation range")
    native = objects.wall({**{key: row[key] for key in ("x1", "y1", "x2", "y2")}, **properties})
    for key in ("presentation", "discovered"):
        if key in properties:
            row[key] = native[key]
    if "behavior" in properties:
        row["behavior"] = {key: native[key + "_behavior"] for key in properties["behavior"]}
    if "vertical" in properties:
        row["vertical"] = {key: native["vertical_" + key] for key in properties["vertical"]}


def clean_floor_shape(raw, row, cell):
    """Validate normalized contour unions and excluded cuts with bounded work.

    Each ring uses even-odd coverage; rings are unioned rather than cancelling
    overlapping strokes. Coordinates are relative to the authored floor box,
    so moving or resizing it retains the contour and its cuts.
    """
    if not isinstance(raw, dict) or set(raw) != {"contours", "cuts"}:
        raise services.MapError("Invalid floor shape.")
    if (not isinstance(raw["contours"], list) or not raw["contours"]
            or not isinstance(raw["cuts"], list)):
        raise services.MapError("Invalid floor shape.")
    if len(raw["contours"]) + len(raw["cuts"]) > LIMITS["maxFloorShapeRings"]:
        raise services.MapError("The map floor shapes are too complex.")
    result, points, pixels, work = {}, 0, 0, 0
    for kind in ("contours", "cuts"):
        result[kind] = []
        for ring in raw[kind]:
            if not isinstance(ring, list) or len(ring) < 3:
                raise services.MapError("Invalid floor shape.")
            if len(ring) > LIMITS["maxFloorRingPoints"]:
                raise services.MapError("The map has too many floor shape points.")
            cleaned = []
            for point in ring:
                if (not isinstance(point, list) or len(point) != 2
                        or any(type(value) not in (int, float) or not 0 <= value <= 1
                               or not math.isfinite(value) for value in point)):
                    raise services.MapError("Invalid floor shape.")
                cleaned.append(list(point))
            origin = cleaned[0]
            other = next((point for point in cleaned[1:] if point != origin), None)
            if other is None or not any((other[0] - origin[0]) * (point[1] - origin[1])
                    != (other[1] - origin[1]) * (point[0] - origin[0]) for point in cleaned):
                raise services.MapError("Invalid floor shape.")
            points += len(cleaned)
            if points > LIMITS["maxFloorShapePoints"]:
                raise services.MapError("The map has too many floor shape points.")
            xs = [(row["x"] + point[0] * row["width"]) * cell for point in cleaned]
            ys = [(row["y"] + point[1] * row["height"]) * cell for point in cleaned]
            width = max(1, math.ceil(max(xs)) - math.floor(min(xs)))
            height = max(1, math.ceil(max(ys)) - math.floor(min(ys)))
            pixels += width * height
            work += len(cleaned) * height
            result[kind].append(cleaned)
    return result, points, pixels, work


def clean_floor_paint(raw, asset_id):
    """Keep solid paint distinct from campaign textures and bound its alpha."""
    if not isinstance(raw, dict) or set(raw) != {"color", "opacity"}:
        raise services.MapError("Invalid floor paint.")
    color = raw["color"]
    if color is not None:
        if asset_id is not None:
            raise services.MapError("Invalid floor paint.")
        try:
            color = services.color(color).lower()
        except services.MapError:
            raise services.MapError("Invalid floor paint.") from None
    opacity = raw["opacity"]
    if type(opacity) not in (int, float) or not 0 <= opacity <= 1 or not math.isfinite(opacity):
        raise services.MapError("Invalid floor paint.")
    return {"color": color, "opacity": opacity}


def validate_imported_projects(campaign):
    """Apply the new image/base contracts to portable content after ID remapping."""
    from types import SimpleNamespace
    from .empty_objects import image as empty_image
    who = SimpleNamespace(campaign=campaign, campaign_id=campaign.pk)
    from .builder_presets import clean_bundle
    from .models import BuilderObjectPreset
    presets = BuilderObjectPreset.objects.filter(campaign=campaign)
    if presets.count() > 128:
        raise services.MapError("Object library limit exceeded.")
    for preset in presets:
        services.title(preset.name)
        clean_bundle(preset.document, who)
    for source in MapBuilderProject.objects.filter(campaign=campaign):
        history = source.generation if isinstance(source.generation, dict) else {}
        for doc in (source.document, history.get("dynamicDocument", {}), history.get("sourceDocument", {})):
            if not isinstance(doc, dict):
                continue
            decorations = doc.get("decorations")
            if ("backgroundImage" in doc or isinstance(decorations, list)
                    and any(isinstance(row, dict) and "empty" in row for row in decorations)):
                clean_document(doc, who, scene_id=source.scene_id)
    for row in SceneObject.objects.filter(scene__campaign=campaign, kind="images").select_related("scene"):
        if isinstance(row.data, dict) and "empty" in row.data:
            empty_image(row.scene, {**row.data, "id": str(row.pk)})


def clean_document(raw, who, *, scene_id=None):
    """Normalize a finite, bounded, campaign-scoped document in grid cells."""
    fields(raw, ("schemaVersion", "name", "columns", "rows", "cellSize", "background", "backgroundImage", "floors", "walls", "doors", "assets", "layers", "decorations", "lights", "particles", "shaders", "regions", "editingMode", "sceneGeometry"), "map project")
    try:
        if len(json.dumps(raw, allow_nan=False)) > MAX_DOCUMENT_BYTES:
            raise services.MapError("The map project is too large.")
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise services.MapError("Invalid map project document.") from None
    if type(raw.get("schemaVersion")) is not int or raw["schemaVersion"] not in (1, 2, 3):
        raise services.MapError("Unsupported map project version.")
    expanded = raw["schemaVersion"] == 3
    if not expanded and any(key in raw for key in ("layers", "decorations", "lights", "particles", "shaders", "regions", "backgroundImage")):
        raise services.MapError("Use map project version 3 for layers and objects.")
    doc = {
        "schemaVersion": 3 if expanded else 2,
        "name": services.title(raw.get("name")),
        "columns": number(raw.get("columns"), 1, LIMITS["maxColumns"], "map columns", integer=True),
        "rows": number(raw.get("rows"), 1, LIMITS["maxRows"], "map rows", integer=True),
        "cellSize": number(raw.get("cellSize"), LIMITS["minCellSize"], LIMITS["maxCellSize"], "cell size", integer=True),
        "background": services.color(raw.get("background")).lower(),
    }
    if "editingMode" in raw:
        if not expanded or raw["editingMode"] not in ("tiles", "paint"):
            raise services.MapError("Invalid map editing mode.")
        doc["editingMode"] = raw["editingMode"]
    if "sceneGeometry" in raw:
        geometry = raw["sceneGeometry"]
        fields(geometry, ("width", "height", "gridSize", "gridOffsetX", "gridOffsetY", "imageScale"), "imported scene geometry")
        if not expanded:
            raise services.MapError("Use map project version 3 for imported scene geometry.")
        geometry = {
            "width": number(geometry.get("width"), 1, doc["columns"] * doc["cellSize"], "canvas width", integer=True),
            "height": number(geometry.get("height"), 1, doc["rows"] * doc["cellSize"], "canvas height", integer=True),
            **{key: number(geometry.get(key), low, high, key) for key, low, high in
               (("gridSize", 1, 10000), ("gridOffsetX", -1000000, 1000000), ("gridOffsetY", -1000000, 1000000))},
            **({"imageScale": number(geometry["imageScale"], .01, 100, "imageScale")} if "imageScale" in geometry else {}),
        }
        if (math.ceil(geometry["width"] / doc["cellSize"]) != doc["columns"]
                or math.ceil(geometry["height"] / doc["cellSize"]) != doc["rows"]):
            raise services.MapError("Invalid imported scene geometry.")
        doc["sceneGeometry"] = geometry
    if "backgroundImage" in raw:
        background = raw["backgroundImage"]
        fields(background, ("assetId",), "map background image")
        asset_id = identifier(background.get("assetId"))
        if not MapAsset.objects.filter(pk=asset_id, campaign=who.campaign, generated_for__isnull=True).exists():
            raise services.MapError("Choose a background image from this campaign.")
        # A ready-made map is a single base image, independent of brush roles.
        doc["backgroundImage"] = {"assetId": str(asset_id)}
    canvas_width, canvas_height = canvas_size(doc)
    bound_columns, bound_rows = canvas_width / doc["cellSize"], canvas_height / doc["cellSize"]
    pixels = canvas_width * canvas_height
    if pixels > min(LIMITS["maxPixels"], settings.GRAVEWRIGHT_MAP_MAX_PIXELS):
        raise services.MapError("The map exceeds the builder image pixel limit.")
    tiling._validate_size(canvas_width, canvas_height)
    # Existing version-three documents retain their shape until effects are
    # authored. Explicit empty effect arrays round-trip as explicit arrays.
    kinds = (("floors", "walls", "doors", "decorations", "lights")
             + tuple(kind for kind in (*NATIVE_EFFECT_FIELDS, "regions") if kind in raw)) if expanded else ("floors", "walls", "doors")
    for key in (*kinds, "assets"):
        if not isinstance(raw.get(key, []), list):
            raise services.MapError(f"Invalid map {key}.")
        doc[key] = []
    if sum(len(raw.get(key, [])) for key in kinds) > LIMITS["maxObjects"]:
        raise services.MapError("The map has too many objects.")
    if len(raw.get("assets", [])) > LIMITS["maxAssets"]:
        raise services.MapError("The map has too many assets.")
    roles, families = {}, {}
    for item in raw.get("assets", []):
        fields(item, ("assetId", "role", "name", "collection", "family") if expanded else ("assetId", "role"), "asset")
        asset_id = str(identifier(item.get("assetId")))
        role = item.get("role")
        if role not in (("floor", "wall", "door", "decoration") if expanded else ("floor", "wall", "door")) or asset_id in roles:
            raise services.MapError("Invalid map asset classification.")
        roles[asset_id] = role
        entry = {"assetId": asset_id, "role": role}
        for key, limit in (("name", 240), ("collection", 80), ("family", 80)):
            if key in item:
                value = item[key]
                if not isinstance(value, str) or len(value) > limit or "\x00" in value:
                    raise services.MapError("Invalid map asset metadata.")
                entry[key] = value.strip()
        if "family" in entry:
            family = entry["family"]
            if not family:
                raise services.MapError("An asset family needs a name.")
            if families.setdefault(family, role) != role:
                raise services.MapError("An asset family must contain only one asset type.")
        doc["assets"].append(entry)
    available = {str(pk) for pk in MapAsset.objects.filter(campaign=who.campaign, generated_for__isnull=True, pk__in=roles).values_list("pk", flat=True)}
    if available != set(roles):
        raise services.MapError("A map asset is missing or belongs to another campaign.")
    ids = set()
    layer_ids = set()
    if expanded:
        layers = raw.get("layers")
        if not isinstance(layers, list) or len(layers) > LIMITS["maxLayers"]:
            raise services.MapError("Use up to 32 map layers.")
        doc["layers"] = []
        for layer in layers:
            fields(layer, ("id", "name", "visible", "locked"), "map layer")
            layer_id = str(identifier(layer.get("id")))
            if layer_id in layer_ids:
                raise services.MapError("Map layer identifiers must be unique.")
            layer_ids.add(layer_id)
            doc["layers"].append({"id": layer_id, "name": services.title(layer.get("name"), 80),
                                  "visible": objects.boolean(layer.get("visible")),
                                  "locked": objects.boolean(layer.get("locked"))})

    def base(item, role, allowed):
        fields(item, (*allowed, "name", "layerId") if expanded else (*allowed, "name"), role)
        obj_id = str(identifier(item.get("id")))
        if obj_id in ids:
            raise services.MapError("Map object identifiers must be unique.")
        ids.add(obj_id)
        asset_id = str(identifier(item["assetId"])) if item.get("assetId") is not None else None
        if asset_id is not None and roles.get(asset_id) != role:
            raise services.MapError("Classify this asset before painting with it.")
        result = {"id": obj_id, "assetId": asset_id}
        if expanded:
            layer_id = str(identifier(item.get("layerId")))
            if layer_id not in layer_ids:
                raise services.MapError("Choose an existing map layer.")
            result["layerId"] = layer_id
        return copy_name(result, item)

    paint_area = 0
    shape_points = shape_pixels = shape_work = 0
    brush_points = brush_pixels = 0
    for item in raw.get("floors", []):
        row = base(item, "floor", ("id", "assetId", "x", "y", "width", "height", *( ("rotation", "shape", "paint", "brush", "dynamic") if expanded else () )))
        if "dynamic" in item:
            row["dynamic"] = objects.boolean(item["dynamic"])
        if expanded:
            row["rotation"] = number(item.get("rotation", 0), 0, 270, "floor rotation")
            if row["rotation"] not in (0, 90, 180, 270):
                raise services.MapError("Floor rotation must use quarter turns.")
        for key, limit in (("x", bound_columns), ("y", bound_rows), ("width", bound_columns), ("height", bound_rows)):
            minimum = 0 if key in ("x", "y") else .001 if expanded and ("shape" in item or "brush" in item) else .05
            row[key] = number(item.get(key), minimum, limit, f"floor {key}")
        if row["x"] + row["width"] > bound_columns + 1e-8 or row["y"] + row["height"] > bound_rows + 1e-8:
            raise services.MapError("A floor lies outside the map.")
        paint_area += row["width"] * row["height"]
        if "paint" in item:
            row["paint"] = clean_floor_paint(item["paint"], row["assetId"])
        if "brush" in item:
            row["brush"] = clean_floor_brush(item["brush"])
            if row["brush"]["operation"] == "erase" and row["assetId"] is not None:
                raise services.MapError("Invalid floor brush.")
            if row["brush"]["operation"] == "erase" and row.get("dynamic") is True:
                raise services.MapError("An erase stroke cannot be a dynamic surface.")
            count, pixels = terrain_brush_cost(row, doc["cellSize"])
            brush_points += count
            brush_pixels += pixels
            if brush_points > LIMITS["maxTerrainDocumentDabs"]:
                raise services.MapError("The map has too many terrain brush dabs.")
            if brush_pixels > LIMITS["maxTerrainBrushPixels"]:
                raise services.MapError("The map terrain brushes are too complex.")
        if "shape" in item:
            row["shape"], points, pixels, work = clean_floor_shape(item["shape"], row, doc["cellSize"])
            shape_points += points
            shape_pixels += pixels
            shape_work += work
            if shape_points > LIMITS["maxFloorDocumentPoints"]:
                raise services.MapError("The map has too many floor shape points.")
            if shape_work > LIMITS["maxFloorShapeWork"]:
                raise services.MapError("The map floor shapes are too complex.")
        doc["floors"].append(row)
    walls = {}
    for item in raw.get("walls", []):
        row = base(item, "wall", ("id", "assetId", "x1", "y1", "x2", "y2", "thickness",
                                  *((*WALL_PROPERTY_FIELDS, "dynamic", "artwork") if expanded else ())))
        if "artwork" in item:
            row["artwork"] = objects.boolean(item["artwork"])
        if "dynamic" in item:
            row["dynamic"] = objects.boolean(item["dynamic"])
        for key in ("x1", "x2", "y1", "y2"):
            row[key] = number(item.get(key), 0, bound_columns if key[0] == "x" else bound_rows, f"wall {key}")
        row["thickness"] = number(item.get("thickness"), LIMITS["minWallThickness"], LIMITS["maxWallThickness"], "wall thickness")
        if math.hypot(row["x2"] - row["x1"], row["y2"] - row["y1"]) < 0.1:
            raise services.MapError("Wall endpoints must differ.")
        clean_wall_properties(item, row)
        if row.get("artwork") is not False:
            paint_area += (abs(row["x2"] - row["x1"]) + row["thickness"]) * (abs(row["y2"] - row["y1"]) + row["thickness"])
        walls[row["id"]] = row
        doc["walls"].append(row)
    if paint_area * doc["cellSize"] ** 2 + shape_pixels > LIMITS["maxPaintPixels"]:
        raise services.MapError("The map has too many overlapping painted surfaces.")
    for item in raw.get("doors", []):
        if raw["schemaVersion"] == 1:
            row = base(item, "door", ("id", "assetId", "wallId", "offset", "width", "state"))
            wall = walls.get(str(identifier(item.get("wallId"))))
            if wall is None:
                raise services.MapError("A legacy door must belong to an existing wall.")
            length = math.hypot(wall["x2"] - wall["x1"], wall["y2"] - wall["y1"])
            offset = number(item.get("offset"), 0, length, "door position")
            width = number(item.get("width"), LIMITS["minDoorWidth"], LIMITS["maxDoorWidth"], "door width")
            if offset + width > length + 1e-8:
                raise services.MapError("The legacy door does not fit its wall.")
            ux, uy = (wall["x2"] - wall["x1"]) / length, (wall["y2"] - wall["y1"]) / length
            end = min(length, offset + width)
            row.update(x1=wall["x1"] + ux * offset, y1=wall["y1"] + uy * offset,
                       x2=wall["x1"] + ux * end, y2=wall["y1"] + uy * end,
                       thickness=wall["thickness"])
            # Valid legacy endpoints on a map edge can round just outside it.
            for key in ("x1", "x2", "y1", "y2"):
                row[key] = max(0, min(doc["columns"] if key[0] == "x" else doc["rows"], row[key]))
        else:
            row = base(item, "door", ("id", "assetId", "x1", "y1", "x2", "y2", "thickness", "state",
                                      *(("blueprint", "interactionEnabled", "rotationAnchor", "artwork", *WALL_PROPERTY_FIELDS) if expanded else ())))
            if "artwork" in item:
                row["artwork"] = objects.boolean(item["artwork"])
            for key in ("x1", "x2", "y1", "y2"):
                row[key] = number(item.get(key), 0, bound_columns if key[0] == "x" else bound_rows, f"door {key}")
            row["thickness"] = number(item.get("thickness"), LIMITS["minWallThickness"], LIMITS["maxWallThickness"], "door thickness")
            length = math.hypot(row["x2"] - row["x1"], row["y2"] - row["y1"])
            number(length, LIMITS["minDoorWidth"] - 1e-7, LIMITS["maxDoorWidth"] + 1e-7, "door width")
        row["state"] = item.get("state", "closed")
        if row["state"] not in ("open", "closed", "locked"):
            raise services.MapError("Invalid door state.")
        if "interactionEnabled" in item:
            row["interactionEnabled"] = objects.boolean(item["interactionEnabled"])
        if "rotationAnchor" in item:
            row["rotationAnchor"] = objects.choice(item["rotationAnchor"], {"start", "center", "end"})
        clean_wall_properties(item, row)
        if any(collinear_overlap(row, other) is not None for other in doc["doors"]):
            raise services.MapError("Doors cannot overlap.")
        doc["doors"].append(row)
    if expanded:
        from .regions import MAX_REGIONS
        if len(raw.get("regions", [])) > MAX_REGIONS:
            raise services.MapError("The scene has too many presence regions.")
        for item in raw.get("regions", []):
            fields(item, ("id", "layerId", "x", "y", "width", "height", "name", "enabled", "vertical", "blueprint", "filters"), "presence region")
            row = {"id": str(identifier(item.get("id"))), "layerId": str(identifier(item.get("layerId")))}
            if row["id"] in ids:
                raise services.MapError("Map object identifiers must be unique.")
            ids.add(row["id"])
            if row["layerId"] not in layer_ids:
                raise services.MapError("Choose an existing map layer.")
            row["name"] = clean_name(item.get("name"))
            row["enabled"] = objects.boolean(item.get("enabled", True))
            if "filters" in item:
                from .regions import clean_filters
                row["filters"] = clean_filters(item["filters"], campaign_id=who.campaign_id)
            for key, bound in (("x", bound_columns), ("y", bound_rows), ("width", bound_columns), ("height", bound_rows)):
                row[key] = number(item.get(key), 0 if key in ("x", "y") else .05, bound, f"region {key}")
            if row["x"] + row["width"] > bound_columns + 1e-8 or row["y"] + row["height"] > bound_rows + 1e-8:
                raise services.MapError("A region lies outside the map.")
            if "vertical" in item:
                vertical = item["vertical"]
                fields(vertical, ("bottom", "top"), "region elevation")
                row["vertical"] = {key: None if vertical.get(key) is None else objects.number(vertical[key]) for key in ("bottom", "top")}
                if (row["vertical"]["bottom"] is not None and row["vertical"]["top"] is not None
                        and row["vertical"]["bottom"] > row["vertical"]["top"]):
                    raise services.MapError("Invalid zone elevation.")
            doc["regions"].append(row)
        for item in raw.get("decorations", []):
            row = base(item, "decoration", ("id", "assetId", "x", "y", "width", "height", "rotation", "lever", "torch", "blueprint", "interactionEnabled", "presenceRadius", "empty", "name"))
            if "empty" in item:
                row["empty"] = objects.boolean(item["empty"])
                if not row["empty"] or row["assetId"] is not None or "torch" in item or "lever" not in item:
                    raise services.MapError("An empty object cannot receive images.")
            if "interactionEnabled" in item:
                row["interactionEnabled"] = objects.boolean(item["interactionEnabled"])
            if "torch" in item:
                from .torches import clean_source
                if "lever" in item:
                    raise services.MapError("An object cannot be both a lever and a torch.")
                if row["assetId"] is None:
                    raise services.MapError("Choose an image for the torch.")
                row["torch"] = clean_source(item["torch"])
            if "lever" in item:
                # A lever decoration toggles between Off and On during play.
                if not isinstance(item["lever"], dict) or set(item["lever"]) != {"state"} or item["lever"]["state"] not in ("off", "on"):
                    raise services.MapError("Invalid lever.")
                if row["assetId"] is None and not row.get("empty"):
                    raise services.MapError("Choose an image for the lever.")
                row["lever"] = {"state": item["lever"]["state"]}
            elif "blueprint" in item and "torch" not in item:
                raise services.MapError("Only levers can have a blueprint.")
            if "presenceRadius" in item:
                if not any(key in row for key in ("lever", "torch")):
                    raise services.MapError("Choose a Smart Object before setting its activation area.")
                row["presenceRadius"] = number(item["presenceRadius"], .05, 200, "activation radius")
            for key, bound in (("x", bound_columns), ("y", bound_rows), ("width", bound_columns), ("height", bound_rows)):
                row[key] = number(item.get(key), 0 if key in ("x", "y") else .05, bound, f"decoration {key}")
            row["rotation"] = number(item.get("rotation", 0), -36000, 36000, "decoration rotation") % 360
            angle = math.radians(row["rotation"])
            half_x = (abs(math.cos(angle)) * row["width"] + abs(math.sin(angle)) * row["height"]) / 2
            half_y = (abs(math.sin(angle)) * row["width"] + abs(math.cos(angle)) * row["height"]) / 2
            cx, cy = row["x"] + row["width"] / 2, row["y"] + row["height"] / 2
            if min(cx - half_x, cy - half_y) < -1e-7 or cx + half_x > bound_columns + 1e-7 or cy + half_y > bound_rows + 1e-7:
                raise services.MapError("A decoration lies outside the map.")
            doc["decorations"].append(row)
        for item in raw.get("lights", []):
            row = base(item, "light", ("id", "x", "y", "brightRadius", "dimRadius", "color", "intensity", "enabled", "rotation", "angle", "animation", "elevation"))
            row.pop("assetId")
            row["x"] = number(item.get("x"), 0, bound_columns, "light x")
            row["y"] = number(item.get("y"), 0, bound_rows, "light y")
            native = objects.light({"x": row["x"], "y": row["y"],
                                    "bright_radius": item.get("brightRadius"), "dim_radius": item.get("dimRadius"),
                                    **{key: item.get(key) for key in ("color", "intensity", "enabled")},
                                    **{key: item[key] for key in ("rotation", "angle", "animation", "elevation") if key in item}})
            row.update(brightRadius=native["bright_radius"], dimRadius=native["dim_radius"],
                       **{key: native[key] for key in ("color", "intensity", "enabled", "rotation", "angle", "animation")})
            if "elevation" in item:
                row["elevation"] = native["elevation"]
            doc["lights"].append(row)
        from .extra_objects import effect
        for kind, allowed in NATIVE_EFFECT_FIELDS.items():
            for item in raw.get(kind, []):
                row = base(item, kind, ("id", "x", "y", *allowed))
                row.pop("assetId")
                row["x"] = number(item.get("x"), 0, bound_columns, "effect x")
                row["y"] = number(item.get("y"), 0, bound_rows, "effect y")
                native = effect(kind, {"x": row["x"], "y": row["y"],
                                       **{key: item[key] for key in allowed if key in item}})
                row.update({key: native[key] for key in allowed})
                doc[kind].append(row)
        # Light targets refer to authored source IDs, so validate graphs after
        # every source object has been collected, independently of list order.
        from gravewright.audio.models import Track
        from .blueprints import clean_blueprint
        from .blueprint_runtime import validate_reference_ownership
        light_ids = {row["id"] for row in doc["lights"]}
        track_ids = set(Track.objects.filter(campaign=who.campaign).values_list("pk", flat=True))
        door_asset_ids = {asset_id for asset_id, role in roles.items() if role == "door"}
        for row, original in zip(doc["doors"], raw.get("doors", [])):
            if "blueprint" in original:
                row["blueprint"] = clean_blueprint(original["blueprint"], asset_ids=door_asset_ids,
                                                   appearance_asset_ids=set(roles),
                                                   light_ids=light_ids, track_ids=track_ids, shader_ids={item["id"] for item in doc.get("shaders", [])})
                if row["blueprint"]["kind"] != "door":
                    raise services.MapError("Unsupported blueprint version or object kind.")
        decoration_asset_ids = {asset_id for asset_id, role in roles.items() if role == "decoration"}
        for row, original in zip(doc.get("decorations", []), raw.get("decorations", [])):
            if "blueprint" in original:
                row["blueprint"] = clean_blueprint(original["blueprint"], asset_ids=decoration_asset_ids,
                                                   appearance_asset_ids=set(roles),
                                                   light_ids=light_ids, track_ids=track_ids, shader_ids={item["id"] for item in doc.get("shaders", [])})
                if row["blueprint"]["kind"] != ("torch" if "torch" in row else "lever"):
                    raise services.MapError("Unsupported blueprint version or object kind.")
                if row.get("empty"):
                    from .empty_objects import validate_blueprint
                    validate_blueprint(row["blueprint"], row["id"])
        for row, original in zip(doc.get("regions", []), raw.get("regions", [])):
            if "blueprint" in original:
                row["blueprint"] = clean_blueprint(original["blueprint"], asset_ids=set(), appearance_asset_ids=set(roles),
                                                   light_ids=light_ids, track_ids=track_ids, shader_ids={item["id"] for item in doc.get("shaders", [])})
                if row["blueprint"]["kind"] != "region":
                    raise services.MapError("Unsupported blueprint version or object kind.")
        from .torches import validate_sources
        validate_sources(doc)
        from .blueprint_variables import validate_definitions
        validate_definitions(row["blueprint"] for kind in ("doors", "decorations", "regions")
                             for row in doc.get(kind, []) if "blueprint" in row)
        for kind in ("doors", "decorations", "regions"):
            for row in doc.get(kind, []):
                if "blueprint" in row:
                    from .blueprint_clocks import clock_scope
                    with clock_scope(scene_id):
                        validate_reference_ownership(row["blueprint"], campaign_id=who.campaign_id)
        if source_presence_count(doc) > MAX_REGIONS:
            raise services.MapError("The scene has too many presence regions.")
    # Independent openings can split several overlapping wall strokes. Bound
    # the resulting native geometry before allocating a raster or scene rows.
    count = sum(1 for _ in segments(doc))
    if count + sum(len(doc.get(kind, [])) for kind in ("decorations", "lights", *NATIVE_EFFECT_FIELDS, "regions")) > LIMITS["maxNativeObjects"]:
        raise services.MapError("The map produces too many native objects.")
    from .builder_dynamic import plan
    if count + len(plan(doc)) + sum(len(doc.get(kind, [])) for kind in ("decorations", "lights", *NATIVE_EFFECT_FIELDS, "regions")) > LIMITS["maxNativeObjects"]:
        raise services.MapError("The map produces too many native objects.")
    return doc


def source_presence_count(doc):
    """Count region and object listeners before generating native resources."""
    from .blueprints import has_event_path
    return len(doc.get("regions", [])) + sum(
        any(has_event_path(row.get("blueprint"), event) for event in ("presence:enter", "presence:exit"))
        for row in doc.get("decorations", []))


def expected(value, row):
    if type(value) is not int or value != (row.version if row else 0):
        raise services.MapError("The map project changed. Reload it before saving.", "conflict")


def expected_scene(source, payload):
    """A linked scene can change without changing the editable source revision."""
    if "expected_scene_id" in payload and identifier(payload["expected_scene_id"]) != source.scene_id:
        raise services.MapError("The generated scene changed. Reload the project before updating it.", "conflict")


def fingerprint(action, project_id, payload):
    try:
        raw = json.dumps([action, str(project_id), payload], sort_keys=True, allow_nan=False, separators=(",", ":"))
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise services.MapError("Invalid map project command.") from None
    return hashlib.sha256(raw.encode()).hexdigest()


def replay(campaign_id, user_id, request_id, digest):
    receipt = Receipt.objects.filter(campaign_id=campaign_id, user_id=user_id, request_id=request_id).first()
    if receipt:
        if receipt.result.get("builderFingerprint") != digest:
            raise services.MapError("Use a new request identifier for a different operation.", "conflict")
        return deepcopy(receipt.result["response"])
    return None


def record(campaign_id, user_id, request_id, digest, response):
    Receipt.objects.create(campaign_id=campaign_id, user_id=user_id, request_id=request_id,
                           result={"builderFingerprint": digest, "response": response})


def save(campaign_id, user_id, project_id, payload):
    fields(payload, ("request_id", "expected_version", "folder_id", "document"), "map project command")
    project_id, request_id = identifier(project_id), identifier(payload.get("request_id"))
    digest = fingerprint("save", project_id, payload)
    with transaction.atomic():
        who = authority(campaign_id, user_id)
        Campaign.objects.select_for_update().get(pk=who.campaign_id)
        who = authority(campaign_id, user_id)
        cached = replay(campaign_id, user_id, request_id, digest)
        if cached is not None:
            return cached
        row = MapBuilderProject.objects.filter(pk=project_id).first()
        if row is not None and row.campaign_id != who.campaign_id:
            raise services.MapError("Map project not found.", "not_found")
        expected(payload.get("expected_version"), row)
        doc = clean_document(payload.get("document"), who, scene_id=row.scene_id if row else None)
        target = services.folder(payload.get("folder_id"), who)
        if row is None:
            row = MapBuilderProject(id=project_id, campaign=who.campaign)
        else:
            # Delivery-one projects have no stored ownership record. Capture
            # proven native IDs before replacing their original source document.
            adopted = legacy_generation(row, who)
            if adopted is not None:
                row.generation = adopted
            row.version += 1
        row.name, row.folder, row.document = doc["name"], target, doc
        row.save()
        response = {"project": view(row, who)}
        record(campaign_id, user_id, request_id, digest, response)
    return response


def collinear_overlap(base, other):
    """Return the positive shared interval measured from a segment's first end."""
    dx, dy = base["x2"] - base["x1"], base["y2"] - base["y1"]
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    offsets = []
    for x, y in ((other["x1"], other["y1"]), (other["x2"], other["y2"])):
        x, y = x - base["x1"], y - base["y1"]
        if abs(x * uy - y * ux) > 1e-7:
            return None
        offsets.append(x * ux + y * uy)
    start, end = max(0, min(offsets)), min(length, max(offsets))
    return (start, end) if end - start > 1e-7 else None


def segments(doc):
    """Cut every collinear wall at independent doors, then yield each door once."""
    epsilon = 0.02 / doc["cellSize"]
    count = 0

    def bounded(span):
        nonlocal count
        count += 1
        if count > LIMITS["maxNativeObjects"]:
            raise services.MapError("The map produces too many wall segments.")
        return span

    for wall in doc["walls"]:
        length = math.hypot(wall["x2"] - wall["x1"], wall["y2"] - wall["y1"])

        def span(start, end):
            return {"wall": wall, "door": None,
                    "x1": wall["x1"] + (wall["x2"] - wall["x1"]) * start / length,
                    "y1": wall["y1"] + (wall["y2"] - wall["y1"]) * start / length,
                    "x2": wall["x1"] + (wall["x2"] - wall["x1"]) * end / length,
                    "y2": wall["y1"] + (wall["y2"] - wall["y1"]) * end / length}

        cursor = 0
        intervals = sorted(interval for door in doc["doors"]
                           if (interval := collinear_overlap(wall, door)) is not None)
        for start, end in intervals:
            if start - cursor > epsilon:
                yield bounded(span(cursor, start))
            cursor = max(cursor, end)
        if length - cursor > epsilon:
            yield bounded(span(cursor, length))
    for door in doc["doors"]:
        yield bounded({"wall": door, "door": door,
                       **{key: door[key] for key in ("x1", "y1", "x2", "y2")}})


def native_objects(doc, scene, *, dynamic_planes=(), stored=None):
    result = []
    if dynamic_planes:
        from .builder_dynamic import native_planes
        result.extend(native_planes(doc, scene, dynamic_planes, stored))
    cell = doc["cellSize"]

    def append(source_id, kind, data, source=None):
        if source is not None:
            copy_name(data, source)
        row = SceneObject(id=uuid.uuid5(scene.pk, source_id), scene=scene, kind=kind, data=data)
        # Keep source identity outside native object data. Archives remap native
        # IDs, while the authored source IDs continue to identify the same door.
        row.builder_source_id = source_id
        result.append(row)

    spans = list(segments(doc))
    span_counts = {}
    for span in spans:
        key = span["wall"]["id"]
        span_counts[key] = span_counts.get(key, 0) + 1
    for span in spans:
        door = span["door"]
        raw = {**{key: span[key] * cell for key in ("x1", "y1", "x2", "y2")},
               "kind": "door" if door else "wall",
               "door_state": door["state"] if door else "closed",
               **{key: span["wall"][key] for key in WALL_PROPERTY_FIELDS if key in span["wall"]}}
        if door and door["assetId"] and door.get("artwork") is not False:
            raw.update(asset_id=door["assetId"], thickness=span["wall"]["thickness"] * cell)
        if door and "rotationAnchor" in door:
            raw["rotationAnchor"] = door["rotationAnchor"]
        data = objects.wall(raw, campaign_id=scene.campaign_id)
        if door and "interactionEnabled" in door:
            data["interactionEnabled"] = door["interactionEnabled"]
        # Independent collision walls keep their source identity when moved.
        # Split artwork walls retain coordinate identities for their spans.
        source_id = (door["id"] if door else span["wall"]["id"]
                     if span["wall"].get("artwork") is False and span_counts[span["wall"]["id"]] == 1
                     else f'{span["wall"]["id"]}:' + ':'.join(
                         format(span[key], '.12g') for key in ("x1", "y1", "x2", "y2")))
        append(source_id, "walls", data, span["wall"])
    from .extra_objects import image
    layers = {layer["id"]: index for index, layer in enumerate(doc.get("layers", []))}
    for index, row in enumerate(doc.get("decorations", [])):
        if row.get("empty"):
            from .empty_objects import native
            data = native(scene, row, cell,
                          layers.get(row.get("layerId"), 0) + index / (LIMITS["maxObjects"] + 1))
            append(row["id"], "images", data, row)
            continue
        if not row["assetId"]:
            continue
        asset = MapAsset.objects.filter(pk=row["assetId"], campaign_id=scene.campaign_id).first()
        if asset is None:
            raise services.MapError("Choose an image from this campaign.")
        scale = min(row["width"] * cell / asset.width, row["height"] * cell / asset.height)
        previous = None
        element_key = "torch" if "torch" in row else "lever"
        if element_key in row:
            previous = {"asset_id": row["assetId"], "scale": scale,
                        element_key: {"state": row[element_key]["state"], "baseAssetId": row["assetId"], "baseLayer": "map",
                                  "width": row["width"] * cell, "height": row["height"] * cell}}
            if element_key == "torch":
                from .torches import COMPONENTS
                source_by_id = {child["id"]: child for kind in COMPONENTS.values() for child in doc.get(kind, [])}
                previous["torch"].update(lit=row["torch"]["lit"], baseRotation=row["rotation"], components={
                    kind: {"id": str(uuid.uuid5(scene.pk, row["torch"][key])),
                           "enabled": source_by_id[row["torch"][key]]["enabled"]}
                    for key, kind in COMPONENTS.items() if key in row["torch"]})
        elif not .001 <= scale <= 100:
            # Contain-fit artwork can need an extreme scale even for a small,
            # bounded box. Retain that box through native edits and archives.
            previous = {"asset_id": row["assetId"], "scale": scale,
                        "spriteBase": {"assetId": row["assetId"], "layer": "map",
                                       "width": row["width"] * cell, "height": row["height"] * cell},
                        "sprite": {"appearance": "asset", "assetId": row["assetId"]}}
        data = image(scene, {"asset_id": row["assetId"],
                             "x": (row["x"] + row["width"] / 2) * cell,
                             "y": (row["y"] + row["height"] / 2) * cell,
                             "scale": scale,
                             "rotation": row["rotation"] + (90 if row.get("torch", {}).get("state") == "on" else 0), "layer": "map",
                             "z_index": layers.get(row.get("layerId"), 0) + index / (LIMITS["maxObjects"] + 1)}, previous)
        if "interactionEnabled" in row:
            data["interactionEnabled"] = row["interactionEnabled"]
        if "presenceRadius" in row:
            data["presenceRadius"] = row["presenceRadius"] * cell
        append(row["id"], "images", data, row)
        if "torch" in row:
            result[-1].builder_torch_rotation = row["rotation"]
    if doc.get("lights") and not settings.DYNAMIC_LIGHTING_ENABLED:
        raise services.MapError("Dynamic lighting is disabled.", "forbidden")
    for row in doc.get("lights", []):
        data = objects.light({"x": row["x"] * cell, "y": row["y"] * cell,
                              "bright_radius": row["brightRadius"], "dim_radius": row["dimRadius"],
                              **{key: row[key] for key in ("color", "intensity", "enabled", "rotation", "angle", "animation", "elevation") if key in row}})
        append(row["id"], "lights", data, row)
    from .extra_objects import effect
    for kind, allowed in NATIVE_EFFECT_FIELDS.items():
        for row in doc.get(kind, []):
            data = effect(kind, {"x": row["x"] * cell, "y": row["y"] * cell,
                                 **{key: row[key] for key in allowed}})
            append(row["id"], kind, data, row)
    visible_layers = {layer["id"]: layer["visible"] for layer in doc.get("layers", [])}
    for row in doc.get("regions", []):
        append(row["id"], "zones", {
            "geometry": {"shape": "rect", **{key: row[key] * cell for key in ("x", "y", "width", "height")}},
            "type": "presence", "audience": {"kind": "gm"},
            "vertical": deepcopy(row.get("vertical", {"bottom": None, "top": None})),
            "enabled": row["enabled"] and visible_layers[row["layerId"]], "tags": [],
            "packageProvenance": {"packageId": "core", "providerId": None},
            "region": {"name": row["name"], "state": "empty", "occupants": [],
                       **({"filters": deepcopy(row["filters"])} if "filters" in row else {})}})
    if len(result) > LIMITS["maxNativeObjects"]:
        raise services.MapError("The map produces too many native objects.")
    remap_native_blueprints(result, doc)
    return result


# Door fields changed by play rather than authoring; updates keep them. Set
# barrier actions change the behaviors and their derived blocking flags.
LIVE_DOOR_FIELDS = ("door_state", "sprite", "movement_behavior", "vision_behavior", "light_behavior",
                    "sound_behavior", "blocks_light", "blocks_sight")
# A lever's state and the image it shows for that state change during play.
LIVE_LEVER_FIELDS = ("sprite", "asset_id", "src", "natural_width", "natural_height", "scale", "layer")


def ordinary_image_base(data):
    """Return authored image identity and box without exposing its live override."""
    if isinstance(data.get("spriteBase"), dict):
        return deepcopy(data["spriteBase"])
    return {"assetId": data["asset_id"], "layer": data["layer"],
            "width": data["natural_width"] * data["scale"],
            "height": data["natural_height"] * data["scale"]}


def strip_live(before, after, *, kind=None):
    """Ignore play state when comparing generated data with the scene."""
    for data in (before, after):
        data.pop("automationVariables", None)
        data.pop("automationMemory", None)
        data.pop("interactionEnabled", None)
        data.pop("areaPresence", None)
        if kind == "images" and data.get("empty") is True:
            data["layer"] = "gm-image-layer"
            if isinstance(data.get("lever"), dict):
                data["lever"]["baseLayer"] = "gm-image-layer"
    if kind == "images" and isinstance(before.get("surface"), dict):
        for data in (before, after):
            data.pop("layer", None)
            for field in ("materialId", "materialCrop"):
                data.get("surface", {}).pop(field, None)
        return
    if kind == "images" and not any(key in before for key in ("lever", "torch", "surfacePlane")):
        for data in (before, after):
            base = ordinary_image_base(data)
            for key in LIVE_LEVER_FIELDS:
                data.pop(key, None)
            data["spriteBase"] = base
        return
    if kind == "zones" and "region" in before:
        for data in (before, after):
            data.pop("enabled", None)
            for key in ("state", "occupants", "arrivalGates"):
                data.get("region", {}).pop(key, None)
        return
    if kind in LIVE_ENABLED_KINDS:
        if type(before.get("enabled")) is not bool or type(after.get("enabled")) is not bool:
            return
        live = ("enabled",)
    elif before.get("kind") == "door":
        live = (*LIVE_DOOR_FIELDS, "discovered")
    elif "lever" in before or "torch" in before:
        live = LIVE_LEVER_FIELDS
        # The base image, layer and box remain authored geometry. Only the
        # nested state changes during play; ignoring the full record would
        # silently overwrite a GM's native resize or image/layer edit.
        for data in (before, after):
            key = "torch" if "torch" in data else "lever"
            if isinstance(data.get(key), dict):
                data[key].pop("state", None)
                if key == "torch":
                    data[key].pop("lit", None)
                    for child in data[key].get("components", {}).values():
                        child.pop("enabled", None)
                    data.pop("rotation", None)
    else:
        return
    for key in live:
        before.pop(key, None)
        after.pop(key, None)


def remap_native_blueprints(rows, doc):
    """Bind authored targets after native IDs, including archive IDs, are final."""
    lights = {row.builder_source_id: str(row.pk) for row in rows if row.kind == "lights"}
    shaders = {row.builder_source_id: str(row.pk) for row in rows if row.kind == "shaders"}
    doors = {row["id"]: row for row in doc["doors"]}
    levers = {row["id"]: row for row in doc.get("decorations", []) if "lever" in row or "torch" in row}
    regions = {row["id"]: row for row in doc.get("regions", [])}
    # References keep authored IDs across doors, levers and composed torches.
    live_sources = {**doors, **{row["id"]: row for row in doc.get("decorations", [])}, **regions,
                    **{row["id"]: row for kind in ("floors", "walls") for row in doc[kind] if row.get("dynamic") is True}}
    native_doors = {row.builder_source_id: str(row.pk) for row in rows
                    if row.kind in ("walls", "images", "zones") and row.builder_source_id in live_sources}

    def bind(blueprint):
        for graph in blueprint["graphs"].values():
            for node in graph["nodes"]:
                if node["type"] in ("light", "lightReference"):
                    node["targetId"] = lights.get(node["targetId"], node["targetId"])
                elif node["type"] == "shaderControl":
                    node["targetId"] = shaders.get(node["targetId"], node["targetId"])
                elif node["type"] == "reference":
                    node["targetId"] = native_doors.get(node["targetId"], node["targetId"])
                elif node["type"] == "teleport":
                    node["destinationId"] = native_doors.get(node["destinationId"], node["destinationId"])
                elif node["type"] == "elementGroup":
                    mapping = native_doors if node["memberType"] == "element" else lights if node["memberType"] == "light" else {}
                    node["targetIds"] = [mapping.get(identifier, identifier) for identifier in node["targetIds"]]
        return blueprint
    from .blueprint_runtime import apply_lever_appearance
    for row in rows:
        if row.kind == "images" and row.builder_source_id in levers:
            source = levers[row.builder_source_id]
            before = deepcopy(row.data)
            if hasattr(row, "builder_torch_rotation"):
                before["rotation"] = row.builder_torch_rotation
                del row.builder_torch_rotation
            if "torch" in source:
                from .torches import COMPONENTS
                by_source = {child.builder_source_id: child for child in rows}
                authored = {child["id"]: child for kind in COMPONENTS.values() for child in doc.get(kind, [])}
                row.data["torch"]["components"] = {
                    kind: {"id": str(by_source[source["torch"][key]].pk),
                           "enabled": getattr(row, "builder_torch_enabled", {}).get(kind, authored[source["torch"][key]]["enabled"])}
                    for key, kind in COMPONENTS.items() if key in source["torch"]}
                if hasattr(row, "builder_torch_enabled"):
                    del row.builder_torch_enabled
            if "blueprint" in source:
                row.data["blueprint"] = bind(deepcopy(source["blueprint"]))
            apply_lever_appearance(row)
            if "torch" in source:
                from .torches import sync_components
                sync_components(row, before, rows=rows)
            continue
        source = (regions if row.kind == "zones" else doors).get(row.builder_source_id)
        if row.kind not in ("walls", "zones") or not source or "blueprint" not in source:
            continue
        row.data["blueprint"] = bind(deepcopy(source["blueprint"]))
        if row.kind == "walls":
            row.data.setdefault("thickness", source["thickness"] * doc["cellSize"])


def generation_manifest(scene, doc, rows):
    """Store authored resources explicitly; all other scene resources stay external."""
    source_enabled = {row["id"]: row["enabled"] for kind in LIVE_ENABLED_KINDS for row in doc.get(kind, [])}
    source_discovered = {row["id"]: row.get("discovered", False) for row in doc["doors"]}
    source_interaction = {row["id"]: row.get("interactionEnabled", True)
                          for key in ("doors", "decorations") for row in doc.get(key, [])}
    visible = {layer["id"]: layer["visible"] for layer in doc.get("layers", [])}
    region_defaults = {row["id"]: {"enabled": row["enabled"], "layerId": row["layerId"], "visible": visible[row["layerId"]]}
                       for row in doc.get("regions", [])}
    surface_defaults = {row["id"]: {"assetId": row["assetId"], "layerId": row["layerId"]}
                        for kind in ("floors", "walls") for row in doc[kind] if row.get("dynamic") is True}
    return {"formatVersion": 1, "sceneId": str(scene.pk), "sourceDocument": deepcopy(doc),
            "width": scene.width, "height": scene.height, "cellSize": doc["cellSize"],
            **({"dynamicDocument": deepcopy(doc)} if surface_defaults else {}),
            "objects": [{"id": str(row.pk), "sourceId": row.builder_source_id,
                         "kind": row.kind, "data": deepcopy(row.data),
                         **({"nativeOverrides": deepcopy(row.builder_native_overrides)}
                            if hasattr(row, "builder_native_overrides") else {}),
                         **({"sourceEnabled": source_enabled[row.builder_source_id]}
                            if row.kind in LIVE_ENABLED_KINDS else {}),
                         **({"sourceDiscovered": source_discovered[row.builder_source_id]}
                            if row.kind == "walls" and row.data.get("kind") == "door" else {}),
                         **({"sourceInteractionEnabled": source_interaction[row.builder_source_id]}
                            if row.builder_source_id in source_interaction else {}),
                         **({"sourceRegionDefaults": region_defaults[row.builder_source_id]}
                            if row.builder_source_id in region_defaults else {}),
                         **({"sourceSurfaceDefaults": surface_defaults[row.builder_source_id]}
                            if row.builder_source_id in surface_defaults else {})} for row in rows]}


def legacy_generation(source, who):
    """Derive delivery-one ownership only from its exact IDs and native data.

    This is read-only. Manual objects are never adopted by proximity, appearance
    or kind, and a changed or missing generated object makes adoption fail.
    """
    if (source.generation != {} or not source.scene_id
            or not isinstance(source.document, dict)
            or source.document.get("schemaVersion") not in (1, 2)):
        return None
    scene = source.scene
    if scene.campaign_id != who.campaign_id:
        return None
    try:
        doc = clean_document(source.document, who, scene_id=source.scene_id)
        if (scene.width != doc["columns"] * doc["cellSize"]
                or scene.height != doc["rows"] * doc["cellSize"]
                or not isinstance(scene.settings, dict)
                or scene.settings.get("gridSize") != doc["cellSize"]):
            return None
        rows = native_objects(doc, scene)
        old_ids = []
        for index, span in enumerate(segments(doc)):
            key = span["door"]["id"] if span["door"] else f'{span["wall"]["id"]}:{index}'
            old_ids.append(uuid.uuid5(scene.pk, key))
        current = {row.pk: row for row in scene.elements.filter(pk__in=old_ids)}
        for row, old_id in zip(rows, old_ids):
            existing = current.get(old_id)
            if existing is None or existing.kind != row.kind:
                return None
            before, after = deepcopy(row.data), deepcopy(existing.data)
            strip_live(before, after, kind=row.kind)
            if before != after:
                return None
            row.pk, row.data = old_id, deepcopy(existing.data)
        return generation_manifest(scene, doc, rows)
    except services.MapError:
        return None


def update_target(source, who, payload, doc):
    expected_scene(source, payload)
    if not source.scene_id:
        raise services.MapError("Generate a scene before updating it.", "conflict")
    scene = services.scene(source.scene_id, who, write=True)
    from .blueprint_variables import validate_definitions
    validate_definitions((row["blueprint"] for kind in ("doors", "decorations", "regions")
                          for row in doc.get(kind, []) if "blueprint" in row),
                         scene.settings.get("automationVariables", {}))
    if type(payload.get("expected_scene_version")) is not int or payload["expected_scene_version"] != scene.version:
        raise services.MapError("The scene changed. Reload the project before updating it.", "conflict")
    manifest = source.generation
    if manifest == {}:
        manifest = legacy_generation(source, who) or manifest
    if (not isinstance(manifest, dict) or manifest.get("formatVersion") != 1
            or manifest.get("sceneId") != str(scene.pk) or not isinstance(manifest.get("objects"), list)):
        raise services.MapError("This scene has no update history. Generate a new scene to preserve existing content.", "conflict")
    source.generation = manifest
    owned = {}
    source_ids = set()
    for previous in manifest["objects"]:
        if (not isinstance(previous, dict) or not isinstance(previous.get("data"), dict)
                or not isinstance(previous.get("sourceId"), str) or not previous["sourceId"]
                or len(previous["sourceId"]) > 256 or previous["sourceId"] in source_ids):
            raise services.MapError("This scene has no valid update history. Generate a new scene.", "conflict")
        source_ids.add(previous["sourceId"])
        pk = str(identifier(previous.get("id")))
        if pk in owned:
            raise services.MapError("This scene has no valid update history. Generate a new scene.", "conflict")
        current = scene.elements.filter(pk=pk).first()
        before, after = deepcopy(previous["data"]), deepcopy(current.data) if current else None
        if current and current.kind in ("walls", "images", "zones", *LIVE_ENABLED_KINDS):
            # Live use of a door or lever is independent of its authored geometry.
            strip_live(before, after, kind=current.kind)
        if current is None or current.kind != previous.get("kind") or before != after:
            raise services.MapError("A generated object was changed in the VTT. Restore it or generate a new scene.", "conflict")
        owned[pk] = current
    from .regions import MAX_REGIONS, presence_rows
    external_regions = sum(str(row.pk) not in owned for row in presence_rows(scene))
    if external_regions + source_presence_count(doc) > MAX_REGIONS:
        raise services.MapError("The scene has too many presence regions.")
    changing_geometry = ((scene.width, scene.height) != canvas_size(doc)
                         or manifest.get("cellSize") != doc["cellSize"]
                         or scene_options(manifest.get("sourceDocument") or doc) != scene_options(doc))
    if changing_geometry:
        env = SceneState.objects.filter(scene=scene).first()
        if (scene.tokens.exists() or scene.elements.exclude(pk__in=owned).exists()
                or env and (env.drawings or env.fog)):
            raise services.MapError("Keep the dimensions and cell size when updating a scene with manually placed content.", "conflict")
    return scene, owned


def prepare(doc, campaign_id, stored, tiles):
    """Bound raster and PNG memory across the render-to-tiler handoff."""
    from .builder_render import render
    from .builder_dynamic import baked_document

    with _preparing:
        raster = render(baked_document(doc), campaign_id)
        try:
            def save_tile(lod, x, y, content):
                candidate = "maps/tiles/" + uuid.uuid4().hex + ".webp"
                # Storage can rename a collision. Only the returned path belongs
                # to this operation after success; an older candidate is private
                # data we must preserve. The UUID candidate also lets local
                # storage remove a partial write when save raises before return.
                existed = default_storage.exists(candidate)
                try:
                    path = default_storage.save(candidate, content)
                except Exception:
                    if not existed:
                        default_storage.delete(candidate)
                    raise
                stored.append(path)
                tiles.append(Tile(lod=lod, x=x, y=y, file=path, byte_size=content.size))

            return tiling.generate_pyramid(raster, save_tile)
        finally:
            raster.close()


def generate(campaign_id, user_id, project_id, payload):
    """Render outside the write transaction, then recheck revision and authority."""
    fields(payload, ("request_id", "expected_version"), "scene generation command")
    project_id, request_id = identifier(project_id), identifier(payload.get("request_id"))
    digest = fingerprint("generate", project_id, payload)
    who = authority(campaign_id, user_id)
    cached = replay(campaign_id, user_id, request_id, digest)
    if cached is not None:
        return cached
    source = project(project_id, who)
    expected(payload.get("expected_version"), source)
    doc = clean_document(source.document, who)
    stored, tiles = [], []
    try:
        from .builder_dynamic import prepare as prepare_dynamic
        with _preparing:
            dynamic_planes = prepare_dynamic(doc, who.campaign_id, stored)
            width, height, max_lod = prepare(doc, who.campaign_id, stored, tiles)
        with transaction.atomic():
            who = authority(campaign_id, user_id)
            Campaign.objects.select_for_update().get(pk=who.campaign_id)
            who = authority(campaign_id, user_id)
            cached = replay(campaign_id, user_id, request_id, digest)
            if cached is not None:
                return cached
            source = project(project_id, who)
            expected(payload.get("expected_version"), source)
            # Asset removal during rendering must not publish dangling door references.
            clean_document(source.document, who)
            target = services.folder(source.folder_id, who)
            scene = Scene.objects.create(campaign=who.campaign, folder=target,
                                         name=doc["name"], visibility="gm", width=width, height=height,
                                         tile_size=tiling.TILE_SIZE, max_lod=max_lod,
                                         settings=services.settings(scene_options(doc)))
            for tile in tiles:
                tile.scene = scene
            Tile.objects.bulk_create(tiles)
            generated = native_objects(doc, scene, dynamic_planes=dynamic_planes, stored=stored)
            from .regions import baseline
            baseline(scene, generated)
            SceneObject.objects.bulk_create(generated)
            if doc.get("lights"):
                SceneState.objects.create(scene=scene, lighting={"mode": "dynamic", "darkness": 1, "lights_out": False})
            SceneNavigation.objects.update_or_create(membership=who, defaults={"scene": scene})
            source.scene = scene
            source.generation = generation_manifest(scene, doc, generated)
            source.save(update_fields=["scene", "generation"])
            response = {"project": view(source, who), "scene": services.view(scene)}
            record(campaign_id, user_id, request_id, digest, response)
            from gravewright.realtime.dispatch import changed
            changed(campaign_id, user_id, "maps", "builder-generate", request_id, {"map": response["scene"]})
        stored.clear()
        return response
    finally:
        for path in stored:
            default_storage.delete(path)


def update(campaign_id, user_id, project_id, payload):
    """Replace only previously generated resources in the same native scene."""
    fields(payload, ("request_id", "expected_version", "expected_scene_version", "expected_scene_id"), "scene update command")
    project_id, request_id = identifier(project_id), identifier(payload.get("request_id"))
    digest = fingerprint("update", project_id, payload)
    who = authority(campaign_id, user_id)
    cached = replay(campaign_id, user_id, request_id, digest)
    if cached is not None:
        return cached
    source = project(project_id, who)
    expected(payload.get("expected_version"), source)
    doc = clean_document(source.document, who, scene_id=source.scene_id)
    initial_manifest = deepcopy(source.generation)
    initial_scene, _ = update_target(source, who, payload, doc)
    stored, tiles = [], []
    try:
        from .builder_dynamic import prepare as prepare_dynamic
        with _preparing:
            dynamic_planes = prepare_dynamic(doc, who.campaign_id, stored)
            width, height, max_lod = prepare(doc, who.campaign_id, stored, tiles)
        with transaction.atomic():
            who = authority(campaign_id, user_id)
            Campaign.objects.select_for_update().get(pk=who.campaign_id)
            who = authority(campaign_id, user_id)
            cached = replay(campaign_id, user_id, request_id, digest)
            if cached is not None:
                return cached
            source = project(project_id, who)
            expected(payload.get("expected_version"), source)
            clean_document(source.document, who, scene_id=source.scene_id)
            if source.scene_id != initial_scene.pk or source.generation != initial_manifest:
                raise services.MapError("The generated scene changed. Reload the project before updating it.", "conflict")
            scene, owned = update_target(source, who, payload, doc)
            generated = native_objects(doc, scene, dynamic_planes=dynamic_planes, stored=stored)
            previous_sources = {row["sourceId"]: owned[row["id"]] for row in source.generation["objects"]}
            # Imported independent walls keep their original identity even when
            # artwork is enabled. Never infer ownership for ambiguous splits.
            independent = {entry["sourceId"] for entry in source.generation["objects"]
                           if entry["kind"] == "walls" and entry["data"].get("kind") == "wall"
                           and ":" not in entry["sourceId"]}
            counts = {}
            for row in generated:
                if row.kind == "walls" and row.data.get("kind") == "wall":
                    key = row.builder_source_id.split(":", 1)[0]
                    counts[key] = counts.get(key, 0) + 1
            for row in generated:
                key = row.builder_source_id.split(":", 1)[0]
                if row.kind == "walls" and key in independent and counts.get(key) == 1:
                    row.builder_source_id = key
            previous_overrides = {row["sourceId"]: row.get("nativeOverrides", {}) for row in source.generation["objects"]}
            previous_enabled_defaults = {row["sourceId"]: row.get("sourceEnabled", row["data"].get("enabled"))
                                         for row in source.generation["objects"] if row.get("kind") in LIVE_ENABLED_KINDS}
            previous_shader_defaults = {item["id"]:item for item in source.generation.get("sourceDocument",{}).get("shaders",[])}
            previous_discovered_defaults = {row["sourceId"]: row.get("sourceDiscovered", row["data"].get("discovered", False))
                                            for row in source.generation["objects"]
                                            if row.get("kind") == "walls" and row["data"].get("kind") == "door"}
            previous_interaction_defaults = {row["sourceId"]: row.get("sourceInteractionEnabled", True)
                                             for row in source.generation["objects"]}
            previous_regions = {row["sourceId"]: row for row in source.generation["objects"] if row.get("kind") == "zones"}
            previous_surfaces = {row["sourceId"]: row.get("sourceSurfaceDefaults") for row in source.generation["objects"]
                                 if isinstance(row.get("data", {}).get("surface"), dict)}
            authored_surfaces = {item["id"]: {"assetId": item["assetId"], "layerId": item["layerId"]}
                                 for key in ("floors", "walls") for item in doc[key] if item.get("dynamic") is True}
            visible_layers = {layer["id"]: layer["visible"] for layer in doc.get("layers", [])}
            authored_regions = {item["id"]: {"enabled": item["enabled"], "layerId": item["layerId"],
                                             "visible": visible_layers[item["layerId"]]}
                                for item in doc.get("regions", [])}
            for row in generated:
                current = previous_sources.get(row.builder_source_id)
                if current:
                    if current.kind != row.kind:
                        raise services.MapError("A generated object changed type. Generate a new scene to preserve the existing object.", "conflict")
                    row.pk = current.pk
                if current is None and SceneObject.objects.filter(pk=row.pk).exists():
                    raise services.MapError("A generated object identifier is already in use.", "conflict")
                if current and row.kind == "walls" and row.data.get("kind") == "door":
                    row.data["door_state"] = current.data["door_state"]
                    if row.data["discovered"] == previous_discovered_defaults.get(row.builder_source_id):
                        row.data["discovered"] = current.data["discovered"]
                    if "sprite" in current.data and "blueprint" in row.data:
                        row.data["sprite"] = current.data["sprite"]
                    if "blueprint" in row.data:
                        for field in LIVE_DOOR_FIELDS[2:]:
                            if field in current.data:
                                row.data[field] = current.data[field]
                elif (current and row.kind == "images"
                      and any(key in row.data and isinstance(current.data.get(key), dict) for key in ("lever", "torch"))):
                    key = "torch" if "torch" in row.data else "lever"
                    row.data[key]["state"] = current.data[key]["state"]
                    if key == "torch":
                        row.data[key]["lit"] = current.data[key]["lit"]
                        from .torches import COMPONENTS
                        source_torch = next(source["torch"] for source in doc["decorations"] if source["id"] == row.builder_source_id)
                        current_components = current.data["torch"]["components"]
                        authored_enabled = {child["id"]: child["enabled"] for kind in COMPONENTS.values() for child in doc.get(kind, [])}
                        row.builder_torch_enabled = {
                            kind: current_components[kind]["enabled"]
                            for field, kind in COMPONENTS.items() if field in source_torch and kind in current_components
                            and source_torch[field] in previous_sources
                            and current_components[kind]["id"] == str(previous_sources[source_torch[field]].pk)
                            and authored_enabled[source_torch[field]] == previous_enabled_defaults.get(source_torch[field])}
                    if "sprite" in current.data:
                        row.data["sprite"] = current.data["sprite"]
                elif (current and row.kind == "images" and isinstance(current.data.get("spriteBase"), dict)
                      and not any(key in row.data for key in ("lever", "torch", "surface", "surfacePlane"))
                      and all(ordinary_image_base(row.data)[key] == ordinary_image_base(current.data)[key]
                              for key in ("assetId", "width", "height"))):
                    from .blueprint_actions import change_sprite
                    change_sprite(scene, row, current.data["sprite"])
                elif (current and row.kind in LIVE_ENABLED_KINDS
                      and row.data["enabled"] == previous_enabled_defaults.get(row.builder_source_id)):
                    row.data["enabled"] = current.data["enabled"]
                if current and row.kind == "shaders":
                    from .shader_controls import SHADER_RANGES
                    defaults = previous_shader_defaults.get(row.builder_source_id,{})
                    for property_name in ("color",*SHADER_RANGES):
                        if property_name in defaults and row.data[property_name] == defaults[property_name]:
                            row.data[property_name] = current.data[property_name]
                if current and row.kind == "zones" and "region" in row.data:
                    if "arrivalGates" in current.data.get("region", {}):
                        row.data["region"]["arrivalGates"] = deepcopy(current.data["region"]["arrivalGates"])
                    previous_region = previous_regions.get(row.builder_source_id, {})
                    defaults = previous_region.get("sourceRegionDefaults")
                    unchanged = (authored_regions[row.builder_source_id] == defaults if defaults is not None else
                                 row.data["enabled"] == previous_region.get("data", {}).get("enabled"))
                    if unchanged:
                        row.data["enabled"] = current.data["enabled"]
                if current and "automationVariables" in current.data and "blueprint" in row.data:
                    from .blueprint_variables import validate_element_store
                    row.data["automationVariables"] = deepcopy(validate_element_store(
                        row.data["blueprint"], current.data["automationVariables"]))
                if (current and isinstance(row.data.get("surface"), dict)
                        and authored_surfaces.get(row.builder_source_id) == previous_surfaces.get(row.builder_source_id)):
                    row.data["layer"] = current.data["layer"]
                    for field in ("materialId", "materialCrop"):
                        if field in current.data.get("surface", {}):
                            row.data["surface"][field] = deepcopy(current.data["surface"][field])
                if current and "interactionEnabled" in current.data:
                    authored_row = next((item for key in ("doors", "decorations") for item in doc.get(key, [])
                                         if item["id"] == row.builder_source_id), {})
                    previous_default = previous_interaction_defaults.get(row.builder_source_id, True)
                    if authored_row.get("interactionEnabled", True) == previous_default:
                        row.data["interactionEnabled"] = current.data["interactionEnabled"]
                if current and "automationMemory" in current.data and "blueprint" in row.data:
                    from .blueprint_memory import reconcile_memory
                    memory = reconcile_memory(row.data["blueprint"], current.data["automationMemory"])
                    if memory:
                        row.data["automationMemory"] = memory
            remap_native_blueprints(generated, doc)
            from .builder_sync import apply_overrides
            for row in generated:
                apply_overrides(row, previous_overrides.get(row.builder_source_id))
            old_files = list(scene.tiles.values_list("file", flat=True))
            scene.tiles.all().delete()
            for tile in tiles:
                tile.scene = scene
            Tile.objects.bulk_create(tiles)
            keeping = {str(row.pk) for row in generated}
            scene.elements.filter(pk__in=set(owned) - keeping).delete()
            for row in generated:
                current = owned.get(str(row.pk))
                if current:
                    if current.data != row.data:
                        current.data = row.data
                        current.version += 1
                        current.save(update_fields=["data", "version"])
                else:
                    row.save(force_insert=True)
            scene.width, scene.height, scene.max_lod = width, height, max_lod
            scene.tile_size = tiling.TILE_SIZE
            # All scene choices (name, folder, visibility, environment and sound)
            # belong to the VTT once generated. Only source grid geometry changes.
            if (initial_manifest.get("cellSize") != doc["cellSize"]
                    or scene_options(initial_manifest.get("sourceDocument") or doc) != scene_options(doc)):
                options = scene_options(doc)
                if (initial_manifest.get("sourceDocument", {}).get("sceneGeometry")
                        and not doc.get("sceneGeometry")):
                    options.update(imageScale=1, gridOffsetX=0, gridOffsetY=0)
                scene.settings = services.settings(options, scene.settings)
            scene.version += 1
            scene.save()
            from .regions import baseline
            for row in baseline(scene, generated):
                current = scene.elements.get(pk=row.pk)
                if current.data != row.data:
                    current.data = row.data
                    current.version += 1
                    current.save(update_fields=["data", "version"])
            source.generation = generation_manifest(scene, doc, generated)
            if initial_manifest.get("importWarnings"):
                source.generation["importWarnings"] = initial_manifest["importWarnings"]
            source.save(update_fields=["generation"])
            from .blueprint_delays import cancel_invalid_delays
            cancel_invalid_delays(scene)
            response = {"project": view(source, who), "scene": services.view(scene)}
            record(campaign_id, user_id, request_id, digest, response)
            from gravewright.realtime.dispatch import changed
            changed(campaign_id, user_id, "maps", "update", request_id, {"map": response["scene"]})
            transaction.on_commit(lambda: [default_storage.delete(path) for path in old_files], robust=True)
            from .builder_dynamic import prune_generated
            transaction.on_commit(lambda: prune_generated(scene), robust=True)
        stored.clear()
        return response
    finally:
        for path in stored:
            default_storage.delete(path)
