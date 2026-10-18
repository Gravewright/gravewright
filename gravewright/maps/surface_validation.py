"""Validate imported managed surfaces after all scene and asset IDs are remapped.

Ordinary legacy images keep their existing archive contract. Only the new
managed-artwork fields and their private Builder recipes are inspected here.
PNG headers are checked before allocation; validation never rasterizes a map.
"""

from collections import defaultdict
import math
from types import SimpleNamespace
from uuid import UUID
import warnings

from PIL import Image

from .models import MapAsset, MapBuilderProject, SceneObject
from .services import MapError


MAX_BITMAP_PIXELS = 16_777_216
MAX_SCENE_PIXELS = 67_108_864
MAX_GENERATED_BYTES = 134_217_728
MAX_PLANES = 5000
MAX_DYNAMIC = 64
MAX_GROUPS = 32


def _invalid():
    raise MapError("Invalid imported map surface.")


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        _invalid()


def _number(value, low=-1_000_000, high=1_000_000, *, integer=False):
    if type(value) not in ((int,) if integer else (int, float)) or not low <= value <= high or not math.isfinite(value):
        _invalid()
    return value


def _uuid(value):
    if not isinstance(value, str):
        _invalid()
    try:
        canonical = str(UUID(value))
    except (ValueError, AttributeError):
        _invalid()
    if value != canonical:
        _invalid()
    return canonical


def _dimensions(asset, *, material=False):
    limit = 40_000_000 if material else MAX_BITMAP_PIXELS
    width = _number(asset.width, 1, limit, integer=True)
    height = _number(asset.height, 1, limit, integer=True)
    if width * height > limit:
        _invalid()
    return width, height


def _inspect(asset, cache, *, material=False):
    if asset.pk in cache:
        return cache[asset.pk]
    dimensions = _dimensions(asset, material=material)
    try:
        size = asset.file.size
        if not material and size > MAX_GENERATED_BYTES:
            _invalid()
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with asset.file.open("rb") as source, Image.open(source) as image:
                if image.size != dimensions or not material and image.format != "PNG":
                    _invalid()
                image.verify()
    except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        _invalid()
    cache[asset.pk] = (*dimensions, size)
    return cache[asset.pk]


def _group_area(rows, scene):
    left, top, right, bottom = math.inf, math.inf, -math.inf, -math.inf
    for data in rows:
        half_width = data["natural_width"] * data["scale"] / 2
        half_height = data["natural_height"] * data["scale"] / 2
        angle = math.radians(data["rotation"])
        cosine, sine = math.cos(angle), math.sin(angle)
        for x, y in ((-half_width, -half_height), (half_width, -half_height), (half_width, half_height), (-half_width, half_height)):
            px, py = data["x"] + x * cosine - y * sine, data["y"] + x * sine + y * cosine
            left, top, right, bottom = min(left, px), min(top, py), max(right, px), max(bottom, py)
    left, top = max(0, math.floor(left)), max(0, math.floor(top))
    right, bottom = min(scene.width, math.ceil(right)), min(scene.height, math.ceil(bottom))
    area = max(0, right - left) * max(0, bottom - top)
    if area > MAX_BITMAP_PIXELS:
        _invalid()
    return area


def _has_dynamic(document):
    if not isinstance(document, dict):
        return False
    return any(isinstance(row, dict) and "dynamic" in row for kind in ("floors", "walls")
               for row in (document[kind] if isinstance(document.get(kind), list) else []))


def _recipes(campaign):
    from .builder_services import clean_document
    context = SimpleNamespace(campaign=campaign, campaign_id=campaign.pk)
    for project in MapBuilderProject.objects.filter(campaign=campaign).iterator():
        generation = project.generation if isinstance(project.generation, dict) else {}
        baseline = generation.get("dynamicDocument")
        if "dynamicDocument" in generation:
            clean_document(baseline, context)
        if baseline is not None or _has_dynamic(project.document):
            clean_document(project.document, context)


