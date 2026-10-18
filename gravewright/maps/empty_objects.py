"""Image-free intelligent objects share native image geometry and automation."""

from copy import deepcopy

from .services import MapError
from .element_names import copy_name


def validate_blueprint(blueprint, owner_id=None):
    """Keep state artwork image-free; visual nodes may control explicit targets."""
    if any(entry["appearance"] != "inherit" for entry in blueprint["states"].values()):
        raise MapError("Empty objects do not have state images.")


def image(scene, raw, previous=None):
    """Validate an empty object's native creation or transform without an asset."""
    from .objects import boolean, choice, number
    from .blueprint_actions import preserve_interaction
    from .blueprint_runtime import clean_native_blueprint, clean_lever
    from .blueprint_variables import copy_runtime

    before = previous or {}
    if "areaPresence" in raw:
        raise MapError("Object area membership cannot be edited.")
    p = {**before, **raw}
    if (p.get("empty") is not True or p.get("asset_id") is not None or p.get("src", "") != ""
            or "torch" in p or "surface" in raw or "surfacePlane" in raw):
        raise MapError("An empty object cannot receive images.")
    if before and before.get("empty") is not True:
        raise MapError("An image cannot become an empty object.")
    lever = clean_lever(before.get("lever", raw.get("lever")), empty=True)
    natural_width = number(p.get("natural_width", lever["width"]), .001, 1_000_000)
    natural_height = number(p.get("natural_height", lever["height"]), .001, 1_000_000)
    scale = number(p.get("scale", 1), .001, 100)
    choice(p.get("layer", "gm-image-layer"), {"map", "gm", "gm-image-layer"})
    layer = "gm-image-layer"
    lever.update(width=number(natural_width * scale, .001, 1_000_000),
                 height=number(natural_height * scale, .001, 1_000_000), baseLayer=layer)
    result = {"empty": True, "asset_id": None, "src": "", "scene_id": str(scene.pk),
              "natural_width": natural_width, "natural_height": natural_height,
              "scale": scale, "x": number(p.get("x", 0)), "y": number(p.get("y", 0)),
              "rotation": number(p.get("rotation", 0)) % 360,
              "z_index": number(p.get("z_index", 0), -10000, 10000), "layer": layer, "lever": lever}
    copy_name(result, p)
    if "blueprint" in p:
        blueprint = clean_native_blueprint(p["blueprint"], scene.campaign_id, scene.pk, kind="lever")
        validate_blueprint(blueprint, raw.get("placement_id", raw.get("id")))
        result["blueprint"] = blueprint
    if "interactionEnabled" in raw:
        result["interactionEnabled"] = boolean(raw["interactionEnabled"])
    if "areaPresence" in before:
        result["areaPresence"] = deepcopy(before["areaPresence"])
    return preserve_interaction(before, copy_runtime(before, result))


def native(scene, source, cell, z_index):
    """Create native metadata for an authored empty object; artwork never exists."""
    width, height = source["width"] * cell, source["height"] * cell
    result = {"empty": True, "asset_id": None, "src": "", "scene_id": str(scene.pk),
              "natural_width": width, "natural_height": height, "scale": 1,
              "x": (source["x"] + source["width"] / 2) * cell,
              "y": (source["y"] + source["height"] / 2) * cell,
              "rotation": source["rotation"], "layer": "gm-image-layer", "z_index": z_index,
              "lever": {"state": source["lever"]["state"], "baseAssetId": None,
                        "baseLayer": "gm-image-layer", "width": width, "height": height}}
    for key in ("name", "interactionEnabled"):
        if key in source:
            result[key] = deepcopy(source[key])
    return result
