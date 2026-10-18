"""Bounded transparent surface planes and their atomic visual runtime state."""

from copy import deepcopy
import math
import uuid

from django.core.files.storage import default_storage
from PIL import Image

from .models import MapAsset
from .services import MapError


MAX_SURFACES = 64
MAX_PLANE_PIXELS = 67_108_864
MAX_ERASE_WORK = 134_217_728
MAX_PLANE_BYTES = 134_217_728


def _box(doc, rows, frames=None):
    cell = doc["cellSize"]
    points = []
    for row in rows:
        if frames is None:
            points.extend(((row["x"] * cell, row["y"] * cell),
                           ((row["x"] + row["width"]) * cell, (row["y"] + row["height"]) * cell)))
        elif row["id"] in frames:
            frame = frames[row["id"]]
            ox, oy = frame["origin"]
            ux, uy = frame["direction"]
            points.extend(((ox + x * ux - y * uy) * cell, (oy + x * uy + y * ux) * cell)
                          for ring in frame["polygons"] for x, y in ring)
    if not points:
        return None
    left = max(0, math.floor(min(x for x, _ in points)))
    top = max(0, math.floor(min(y for _, y in points)))
    right = min(doc["columns"] * cell, math.ceil(max(x for x, _ in points)))
    bottom = min(doc["rows"] * cell, math.ceil(max(y for _, y in points)))
    return (left, top, right, bottom) if right > left and bottom > top else None


def plan(doc):
    """Split static runs around promoted sources, retaining their exact order."""
    promoted = [row for kind in ("floors", "walls") for row in doc[kind] if row.get("dynamic") is True]
    if not promoted:
        return []
    if len(promoted) > MAX_SURFACES:
        raise MapError("The map has too many dynamic surfaces.")
    from .builder_services import segments
    from .wall_joins import wall_join_geometry
    frames = wall_join_geometry(doc, [span for span in segments(doc) if not span["door"]])
    floors_live = any(row.get("dynamic") is True for row in doc["floors"])
    planes, pixels, erase_work = [], 0, 0
    layers = doc.get("layers") or [{"id": None}]
    first = layers[0]["id"]
    for kind in ("floors", "walls"):
        if kind == "floors" and not floors_live:
            continue
        for layer in layers:
            rows = [row for row in doc[kind] if row.get("layerId", first) == layer["id"]]
            pending = []
            if kind == "floors" and (group_bounds := _box(doc, rows)):
                pixels += (group_bounds[2] - group_bounds[0]) * (group_bounds[3] - group_bounds[1])

            def append(group, dynamic=False, operation="paint"):
                nonlocal pixels, erase_work
                bounds = _box(doc, group, frames if kind == "walls" else None)
                if bounds is None:
                    return
                area = (bounds[2] - bounds[0]) * (bounds[3] - bounds[1])
                pixels += area * (2 if dynamic else 1)
                if operation == "erase":
                    erase_work += area
                if pixels > MAX_PLANE_PIXELS or erase_work > MAX_ERASE_WORK:
                    raise MapError("The map dynamic surfaces are too complex.")
                source_id = group[0]["id"] if dynamic else f'plane:{kind}:{layer["id"]}:{group[0]["id"]}'
                selection = {kind: [row["id"] for row in group]}
                value = {"sourceId": source_id, "kind": kind, "bounds": bounds,
                         "selection": selection, "dynamic": dynamic, "operation": operation}
                if kind == "floors":
                    value["group"] = layer["id"]
                if dynamic:
                    source = group[0]
                    surface = {"kind": "floor" if kind == "floors" else "wall", "cellSize": doc["cellSize"],
                               "left": bounds[0], "top": bounds[1]}
                    if kind == "floors":
                        surface["rotation"] = source.get("rotation", 0)
                    else:
                        frame = frames[source["id"]]
                        surface.update(origin=[value * doc["cellSize"] for value in frame["origin"]],
                                       direction=list(frame["direction"]), phase=frame["phase"] * doc["cellSize"],
                                       thickness=source["thickness"] * doc["cellSize"])
                    value["surface"] = surface
                planes.append(value)

            for row in rows:
                if row.get("brush", {}).get("operation") == "erase":
                    if pending:
                        append(pending)
                        pending = []
                    append([row], operation="erase")
                    continue
                if row.get("dynamic") is True:
                    if pending:
                        append(pending)
                        pending = []
                    append([row], True)
                else:
                    pending.append(row)
            if pending:
                append(pending)
    return planes


def baked_document(doc):
    if not any(row.get("dynamic") is True for kind in ("floors", "walls") for row in doc[kind]):
        return doc
    result = {**doc, "walls": []}
    if any(row.get("dynamic") is True for row in doc["floors"]):
        result["floors"] = []
    return result


def _store(content, stored):
    candidate = "maps/generated/" + uuid.uuid4().hex + ".png"
    existed = default_storage.exists(candidate)
    try:
        path = default_storage.save(candidate, content)
    except Exception:
        if not existed:
            default_storage.delete(candidate)
        raise
    stored.append(path)
    return path


