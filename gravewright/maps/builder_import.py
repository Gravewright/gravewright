"""Adopt a native scene into a Builder source without changing the live table.

Only faithfully representable objects become Builder-owned. Everything else
keeps its native identity and remains external to subsequent source updates.
"""

from copy import deepcopy
from io import BytesIO
import math
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from PIL import Image

from gravewright.campaigns.models import Campaign
from gravewright.journals.services import identifier
from . import builder_services as builder, objects, services, tiling
from .models import MapAsset, MapBuilderProject


EXTERNAL_CONTENT = "Only walls, doors and lights are imported as editable objects. Other scene content remains in the scene."
UNSUPPORTED_OBJECTS = "Scene objects that cannot be represented in Map Builder remain unchanged in the scene."


def read_background(scene):
    """Read the complete base raster, excluding all native overlays and secrets."""
    if scene.width * scene.height > min(builder.LIMITS["maxPixels"],
                                       builder.settings.GRAVEWRIGHT_MAP_MAX_PIXELS,
                                       builder.settings.GRAVEWRIGHT_MAP_PILLOW_MAX_PIXELS):
        raise services.MapError("The map exceeds the builder image pixel limit.")
    tiling._validate_size(scene.width, scene.height)
    expected = {(x, y) for y in range(math.ceil(scene.height / scene.tile_size))
                for x in range(math.ceil(scene.width / scene.tile_size))}
    tiles = list(scene.tiles.filter(lod=0))
    if {(tile.x, tile.y) for tile in tiles} != expected or len(tiles) != len(expected):
        raise services.MapError("The scene raster is incomplete.")
    with Image.new("RGBA", (scene.width, scene.height)) as canvas:
        for tile in tiles:
            left, top = tile.x * scene.tile_size, tile.y * scene.tile_size
            size = min(scene.tile_size, scene.width - left), min(scene.tile_size, scene.height - top)
            try:
                with tile.file.open("rb") as stream, Image.open(stream) as image:
                    if image.size != size or getattr(image, "n_frames", 1) != 1:
                        raise services.MapError("The scene raster is incomplete.")
                    with image.convert("RGBA") as piece:
                        canvas.paste(piece, (left, top))
            except (OSError, ValueError):
                raise services.MapError("Could not read the scene raster.") from None
        with BytesIO() as output:
            canvas.save(output, "PNG")
            return ContentFile(output.getvalue(), name="builder-background.png")


def _source_document(scene):
    options = services.settings({}, scene.settings)
    cell = min(builder.LIMITS["maxCellSize"], max(builder.LIMITS["minCellSize"], round(options["gridSize"]),
               math.ceil(scene.width / builder.LIMITS["maxColumns"]),
               math.ceil(scene.height / builder.LIMITS["maxRows"])))
    layer_id = str(uuid.uuid4())
    return {"schemaVersion": 3, "name": scene.name,
            "columns": math.ceil(scene.width / cell), "rows": math.ceil(scene.height / cell),
            "cellSize": cell, "background": "#253038", "assets": [],
            "layers": [{"id": layer_id, "name": "Imported objects", "visible": True, "locked": False}],
            "sceneGeometry": {"width": scene.width, "height": scene.height,
                              **{key: options[key] for key in ("gridSize", "gridOffsetX", "gridOffsetY", "imageScale")}},
            "floors": [], "walls": [], "doors": [], "decorations": [], "lights": []}


def _equivalent(left, right):
    """Compare the complete initial snapshot, tolerating numeric round trips."""
    if type(left) in (int, float) and type(right) in (int, float):
        return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-8)
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_equivalent(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_equivalent(a, b) for a, b in zip(left, right))
    return type(left) is type(right) and left == right


def _candidate(native, template, scene):
    """Validate one simple object using domain validators, without database IO.

    The whole document is validated once after collection. Per-object checks
    keep unsupported rows external without querying campaign assets or audio
    for every barrier, or copying the growing document for each candidate.
    """
    from .builder_sync import projection

    if not isinstance(native.data, dict) or any(key in native.data for key in
            ("blueprint", "sprite", "asset_id", "automationVariables", "automationMemory")):
        raise services.MapError(UNSUPPORTED_OBJECTS)
    data = objects.wall(native.data) if native.kind == "walls" else objects.light(native.data)
    kind = "doors" if native.kind == "walls" and data["kind"] == "door" else native.kind
    cell = template["cellSize"]
    # A rounded workspace can include a partial cell beyond the actual raster.
    # Such native objects remain external rather than becoming Builder-owned.
    coordinates = ("x1", "x2", "y1", "y2") if native.kind == "walls" else ("x", "y")
    for key in coordinates:
        builder.number(data[key], 0, scene.width if key.startswith("x") else scene.height, key)
    source = {"id": str(native.pk), "layerId": template["layers"][0]["id"],
              **projection(data, native.kind, cell, {})}
    builder.copy_name(source, source)
    if native.kind == "walls":
        source.update(assetId=None, thickness=.15, artwork=False)
        length = math.hypot(source["x2"] - source["x1"], source["y2"] - source["y1"])
        if kind == "doors":
            builder.number(length, builder.LIMITS["minDoorWidth"] - 1e-7,
                           builder.LIMITS["maxDoorWidth"] + 1e-7, "door width")
            # Adoption records the authored initial state, including channels
            # which ordinary synchronization treats as mutable gameplay state.
            source.update(state=data["door_state"], discovered=data["discovered"],
                          behavior={key: data[key + "_behavior"] for key in ("movement", "vision", "light", "sound")})
            if "rotationAnchor" not in data:
                source.pop("rotationAnchor", None)
            if "interactionEnabled" in data:
                source["interactionEnabled"] = data["interactionEnabled"]
        elif length < .1:
            raise services.MapError(UNSUPPORTED_OBJECTS)
        builder.clean_wall_properties(source, source)
    else:
        source["enabled"] = data["enabled"]
    candidate = {**template, **{name: [source] if name == kind else [] for name in ("walls", "doors", "lights")}}
    generated = builder.native_objects(candidate, scene)
    if len(generated) != 1 or not _equivalent(generated[0].data, native.data):
        raise services.MapError(UNSUPPORTED_OBJECTS)
    return kind, source


