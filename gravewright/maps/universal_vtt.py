"""Bounded Universal VTT 0.2/0.3 interchange and normalized scene geometry.

The producer's format is documented at https://arkenforge.com/universal-vtt-files/.
Coordinates are grid units; the embedded raster is PNG or WebP. Unsupported game
content is reported explicitly and is never serialized into extension fields.
"""

import base64
import binascii
from io import BytesIO
import hashlib
import json
import math
import re
import threading
import uuid
import warnings

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from PIL import Image, ImageChops

from gravewright.campaigns.models import Campaign
from gravewright.journals.services import identifier
from . import objects, services, tiling
from .models import MapAsset, Scene, SceneNavigation, SceneObject, SceneState, Tile

MAX_JSON_BYTES = 64 * 1024 * 1024
MAX_IMAGE_BYTES = 48 * 1024 * 1024
MAX_PIXELS = 16_777_216
MAX_POINTS = 20_000
MAX_OBJECTS = 5000
MAX_WORK_PIXELS = 134_217_728
SUPPORTED_FORMATS = (.2, .3)
PORTAL_TOLERANCE = .05  # Pixels, allowing rounded grid-coordinate exports.
_processing = threading.RLock()


def _invalid():
    raise services.MapError("Choose a valid Universal VTT 0.2 or 0.3 file.")


def _number(value, low=-1_000_000, high=1_000_000):
    if type(value) not in (int, float) or not low <= value <= high or not math.isfinite(value):
        _invalid()
    return value


def _boolean(value):
    if type(value) is not bool:
        _invalid()
    return value


def _point(value):
    if not isinstance(value, dict):
        _invalid()
    return {key: _number(value.get(key)) for key in ("x", "y")}


def _array(value, limit=MAX_OBJECTS):
    if not isinstance(value, list) or len(value) > limit:
        _invalid()
    return value


def _argb(value):
    if not isinstance(value, str) or not re.fullmatch(r"#?(?:[a-fA-F0-9]{6}|[a-fA-F0-9]{8})", value):
        _invalid()
    value = value.lstrip("#").lower()
    return "#" + value[-6:], int(value[:2], 16) / 255 if len(value) == 8 else 1


def _size(width, height):
    if min(width, height) < 1 or width * height > min(MAX_PIXELS, settings.GRAVEWRIGHT_MAP_MAX_PIXELS,
                                                     settings.GRAVEWRIGHT_MAP_PILLOW_MAX_PIXELS):
        raise services.MapError("This Universal VTT image exceeds the interchange pixel limit.")
    tiling._validate_size(width, height)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _invalid()
        result[key] = value
    return result


def _read(raw):
    if not isinstance(raw, bytes) or not raw or len(raw) > min(MAX_JSON_BYTES, settings.MAP_UPLOAD_MAX_BYTES):
        raise services.MapError("The Universal VTT file exceeds the interchange size limit.")
    try:
        result = json.loads(raw, object_pairs_hook=_pairs, parse_constant=lambda _: _invalid())
    except (ValueError, UnicodeError, RecursionError):
        _invalid()
    if (not isinstance(result, dict) or type(result.get("format")) not in (int, float)
            or result["format"] not in SUPPORTED_FORMATS):
        _invalid()
    return result


def _image(encoded, expected):
    if not isinstance(encoded, str) or len(encoded) > MAX_IMAGE_BYTES * 4 // 3 + 1024:
        _invalid()
    try:
        content = base64.b64decode(re.sub(r"[\r\n]", "", encoded), validate=True)
        if len(content) > MAX_IMAGE_BYTES:
            _invalid()
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as source:
                if source.format not in ("PNG", "WEBP") or getattr(source, "n_frames", 1) != 1:
                    _invalid()
                _size(*source.size)
                if source.size != expected:
                    raise services.MapError("The Universal VTT image does not match its resolution.")
                # Strip metadata; map geometry refers to encoded pixels, not EXIF transforms.
                with source.convert("RGBA") as image, BytesIO() as output:
                    image.save(output, "PNG")
                    return ContentFile(output.getvalue(), name="uvtt.png")
    except (OSError, ValueError, SyntaxError, binascii.Error, Image.DecompressionBombError, Image.DecompressionBombWarning):
        _invalid()