def prepare(doc, campaign_id, stored=None):
    """Render before entering a campaign write transaction; keep bytes bounded."""
    from .builder_render import render
    planes, total = plan(doc), 0
    for plane in planes:
        source = doc
        if plane["operation"] == "erase":
            source = deepcopy(doc)
            for row in source["floors"]:
                if row["id"] in plane["selection"]["floors"]:
                    row["brush"]["operation"] = "paint"
            plane["content"] = render(source, campaign_id, selection=plane["selection"], crop=plane["bounds"], mask=True)
        else:
            plane["content"] = render(source, campaign_id, selection=plane["selection"], crop=plane["bounds"])
        total += plane["content"].size
        if plane["dynamic"]:
            plane["mask"] = render(doc, campaign_id, selection=plane["selection"], crop=plane["bounds"], mask=True)
            total += plane["mask"].size
        if total > MAX_PLANE_BYTES:
            raise MapError("The map dynamic surfaces are too complex.")
        if stored is not None:
            for key in ("content", "mask"):
                if key in plane:
                    content = plane.pop(key)
                    try:
                        plane[key + "Path"] = _store(content, stored)
                    finally:
                        content.close()
    return planes


def native_planes(doc, scene, planes, stored):
    """Persist generated assets alongside their scene; the caller owns rollback."""
    from .models import SceneObject
    from .element_names import copy_name

    sources = {row["id"]: row for kind in ("floors", "walls") for row in doc[kind]}

    def asset(plane, key, name):
        bounds = plane["bounds"]
        path = plane.get(key + "Path") or _store(plane[key], stored)
        return MapAsset.objects.create(campaign_id=scene.campaign_id, generated_for=scene, name=name,
                                       file=path, width=bounds[2] - bounds[0], height=bounds[3] - bounds[1])

    result = []
    for index, plane in enumerate(planes):
        bounds = plane["bounds"]
        artwork = asset(plane, "content", "Generated map surface")
        data = {"asset_id": str(artwork.pk), "scene_id": str(scene.pk), "src": f"/game/map-assets/{artwork.pk}",
                "natural_width": artwork.width, "natural_height": artwork.height,
                "x": (bounds[0] + bounds[2]) / 2, "y": (bounds[1] + bounds[3]) / 2,
                "scale": 1, "rotation": 0, "layer": "map", "z_index": -9000 + index}
        data["surfacePlane"] = {"group": (str(uuid.uuid5(scene.pk, f'surface-group:{plane["group"]}'))
                                           if plane["kind"] == "floors" else None),
                                "order": index, "operation": plane["operation"]}
        if plane["dynamic"]:
            mask = asset(plane, "mask", "Generated map surface mask")
            data["surface"] = {**plane["surface"], "maskId": str(mask.pk)}
            copy_name(data, sources[plane["sourceId"]])
        row = SceneObject(id=uuid.uuid5(scene.pk, plane["sourceId"]), scene=scene, kind="images", data=data)
        row.builder_source_id = plane["sourceId"]
        result.append(row)
    return result


def set_visibility(scene, row, visible):
    if row.kind != "images" or not isinstance(row.data.get("surface"), dict):
        return False
    if type(visible) is not bool:
        raise MapError("Invalid surface visibility.")
    row.data["layer"] = "map" if visible else "gm-image-layer"
    return True


def set_appearance(scene, row, asset_id):
    if row.kind != "images" or not isinstance(row.data.get("surface"), dict):
        return False
    asset = MapAsset.objects.filter(pk=asset_id, campaign_id=scene.campaign_id, generated_for__isnull=True).first()
    if asset is None:
        raise MapError("Choose an image from this campaign.")
    surface = deepcopy(row.data["surface"])
    surface["materialId"] = str(asset.pk)
    if surface["kind"] == "wall":
        from .blueprint_world import material_crop
        def load_crop():
            with asset.file.open("rb") as stream, Image.open(stream) as image:
                if image.width * image.height > 40_000_000:
                    raise MapError("A map asset exceeds the image pixel limit.")
                with image.convert("RGBA") as rgba, rgba.getchannel("A") as alpha:
                    with alpha.point(lambda value: 255 if value >= 8 else 0) as visible:
                        return list(visible.getbbox() or (0, 0, image.width, image.height))
        try:
            surface["materialCrop"] = material_crop(asset.pk, load_crop)
        except (OSError, ValueError) as error:
            raise MapError(f"Unable to read map asset: {asset.name}.") from error
    row.data["surface"] = surface
    return True


def prune_generated(scene):
    """Remove superseded owned artifacts only after their scene update commits."""
    from .models import SceneObject
    using = set()
    for data in SceneObject.objects.filter(scene__campaign_id=scene.campaign_id, kind="images").values_list("data", flat=True):
        using.add(data.get("asset_id"))
        using.add(data.get("surface", {}).get("maskId"))
    for asset in MapAsset.objects.filter(generated_for=scene).exclude(pk__in=[value for value in using if value]):
        asset.delete()