def create_project(scene, who, stored):
    """Called under the campaign lock; caller owns rollback of stored files."""
    existing = MapBuilderProject.objects.filter(campaign=who.campaign, scene=scene).first()
    if existing:
        return existing, existing.generation.get("importWarnings", [])
    doc = _source_document(scene)
    doc = builder.clean_document(doc, who)
    template = deepcopy(doc)
    rows = list(scene.elements.all()[:builder.LIMITS["maxNativeObjects"] + 1])
    if len(rows) > builder.LIMITS["maxNativeObjects"]:
        raise services.MapError("The scene has too many objects to import into Map Builder.")
    notes, adopted = [], {}
    for native in rows:
        if native.kind not in ("walls", "lights"):
            if EXTERNAL_CONTENT not in notes:
                notes.append(EXTERNAL_CONTENT)
            continue
        # Validate candidates separately so an unsupported object is retained,
        # rather than dropping it or preventing the rest of the map from opening.
        try:
            if len(adopted) >= builder.LIMITS["maxObjects"]:
                raise services.MapError(UNSUPPORTED_OBJECTS)
            kind, candidate = _candidate(native, template, scene)
            doc[kind].append(candidate)
            adopted[str(native.pk)] = native
        except (services.MapError, KeyError, TypeError, ValueError, OverflowError):
            if UNSUPPORTED_OBJECTS not in notes:
                notes.append(UNSUPPORTED_OBJECTS)

    # A native wall spanning a door must not be replaced by several owned spans.
    # Likewise, overlapping native doors cannot share Builder ownership.
    retained_doors = []
    for door in doc["doors"]:
        if any(builder.collinear_overlap(door, other) is not None for other in retained_doors):
            adopted.pop(door["id"])
            if UNSUPPORTED_OBJECTS not in notes:
                notes.append(UNSUPPORTED_OBJECTS)
        else:
            retained_doors.append(door)
    doc["doors"] = retained_doors
    walls = []
    for wall in doc["walls"]:
        if any(builder.collinear_overlap(wall, door) is not None for door in doc["doors"]):
            adopted.pop(wall["id"])
            if UNSUPPORTED_OBJECTS not in notes:
                notes.append(UNSUPPORTED_OBJECTS)
        else:
            walls.append(wall)
    doc["walls"] = walls

    content = read_background(scene)
    try:
        asset = MapAsset(campaign=who.campaign, name=scene.name + ".png", width=scene.width, height=scene.height)
        candidate_path = "maps/assets/" + uuid.uuid4().hex + ".png"
        # Track the intended name even when a storage write fails midway.
        if not default_storage.exists(candidate_path):
            stored.append(candidate_path)
        path = default_storage.save(candidate_path, content)
        if path != candidate_path:
            stored.append(path)
        asset.file = path
        asset.save()
    finally:
        content.close()
    doc["backgroundImage"] = {"assetId": str(asset.pk)}
    doc = builder.clean_document(doc, who)
    owned = builder.native_objects(doc, scene)
    for row in owned:
        key = row.builder_source_id.split(":", 1)[0]
        native = adopted[key]
        row.pk, row.data = native.pk, deepcopy(native.data)
    manifest = builder.generation_manifest(scene, doc, owned)
    if notes:
        manifest["importWarnings"] = notes
    source = MapBuilderProject.objects.create(campaign=who.campaign, folder=scene.folder, scene=scene,
        name=doc["name"], document=doc, generation=manifest)
    return source, notes


def adopt(campaign_id, user_id, scene_id, payload):
    """Create one linked project, with GM authority, revision checking and retries."""
    builder.fields(payload, ("request_id", "expected_scene_version"), "scene import command")
    scene_id, rid = identifier(scene_id), identifier(payload.get("request_id"))
    digest = builder.fingerprint("builder-adopt", scene_id, payload)
    stored = []
    try:
        with transaction.atomic():
            who = builder.authority(campaign_id, user_id)
            Campaign.objects.select_for_update().get(pk=who.campaign_id)
            who = builder.authority(campaign_id, user_id)
            cached = builder.replay(campaign_id, user_id, rid, digest)
            if cached is not None:
                return cached
            scene = services.scene(scene_id, who, write=True)
            if type(payload.get("expected_scene_version")) is not int or payload["expected_scene_version"] != scene.version:
                raise services.MapError("The scene changed. Reload the project before updating it.", "conflict")
            source, notes = create_project(scene, who, stored)
            result = {"project": builder.view(source, who), "scene": services.view(scene), "warnings": notes}
            builder.record(campaign_id, user_id, rid, digest, result)
            from gravewright.realtime.dispatch import changed
            changed(campaign_id, user_id, "maps", "builder-adopt", rid, {"map": result["scene"]})
        stored.clear()
        return result
    finally:
        for path in stored:
            default_storage.delete(path)