def _portal_walls(solids, doors):
    """Cut portal openings without depending on editable Builder geometry.

    Exporters round each point independently. A small distance tolerance in
    pixels accepts that rounding without cutting nearby parallel barriers.
    Door bounds remain authoritative; no rotation or position is applied twice.
    """
    if len(solids) * len(doors) > 2_000_000:
        raise services.MapError("The UVTT portal geometry exceeds the interchange complexity limit.")
    result = []

    def append(data):
        if len(result) >= MAX_OBJECTS:
            raise services.MapError("The UVTT portal geometry exceeds the interchange complexity limit.")
        result.append(("walls", data))

    for wall in solids:
        dx, dy = wall["x2"] - wall["x1"], wall["y2"] - wall["y1"]
        length = math.hypot(dx, dy)
        ux, uy = dx / length, dy / length
        intervals = []
        for door in doors:
            offsets = []
            for endpoint in ("1", "2"):
                x, y = door["x" + endpoint] - wall["x1"], door["y" + endpoint] - wall["y1"]
                if abs(x * uy - y * ux) > PORTAL_TOLERANCE:
                    break
                offsets.append(x * ux + y * uy)
            if len(offsets) == 2:
                start, end = max(0, min(offsets)), min(length, max(offsets))
                if end - start > .01:
                    intervals.append((start, end))

        def span(start, end):
            append({**wall, "x1": wall["x1"] + ux * start, "y1": wall["y1"] + uy * start,
                    "x2": wall["x1"] + ux * end, "y2": wall["y1"] + uy * end})

        cursor = 0
        for start, end in sorted(intervals):
            if start - cursor >= .01:
                span(cursor, start)
            cursor = max(cursor, end)
        if length - cursor >= .01:
            span(cursor, length)
    for door in doors:
        append(door)
    return result


def _source(document):
    """Keep only bounded producer labels, never arbitrary extension payloads."""
    result = {"format": document["format"], "coordinateSystem": "pixels"}
    for key in ("software", "creator"):
        value = document.get(key)
        if isinstance(value, str) and len(value) <= 200 and not any(ord(char) < 32 for char in value):
            result[key] = value.strip()
    return result