def validate_campaign_surfaces(campaign):
    """Reject malformed managed markers without mutating any imported content."""
    assets = {str(row.pk): row for row in MapAsset.objects.filter(campaign=campaign).select_related("generated_for")}
    cache, generated_bytes = {}, defaultdict(int)
    for asset in assets.values():
        if asset.generated_for_id is None:
            continue
        if asset.generated_for.campaign_id != campaign.pk:
            _invalid()
        _, _, size = _inspect(asset, cache)
        generated_bytes[asset.generated_for_id] += size
        if generated_bytes[asset.generated_for_id] > MAX_GENERATED_BYTES:
            _invalid()
    scenes, totals, dynamics, groups, orders, counts = {}, defaultdict(int), defaultdict(int), defaultdict(dict), defaultdict(set), defaultdict(int)
    for row in SceneObject.objects.filter(scene__campaign=campaign).select_related("scene").iterator():
        data = row.data
        if not isinstance(data, dict):
            continue
        managed = "surface" in data or "surfacePlane" in data
        base = assets.get(data.get("asset_id")) if isinstance(data.get("asset_id"), str) else None
        if not managed:
            if base is not None and base.generated_for_id is not None:
                _invalid()
            continue
        scene, scene_id = row.scene, row.scene_id
        scenes[scene_id] = scene
        if row.kind != "images" or base is None or base.generated_for_id != scene_id:
            _invalid()
        width, height, _ = _inspect(base, cache)
        if (_uuid(data.get("scene_id")) != str(scene_id)
                or data.get("src") != f"/game/map-assets/{base.pk}"
                or type(data.get("natural_width")) is not int or data["natural_width"] != width
                or type(data.get("natural_height")) is not int or data["natural_height"] != height):
            _invalid()
        for key in ("x", "y", "rotation"):
            _number(data.get(key))
        _number(data.get("scale"), .001, 100)
        _number(data.get("z_index"), -10000, 10000)
        if data.get("layer") not in ("map", "gm", "gm-image-layer"):
            _invalid()
        plane = data.get("surfacePlane")
        _fields(plane, ("group", "order", "operation"))
        order = _number(plane["order"], 0, MAX_PLANES - 1, integer=True)
        if order in orders[scene_id] or plane["operation"] not in ("paint", "erase"):
            _invalid()
        orders[scene_id].add(order)
        counts[scene_id] += 1
        if counts[scene_id] > MAX_PLANES:
            _invalid()
        group = None if plane["group"] is None else _uuid(plane["group"])
        if group is not None:
            groups[scene_id].setdefault(group, []).append(data)
            if len(groups[scene_id]) > MAX_GROUPS:
                _invalid()
        elif plane["operation"] != "paint":
            _invalid()
        totals[scene_id] += width * height
        if "surface" in data:
            surface = data["surface"]
            if not isinstance(surface, dict) or surface.get("kind") not in ("floor", "wall"):
                _invalid()
            floor = surface["kind"] == "floor"
            required = ("kind", "maskId", "cellSize", "left", "top", *( ("rotation",) if floor else ("origin", "direction", "phase", "thickness") ))
            _fields(surface, required, ("materialId", *( () if floor else ("materialCrop",) )))
            if plane["operation"] != "paint" or floor != (group is not None):
                _invalid()
            dynamics[scene_id] += 1
            if dynamics[scene_id] > MAX_DYNAMIC:
                _invalid()
            cell = _number(surface["cellSize"], 16, 256, integer=True)
            left = _number(surface["left"], 0, scene.width, integer=True)
            top = _number(surface["top"], 0, scene.height, integer=True)
            if left + width > scene.width or top + height > scene.height:
                _invalid()
            mask = assets.get(_uuid(surface["maskId"]))
            if mask is None or mask.pk == base.pk or mask.generated_for_id != scene_id:
                _invalid()
            if _inspect(mask, cache)[:2] != (width, height):
                _invalid()
            totals[scene_id] += width * height
            material = None
            if "materialId" in surface:
                material = assets.get(_uuid(surface["materialId"]))
                if material is None or material.generated_for_id is not None:
                    _invalid()
                _inspect(material, cache, material=True)
            if floor:
                if _number(surface["rotation"], 0, 270) not in (0, 90, 180, 270):
                    _invalid()
            else:
                for key in ("origin", "direction"):
                    vector = surface[key]
                    if not isinstance(vector, list) or len(vector) != 2:
                        _invalid()
                    for value in vector:
                        _number(value)
                if abs(math.hypot(*surface["direction"]) - 1) > .000001:
                    _invalid()
                _number(surface["phase"])
                _number(surface["thickness"], .000001, 2 * cell)
                if "materialCrop" in surface:
                    crop = surface["materialCrop"]
                    if material is None or not isinstance(crop, list) or len(crop) != 4:
                        _invalid()
                    for value in crop:
                        _number(value, 0, max(material.width, material.height), integer=True)
                    x1, y1, x2, y2 = crop
                    if not (x1 < x2 <= material.width and y1 < y2 <= material.height):
                        _invalid()
        if totals[scene_id] > MAX_SCENE_PIXELS:
            _invalid()
    for scene_id, grouped in groups.items():
        for rows in grouped.values():
            totals[scene_id] += _group_area(rows, scenes[scene_id])
            if totals[scene_id] > MAX_SCENE_PIXELS:
                _invalid()
    _recipes(campaign)