def parse(raw):
    """Normalize interchange to pixels before decoding the embedded image.

    The original grid origin determines both local object positions and the
    grid phase. Raster artwork stays flattened, while rows contain editable
    native barriers and lights for either scene or Builder integration.
    """
    document = _read(raw)
    resolution = document.get("resolution")
    if not isinstance(resolution, dict):
        _invalid()
    origin, dimensions = _point(resolution.get("map_origin")), _point(resolution.get("map_size"))
    cell = _number(resolution.get("pixels_per_grid"), 1, 10000)
    if cell != int(cell) or min(dimensions.values()) <= 0:
        _invalid()
    cell = int(cell)
    width, height = (round(dimensions[key] * cell) for key in ("x", "y"))
    _size(width, height)
    notes, rows, points = [], [], 0

    def local(point):
        value = _point(point)
        return {key: _number((value[key] - origin[key]) * cell) for key in ("x", "y")}

    for key in ("line_of_sight", "objects_line_of_sight"):
        for polyline in _array(document.get(key, [])):
            polyline = _array(polyline, MAX_POINTS)
            if len(polyline) < 2:
                _invalid()
            points += len(polyline)
            if points > MAX_POINTS:
                _invalid()
            vertices = [local(point) for point in polyline]
            for before, after in zip(vertices, vertices[1:]):
                if math.hypot(after["x"] - before["x"], after["y"] - before["y"]) < .01:
                    if "Degenerate UVTT wall segments were ignored." not in notes:
                        notes.append("Degenerate UVTT wall segments were ignored.")
                    continue
                rows.append(("walls", objects.wall({"x1": before["x"], "y1": before["y"], "x2": after["x"], "y2": after["y"]})))
                if len(rows) > MAX_OBJECTS:
                    _invalid()
    portals = _array(document.get("portals", []))
    for portal in portals:
        if not isinstance(portal, dict):
            _invalid()
        bounds = _array(portal.get("bounds"), 2)
        if len(bounds) != 2:
            _invalid()
        before, after = map(local, bounds)
        if "position" in portal:
            local(portal["position"])
        _number(portal.get("rotation", 0), -36000, 36000)
        _boolean(portal.get("freestanding", False))
        rows.append(("walls", objects.wall({"kind": "door", "x1": before["x"], "y1": before["y"],
                                            "x2": after["x"], "y2": after["y"],
                                            "door_state": "closed" if _boolean(portal.get("closed")) else "open"})))
    if len(rows) > MAX_OBJECTS:
        _invalid()
    if portals:
        notes.append("UVTT portals are imported as doors; window behavior may need adjustment.")
        solids = [data for _, data in rows if data["kind"] == "wall"]
        doors = [data for _, data in rows if data["kind"] == "door"]
        rows = _portal_walls(solids, doors)
    environment = document.get("environment", {})
    if not isinstance(environment, dict):
        _invalid()
    baked = _boolean(environment.get("baked_lighting", False))
    ambient, alpha = _argb(environment.get("ambient_light", "ffffffff"))
    channels = [int(ambient[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    darkness = 1 - (sum(channels) / 3) * alpha
    if len(set(channels)) > 1:
        notes.append("UVTT ambient color is approximated by scene darkness.")
    if baked:
        notes.append("The UVTT image already contains baked lighting; imported lights start disabled.")
    for light in _array(document.get("lights", [])):
        if not isinstance(light, dict):
            _invalid()
        position = local(light.get("position"))
        color, alpha = _argb(light.get("color", "ffffffff"))
        source_radius = _number(light.get("range"), 0)
        source_intensity = _number(light.get("intensity"), 0)
        radius = min(200, source_radius)
        for exceeded, warning in ((source_radius > 200, "UVTT light ranges above 200 cells are clamped."),
                                   (source_intensity > 1, "UVTT light intensities above 1 are clamped.")):
            if exceeded and warning not in notes:
                notes.append(warning)
        shadows = _boolean(light.get("shadows", True))
        if not shadows and "Per-light UVTT shadow settings are not supported." not in notes:
            notes.append("Per-light UVTT shadow settings are not supported.")
        rows.append(("lights", objects.light({**position, "bright_radius": 0, "dim_radius": radius,
                                               "color": color, "intensity": min(1, source_intensity) * alpha,
                                               "enabled": not baked and radius > 0})))
        if radius == 0 and "Zero-range UVTT lights start disabled." not in notes:
            notes.append("Zero-range UVTT lights start disabled.")
        if len(rows) > MAX_OBJECTS:
            _invalid()
    if len(rows) > MAX_OBJECTS:
        _invalid()
    if any(kind == "lights" for kind, _ in rows) and not settings.DYNAMIC_LIGHTING_ENABLED:
        raise services.MapError("Dynamic lighting is disabled.", "forbidden")
    grid = {"size": cell, **{"offset" + key.upper(): (-origin[key] * cell) % cell for key in ("x", "y")}}
    return {"width": width, "height": height, "cell": cell, "origin": origin, "rows": rows,
            "grid": grid, "source": _source(document),
            "baked": baked, "darkness": darkness, "warnings": notes,
            "image": _image(document.get("image"), (width, height))}


def import_map(campaign_id, user_id, raw, *, name, request_id, folder_id=None, activate=False, builder_editable=False):
    """Create a native scene once, cleaning every newly stored tile on failure."""
    from .builder_services import authority, fingerprint, record, replay
    who = authority(campaign_id, user_id)
    name, rid = services.title(name), identifier(request_id)
    if type(activate) is not bool or type(builder_editable) is not bool or not isinstance(raw, bytes):
        _invalid()
    if not raw or len(raw) > min(MAX_JSON_BYTES, settings.MAP_UPLOAD_MAX_BYTES):
        raise services.MapError("The Universal VTT file exceeds the interchange size limit.")
    target = services.folder(folder_id, who)
    digest = fingerprint("uvtt-import", campaign_id, {"content": hashlib.sha256(raw).hexdigest(), "name": name,
                                                       "folder": str(target.pk) if target else None, "activate": activate,
                                                       **({"builderEditable": True} if builder_editable else {})})
    cached = replay(campaign_id, user_id, rid, digest)
    if cached is not None:
        return cached
    stored, tiles = [], []
    try:
        with _processing:
            parsed = parse(raw)
            try:
                def save_tile(lod, x, y, content):
                    candidate = "maps/tiles/" + uuid.uuid4().hex + ".webp"
                    existed = default_storage.exists(candidate)
                    try:
                        path = default_storage.save(candidate, content)
                    except Exception:
                        if not existed:
                            default_storage.delete(candidate)
                        raise
                    stored.append(path)
                    tiles.append(Tile(lod=lod, x=x, y=y, file=path, byte_size=content.size))
                width, height, max_lod = tiling.generate_pyramid(parsed["image"], save_tile)
            finally:
                parsed["image"].close()
        with transaction.atomic():
            Campaign.objects.select_for_update().get(pk=campaign_id)
            who = authority(campaign_id, user_id)
            cached = replay(campaign_id, user_id, rid, digest)
            if cached is not None:
                return cached
            target = services.folder(folder_id, who)
            cell = parsed["cell"]
            options = services.settings({"gridSize": cell, "gridOffsetX": (-parsed["origin"]["x"] * cell) % cell,
                                         "gridOffsetY": (-parsed["origin"]["y"] * cell) % cell})
            options["uvttBakedLighting"] = parsed["baked"]
            scene = Scene.objects.create(campaign=who.campaign, folder=target, name=name, visibility="players" if activate else "gm",
                                         width=width, height=height, tile_size=tiling.TILE_SIZE, max_lod=max_lod, settings=options)
            for tile in tiles:
                tile.scene = scene
            Tile.objects.bulk_create(tiles)
            SceneObject.objects.bulk_create([SceneObject(scene=scene, kind=kind, data=data) for kind, data in parsed["rows"]])
            SceneState.objects.create(scene=scene, lighting={"mode": "none" if parsed["baked"] else "dynamic" if any(kind == "lights" for kind, _ in parsed["rows"]) else "manual",
                                                           "darkness": parsed["darkness"], "lights_out": not parsed["baked"]})
            if activate:
                from .audience import broadcast
                broadcast(who, scene)
            SceneNavigation.objects.update_or_create(membership=who, defaults={"scene": None if activate else scene})
            response = {"scene": services.view(scene), "warnings": parsed["warnings"], "builderEditable": False}
            if builder_editable:
                from .builder_import import create_project
                from .builder_services import view
                source, notes = create_project(scene, who, stored)
                if parsed["warnings"] or notes:
                    source.generation["importWarnings"] = [*parsed["warnings"], *notes]
                    source.save(update_fields=["generation"])
                response.update(project=view(source, who), builderEditable=True,
                                warnings=[*parsed["warnings"], *notes])
            record(campaign_id, user_id, rid, digest, response)
            from gravewright.realtime.dispatch import changed
            changed(campaign_id, user_id, "maps", "uvtt-import", rid, {"map": response["scene"]})
        stored.clear()
        return response
    finally:
        for path in stored:
            default_storage.delete(path)


class _Budget:
    def __init__(self):
        self.pixels = 0

    def use(self, width, height):
        self.pixels += width * height
        if width * height > MAX_PIXELS or self.pixels > MAX_WORK_PIXELS:
            raise services.MapError("The scene exceeds the Universal VTT composition limit.")


def _bounds(data, width, height):
    x, y = _number(data["x"]), _number(data["y"])
    # Fitted state/sprite artwork can exceed the ordinary image editor's scale
    # range. Composition still allocates only its clipped scene intersection.
    scale = _number(data["scale"], 0)
    if scale == 0:
        _invalid()
    w, h = _number(data["natural_width"], .001) * scale, _number(data["natural_height"], .001) * scale
    angle = math.radians(_number(data.get("rotation", 0), -36000, 36000))
    c, s = abs(math.cos(angle)), abs(math.sin(angle))
    left, top = max(0, math.floor(x - (c * w + s * h) / 2)), max(0, math.floor(y - (s * w + c * h) / 2))
    right, bottom = min(width, math.ceil(x + (c * w + s * h) / 2)), min(height, math.ceil(y + (s * w + c * h) / 2))
    return (left, top, right, bottom) if right > left and bottom > top else None


def _place(canvas, image, data, budget, *, origin=(0, 0), erase=False):
    global_box = _bounds(data, canvas.width + origin[0], canvas.height + origin[1])
    if global_box is None:
        return
    left, top = max(origin[0], global_box[0]), max(origin[1], global_box[1])
    right, bottom = min(origin[0] + canvas.width, global_box[2]), min(origin[1] + canvas.height, global_box[3])
    if right <= left or bottom <= top:
        return
    budget.use(right - left, bottom - top)
    c, s = math.cos(math.radians(data.get("rotation", 0))), math.sin(math.radians(data.get("rotation", 0)))
    sx, sy = image.width / (data["natural_width"] * data["scale"]), image.height / (data["natural_height"] * data["scale"])
    dx, dy = left - data["x"], top - data["y"]
    affine = (c * sx, s * sx, (c * dx + s * dy) * sx + image.width / 2,
              -s * sy, c * sy, (-s * dx + c * dy) * sy + image.height / 2)
    with image.transform((right - left, bottom - top), Image.Transform.AFFINE, affine, Image.Resampling.BICUBIC) as patch:
        position = left - origin[0], top - origin[1]
        if not erase:
            canvas.alpha_composite(patch, position)
        else:
            box = (*position, position[0] + patch.width, position[1] + patch.height)
            with canvas.crop(box) as previous, previous.getchannel("A") as alpha, patch.getchannel("A") as removal:
                with ImageChops.invert(removal) as keep, ImageChops.multiply(alpha, keep) as faded:
                    previous.putalpha(faded)
                canvas.paste(previous, position)


def _load_asset(asset, scene, budget):
    if asset is None or asset.generated_for_id not in (None, scene.pk):
        raise services.MapError("A scene image is missing or belongs to another scene.")
    try:
        with asset.file.open("rb") as stream, Image.open(stream) as image:
            if image.width * image.height > 40_000_000:
                raise services.MapError("A map asset exceeds the image pixel limit.")
            budget.pixels += image.width * image.height
            if budget.pixels > MAX_WORK_PIXELS:
                raise services.MapError("The scene exceeds the Universal VTT composition limit.")
            return image.convert("RGBA")
    except (OSError, ValueError, Image.DecompressionBombError):
        raise services.MapError("Could not read artwork for Universal VTT export.") from None


def _wall_pattern(surface, material, size, budget):
    from .builder_render import _wall_strip
    crop = surface.get("materialCrop", [0, 0, material.width, material.height])
    image = material.crop(crop)
    result = Image.new("RGBA", size)
    try:
        thickness = surface["thickness"]
        if thickness < 1:
            smaller = image.resize((image.width, 1), Image.Resampling.BOX); image.close(); image = smaller; thickness = 1
        ux, uy = surface["direction"]
        ox, oy = surface["origin"]
        # Small affine blocks avoid an enormous rotated repeat canvas or tile.
        for top in range(0, size[1], 256):
            for left in range(0, size[0], 256):
                w, h = min(256, size[0] - left), min(256, size[1] - top)
                gx, gy = surface["left"] + left - ox, surface["top"] + top - oy
                ts = [ux * (gx + x) + uy * (gy + y) + surface["phase"] for x, y in ((0, 0), (w, 0), (0, h), (w, h))]
                vs = [-uy * (gx + x) + ux * (gy + y) + thickness / 2 for x, y in ((0, 0), (w, 0), (0, h), (w, h))]
                t0, v0 = math.floor(min(ts)), math.floor(min(vs))
                length, height = max(1, math.ceil(max(ts)) - t0), max(1, math.ceil(max(vs)) - v0)
                budget.use(length, height)
                with _wall_strip(image, length, thickness, t0) as strip, Image.new("RGBA", (length, height)) as repeated:
                    for repeat in range(math.floor(v0 / thickness), math.ceil((v0 + height) / thickness)):
                        start, end = max(0, math.floor(repeat * thickness - v0)), min(height, math.ceil((repeat + 1) * thickness - v0))
                        if end <= start:
                            continue
                        with strip.transform((length, end - start), Image.Transform.AFFINE,
                                             (1, 0, 0, 0, 1, start + v0 - repeat * thickness), Image.Resampling.BICUBIC) as piece:
                            repeated.alpha_composite(piece, (0, start))
                    with repeated.transform((w, h), Image.Transform.AFFINE,
                                            (ux, uy, ts[0] - t0, -uy, ux, vs[0] - v0), Image.Resampling.BICUBIC) as patch:
                        result.paste(patch, (left, top))
        return result
    except Exception:
        result.close()
        raise
    finally:
        image.close()


def _bitmap(data, assets, scene, budget):
    surface = data.get("surface")
    if not surface or not surface.get("materialId"):
        return _load_asset(assets.get(data.get("asset_id")), scene, budget)
    material_asset, mask_asset = assets.get(surface["materialId"]), assets.get(surface["maskId"])
    if material_asset is None or material_asset.generated_for_id is not None or mask_asset is None or mask_asset.generated_for_id != scene.pk:
        raise services.MapError("A scene image is missing or belongs to another scene.")
    with _load_asset(mask_asset, scene, budget) as mask, _load_asset(material_asset, scene, budget) as material:
        budget.use(*mask.size)
        if surface["kind"] == "wall":
            result = _wall_pattern(surface, material, mask.size, budget)
        else:
            cell = surface["cellSize"]
            with material.resize((cell, cell), Image.Resampling.LANCZOS) as tile:
                rotated = tile.rotate(-surface["rotation"])
            try:
                result = Image.new("RGBA", mask.size)
                for y in range(-(surface["top"] % cell), mask.height, cell):
                    for x in range(-(surface["left"] % cell), mask.width, cell):
                        result.paste(rotated, (x, y))
            finally:
                rotated.close()
        with result.getchannel("A") as alpha, mask.getchannel("A") as coverage, ImageChops.multiply(alpha, coverage) as combined:
            result.putalpha(combined)
        return result


def _raster(scene, rows, notes):
    _size(scene.width, scene.height)
    budget = _Budget(); budget.use(scene.width, scene.height)
    canvas = Image.new("RGBA", (scene.width, scene.height))
    try:
        tiles = list(scene.tiles.filter(lod=0))
        expected = math.ceil(scene.width / scene.tile_size) * math.ceil(scene.height / scene.tile_size)
        if len(tiles) != expected:
            raise services.MapError("The scene raster is incomplete.")
        for tile in tiles:
            left, top = tile.x * scene.tile_size, tile.y * scene.tile_size
            size = (min(scene.tile_size, scene.width - left), min(scene.tile_size, scene.height - top))
            try:
                with tile.file.open("rb") as stream, Image.open(stream) as image:
                    if image.size != size:
                        raise services.MapError("The scene raster is incomplete.")
                    with image.convert("RGBA") as piece:
                        canvas.paste(piece, (left, top))
            except (OSError, ValueError):
                raise services.MapError("Could not read the scene raster.") from None
        images = [row.data for row in rows if row.kind == "images" and row.data.get("empty") is not True]
        doors = [row.data for row in rows if row.kind == "walls" and row.data.get("kind") == "door"]
        from .blueprint_runtime import appearance
        doors = [(data, appearance(data)) for data in doors]
        asset_ids = {value for data in images for value in [data.get("asset_id"), data.get("surface", {}).get("maskId"), data.get("surface", {}).get("materialId")] if value}
        asset_ids.update(config["assetId"] for _, config in doors if config["visible"] and config["assetId"])
        assets = {str(asset.pk): asset for asset in MapAsset.objects.filter(campaign=scene.campaign, pk__in=asset_ids)}
        grouped, jobs = {}, []
        for data in images:
            if data.get("layer") in ("gm", "gm-image-layer"):
                if "Hidden GM artwork is omitted from UVTT export." not in notes:
                    notes.append("Hidden GM artwork is omitted from UVTT export.")
                continue
            group = data.get("surfacePlane", {}).get("group")
            if group:
                grouped.setdefault(group, []).append(data)
            else:
                jobs.append((data.get("z_index", 0), [data], False))
        if len(grouped) > 32:
            raise services.MapError("The scene exceeds the Universal VTT composition limit.")
        jobs.extend((min(data.get("z_index", 0) for data in values), values, True) for values in grouped.values())
        for _, placements, grouped_job in sorted(jobs, key=lambda job: job[0]):
            if not grouped_job:
                with _bitmap(placements[0], assets, scene, budget) as image:
                    _place(canvas, image, placements[0], budget)
                continue
            bounds = [_bounds(data, scene.width, scene.height) for data in placements]
            bounds = [box for box in bounds if box]
            if not bounds:
                continue
            left, top = min(box[0] for box in bounds), min(box[1] for box in bounds)
            right, bottom = max(box[2] for box in bounds), max(box[3] for box in bounds)
            budget.use(right - left, bottom - top)
            with Image.new("RGBA", (right - left, bottom - top)) as group:
                for data in sorted(placements, key=lambda data: data["surfacePlane"]["order"]):
                    with _bitmap(data, assets, scene, budget) as image:
                        _place(group, image, data, budget, origin=(left, top), erase=data["surfacePlane"]["operation"] == "erase")
                canvas.alpha_composite(group, (left, top))
        for data, config in doors:
            if not config["visible"] or not config["assetId"]:
                continue
            if data.get("presentation") in ("secret", "invisible") and not data.get("discovered"):
                continue
            with _load_asset(assets.get(config["assetId"]), scene, budget) as image:
                dx, dy = data["x2"] - data["x1"], data["y2"] - data["y1"]
                placement = {"x": (data["x1"] + data["x2"]) / 2, "y": (data["y1"] + data["y2"]) / 2,
                             "natural_width": math.hypot(dx, dy), "natural_height": data.get("thickness", 14),
                             "scale": 1, "rotation": math.degrees(math.atan2(dy, dx))}
                if data.get("door_state") == "open" and data.get("rotationAnchor") in ("start", "center", "end"):
                    offset = {"start": 0, "center": .5, "end": 1}[data["rotationAnchor"]]
                    pivot_x, pivot_y = data["x1"] + dx * offset, data["y1"] + dy * offset
                    # Match the native clockwise quarter turn around the pivot.
                    placement["x"], placement["y"] = (pivot_x - (placement["y"] - pivot_y),
                                                       pivot_y + (placement["x"] - pivot_x))
                    placement["rotation"] += 90
                _place(canvas, image, placement, budget)
        return canvas
    except Exception:
        canvas.close()
        raise


def export_map(campaign_id, user_id, scene_id):
    """Flatten current public artwork and portable native geometry without writes."""
    from .builder_services import authority
    who = authority(campaign_id, user_id)
    with transaction.atomic(), _processing:
        Campaign.objects.select_for_update().get(pk=campaign_id)
        who = authority(campaign_id, user_id)
        scene = services.scene(scene_id, who)
        rows = list(scene.elements.all())
        if len(rows) > MAX_OBJECTS:
            _invalid()
        notes = []
        if any(data.data.get("blueprint") for data in rows):
            notes.append("UVTT does not include behaviors, variables, timers or scene automation.")
        if scene.tokens.exists() or any(row.kind in ("cards", "markers", "journalPins", "zones") for row in rows):
            notes.append("UVTT does not include tokens, regions, cards, markers or journal permissions.")
        env = SceneState.objects.filter(scene=scene).first()
        if any(row.kind in ("particles", "shaders", "spatialSounds") for row in rows) or scene.soundscape_id:
            notes.append("UVTT does not include particles, shaders or audio.")
        if env and (env.fog or env.drawings):
            notes.append("UVTT does not include fog or scene drawings.")
        if any(row.kind == "images" for row in rows):
            notes.append("UVTT flattens scene images and dynamic surfaces into one raster.")
        cell = scene.settings.get("gridSize", services.DEFAULTS["gridSize"]) * scene.settings.get("imageScale", 1)
        _number(cell, 1, 10000)
        ppg = round(cell)
        offset = {key: scene.settings.get("gridOffset" + key.upper(), 0) * scene.settings.get("imageScale", 1) for key in ("x", "y")}
        origin = {key: -offset[key] / cell for key in ("x", "y")}

        def point(x, y):
            return {key: (value - offset[key]) / cell for key, value in (("x", x), ("y", y))}

        walls, portals, lights = [], [], []
        for row in rows:
            data = row.data
            if row.kind == "walls":
                bounds = [point(data["x1"], data["y1"]), point(data["x2"], data["y2"])]
                if data.get("kind") == "door":
                    portals.append({"position": point((data["x1"] + data["x2"]) / 2, (data["y1"] + data["y2"]) / 2),
                                    "bounds": bounds, "rotation": math.atan2(data["y2"] - data["y1"], data["x2"] - data["x1"]),
                                    "closed": data.get("door_state") != "open", "freestanding": False})
                elif any(data.get(key + "_behavior", "block") != "pass" for key in ("movement", "vision", "light")):
                    walls.append(bounds)
                if (data.get("door_state") == "locked" or data.get("presentation", "normal") != "normal"
                        or len({data.get(key + "_behavior", "block") for key in ("movement", "vision", "light", "sound")}) > 1
                        or data.get("vertical_bottom") is not None):
                    if "UVTT does not preserve locks, secret doors, height or separate barrier channels." not in notes:
                        notes.append("UVTT does not preserve locks, secret doors, height or separate barrier channels.")
            if row.kind == "lights" and data.get("enabled", True):
                lights.append({"position": point(data["x"], data["y"]), "range": data["dim_radius"],
                               "intensity": data["intensity"], "color": "ff" + data["color"].lstrip("#"), "shadows": True})
                if data.get("angle", 360) != 360 or data.get("animation", "none") != "none" or data.get("elevation", 0) or data["dim_radius"] == 0:
                    if "UVTT approximates light cones, animations, elevation and unlimited ranges." not in notes:
                        notes.append("UVTT approximates light cones, animations, elevation and unlimited ranges.")
                if data["dim_radius"] == 0:
                    lights[-1]["range"] = min(200, math.hypot(scene.width, scene.height) / cell * 2)
        with _raster(scene, rows, notes) as raster:
            if ppg != cell:
                notes.append("UVTT grid size was rounded to whole pixels.")
                width, height = round(scene.width * ppg / cell), round(scene.height * ppg / cell)
                _size(width, height)
                image = raster.resize((width, height), Image.Resampling.LANCZOS)
            else:
                image = raster
            try:
                with BytesIO() as output:
                    image.save(output, "PNG")
                    if output.tell() > MAX_IMAGE_BYTES:
                        raise services.MapError("The Universal VTT file exceeds the interchange size limit.")
                    encoded = base64.b64encode(output.getvalue()).decode("ascii")
                lighting = env.lighting if env else {}
                ambient = round(255 * (1 - lighting.get("darkness", 1))) if lighting.get("mode", "none") != "none" and lighting.get("lights_out", True) else 255
                document = {"format": .2, "resolution": {"map_origin": origin, "map_size": {"x": image.width / ppg, "y": image.height / ppg}, "pixels_per_grid": ppg},
                            "line_of_sight": walls, "objects_line_of_sight": [], "portals": portals,
                            "environment": {"baked_lighting": scene.settings.get("uvttBakedLighting", False), "ambient_light": f"ff{ambient:02x}{ambient:02x}{ambient:02x}"},
                            "lights": lights, "image": encoded}
                metadata = json.dumps({**document, "image": ""}, separators=(",", ":"), allow_nan=False)
                if len(metadata.encode()) + len(encoded) > MAX_JSON_BYTES:
                    raise services.MapError("The Universal VTT file exceeds the interchange size limit.")
            finally:
                if image is not raster:
                    image.close()
        filename = re.sub(r"[^\w .-]", "_", scene.name).strip(" .") or "map"
        return {"filename": filename + ".uvtt", "document": document, "warnings": notes}
