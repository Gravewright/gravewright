"""Validated native transforms and runtime flags used by Blueprint actions."""

from copy import deepcopy
import math

from django.conf import settings

from .models import MapBuilderProject, SceneObject
from .services import MapError


def movable(row):
    if row.kind == "images" and "surfacePlane" in row.data and "surface" not in row.data:
        return False
    return (row.kind in ("images", "lights") or row.kind == "walls" and row.data.get("kind") == "door"
            or row.kind == "zones" and isinstance(row.data.get("region"), dict))


def intelligent(row):
    return (row.kind == "walls" and row.data.get("kind") == "door"
            or row.kind == "images" and any(isinstance(row.data.get(key), dict) for key in ("lever", "torch"))
            or row.kind == "zones" and isinstance(row.data.get("region"), dict))


def live_objects(scene):
    from django.db.models import Q
    return SceneObject.objects.filter(scene=scene).filter(Q(kind__in=("images", "lights"))
        | Q(kind="walls", data__kind="door") | Q(kind="zones", data__region__isnull=False)).exclude(
            Q(kind="images", data__surfacePlane__isnull=False, data__surface__isnull=True))


def preserve_interaction(previous, result):
    if previous and "interactionEnabled" in previous and "interactionEnabled" not in result:
        if type(previous["interactionEnabled"]) is not bool:
            raise MapError("Invalid blueprint interaction state.")
        result["interactionEnabled"] = previous["interactionEnabled"]
    return result


def require_interaction(row, who):
    """This gate applies only to direct players, never authored automation."""
    if who.role != "gm" and row.data.get("interactionEnabled") is False:
        error = MapError("Player interaction is disabled for this object.", "forbidden")
        if row.data.get("blueprint") is not None:
            from .blueprint_runtime import element_state
            state = element_state(row)
            error.automation_run = {"requested": None, "stateBefore": state, "stateAfter": state,
                                    "events": [], "message": str(error)}
        raise error


def acknowledge_geometry(scene, row, before):
    """Adopt only the transform of an unchanged owned snapshot, preserving conflicts."""
    from .builder_services import strip_live
    for source in MapBuilderProject.objects.filter(scene=scene):
        manifest = deepcopy(source.generation)
        changed = False
        for record in manifest.get("objects", []):
            if record.get("id") != str(row.pk) or record.get("kind") != row.kind:
                continue
            stored, actual = deepcopy(record["data"]), deepcopy(before)
            strip_live(stored, actual, kind=row.kind)
            if stored == actual:
                record["data"] = deepcopy(row.data)
                changed = True
        if changed:
            source.generation = manifest
            source.save(update_fields=["generation"])


def transform(scene, who, row, action):
    """Transform one live object with its native validator inside the caller's transaction."""
    from .objects import light, number, wall
    if not movable(row):
        return False
    if row.kind == "lights" and not settings.DYNAMIC_LIGHTING_ENABLED:
        raise MapError("Dynamic lighting is disabled.", "forbidden")
    before = deepcopy(row.data)
    if action["type"] == "move":
        from gravewright.tokens.services import geometry
        cell = geometry(scene)[0]
        dx, dy = action["dx"] * cell, action["dy"] * cell
        if row.kind == "walls":
            patch = {f"{axis}{index}": number(before[f"{axis}{index}"] + (dx if axis == "x" else dy))
                     for axis in ("x", "y") for index in (1, 2)}
        elif row.kind == "zones":
            g = before["geometry"]
            patch = {"geometry": {**g, "x": number(g["x"] + dx), "y": number(g["y"] + dy)}}
        else:
            patch = {"x": number(before["x"] + dx), "y": number(before["y"] + dy)}
    else:
        degrees = action["degrees"]
        if row.kind == "walls":
            offset = {"start": 0, "end": 1}.get(before.get("rotationAnchor"), .5)
            cx = before["x1"] + (before["x2"] - before["x1"]) * offset
            cy = before["y1"] + (before["y2"] - before["y1"]) * offset
            c, s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
            patch = {}
            for index in (1, 2):
                x, y = before[f"x{index}"] - cx, before[f"y{index}"] - cy
                patch.update({f"x{index}": number(cx + x * c - y * s), f"y{index}": number(cy + x * s + y * c)})
        elif row.kind == "zones":
            if degrees % 90:
                raise MapError("Presence regions can only rotate in multiples of 90 degrees.")
            g = before["geometry"]
            width, height = (g["height"], g["width"]) if int(degrees / 90) % 2 else (g["width"], g["height"])
            patch = {"geometry": {"shape": "rect", "x": number(g["x"] + (g["width"] - width) / 2),
                                  "y": number(g["y"] + (g["height"] - height) / 2), "width": width, "height": height}}
        else:
            patch = {"rotation": (before.get("rotation", 0) + degrees) % 360}
    if row.kind == "walls":
        row.data = wall(patch, before, campaign_id=scene.campaign_id, scene_id=scene.pk)
    elif row.kind == "images":
        from .extra_objects import image
        row.data = image(scene, patch, before)
    elif row.kind == "lights":
        row.data = light(patch, before)
    else:
        from .zones import clean
        from .regions import rebaseline_region
        row.data = clean(patch, who, before, scene_id=scene.pk)
        if row.data["geometry"] != before["geometry"]:
            rebaseline_region(scene, row)
        else:
            row.data["region"] = before["region"]
    if row.data != before:
        if row.kind == "images":
            from .regions import rebaseline_object
            rebaseline_object(scene, row)
        if row.kind == "images" and "torch" in row.data:
            from .torches import sync_components
            sync_components(row, before, remember=True)
        row.version += 1
        row.save(update_fields=["data", "version"])
        acknowledge_geometry(scene, row, before)
    return True


def clean_sprite_base(raw):
    """Validate the private restoration record of an ordinary image override."""
    from .objects import choice, identifier, number
    if not isinstance(raw, dict) or set(raw) != {"assetId", "layer", "width", "height"}:
        raise MapError("Invalid sprite base image.")
    return {"assetId": str(identifier(raw["assetId"])),
            "layer": choice(raw["layer"], {"map", "gm-image-layer"}),
            **{key: number(raw[key], .001, 1_000_000) for key in ("width", "height")}}


def validate_campaign_sprites(campaign):
    """Validate remapped restoration records before committing a campaign import."""
    from .blueprint_runtime import clean_sprite
    from .models import MapAsset
    assets = {str(asset.pk): asset for asset in MapAsset.objects.filter(campaign=campaign, generated_for__isnull=True)}
    for row in SceneObject.objects.filter(scene__campaign=campaign, data__spriteBase__isnull=False):
        data = row.data
        if row.kind != "images" or intelligent(row) or "surface" in data:
            raise MapError("Invalid sprite base image.")
        base, sprite = clean_sprite_base(data["spriteBase"]), clean_sprite(data.get("sprite"))
        if sprite is None or sprite["appearance"] not in ("asset", "hidden") or base["assetId"] not in assets:
            raise MapError("Invalid sprite base image.")
        asset_id = sprite.get("assetId", base["assetId"])
        asset = assets.get(asset_id)
        if (asset is None or data.get("asset_id") != asset_id
                or data.get("src") != f"/game/map-assets/{asset_id}"
                or data.get("natural_width") != asset.width or data.get("natural_height") != asset.height):
            raise MapError("Invalid sprite base image.")
        expected_scale = min(base["width"] / asset.width, base["height"] / asset.height)
        scale = data.get("scale")
        if type(scale) not in (int, float) or not math.isfinite(scale) or not math.isclose(scale, expected_scale):
            raise MapError("Invalid sprite base image.")
        if data.get("layer") != ("gm-image-layer" if sprite["appearance"] == "hidden" else base["layer"]):
            raise MapError("Invalid sprite base image.")


def change_sprite(scene, row, action):
    """Apply a live image to Self or a target without starting its behavior.

    Ordinary images retain a server-owned base image and box while overridden,
    so restoring their native appearance also restores their original visibility.
    """
    if row.kind == "walls" and row.data.get("kind") == "door" or row.kind == "images" and intelligent(row):
        if row.data.get("empty") is True:
            return False
        from .blueprint_runtime import apply_lever_appearance
        row.data["sprite"] = {key: action[key] for key in ("appearance", "assetId") if key in action}
        if row.kind == "images":
            apply_lever_appearance(row)
        return True
    if row.kind != "images":
        return False
    mode = action["appearance"]
    if isinstance(row.data.get("surface"), dict):
        from .builder_dynamic import set_appearance, set_visibility
        if mode == "asset":
            return set_appearance(scene, row, action["assetId"])
        if mode == "inherit":
            row.data["surface"].pop("materialId", None)
            row.data["surface"].pop("materialCrop", None)
        return set_visibility(scene, row, mode != "hidden")
    from .models import MapAsset
    base = clean_sprite_base(row.data["spriteBase"] if "spriteBase" in row.data else {
        "assetId": row.data["asset_id"], "layer": row.data["layer"],
        "width": row.data["natural_width"] * row.data["scale"],
        "height": row.data["natural_height"] * row.data["scale"],
    })
    width, height = base["width"], base["height"]
    asset_id = action["assetId"] if mode == "asset" else base["assetId"]
    asset = MapAsset.objects.filter(pk=asset_id, campaign_id=scene.campaign_id, generated_for__isnull=True).first()
    if asset is None:
        raise MapError("Choose an image from this campaign.")
    row.data.update(asset_id=str(asset.pk), src=f"/game/map-assets/{asset.pk}",
                    natural_width=asset.width, natural_height=asset.height,
                    scale=min(width / asset.width, height / asset.height),
                    layer="gm-image-layer" if mode == "hidden" else base["layer"])
    if mode == "inherit" and .001 <= row.data["scale"] <= 100:
        row.data.pop("sprite", None)
        row.data.pop("spriteBase", None)
    else:
        row.data["spriteBase"] = deepcopy(base)
        # A native edit may adopt an image whose fitted scale needs the bounded
        # restoration box even after the visual override has been restored.
        row.data["sprite"] = ({"appearance": "asset", "assetId": str(asset.pk)} if mode == "inherit"
                              else {key: action[key] for key in ("appearance", "assetId") if key in action})
    return True


def change_visual(scene, row, action):
    """Change artwork only; collision and native barriers stay independent."""
    if row.kind == "images" and row.data.get("empty") is True:
        return False
    if row.kind == "images" and "spriteBase" in row.data:
        if action["type"] == "setAppearance":
            return change_sprite(scene, row, {"appearance": "asset", "assetId": action["assetId"]})
        before = deepcopy(row.data)
        if row.data.get("sprite", {}).get("appearance") == "hidden" and action["visible"]:
            change_sprite(scene, row, {"appearance": "inherit"})
        layer = "map" if action["visible"] else "gm-image-layer"
        row.data["layer"] = layer
        if "spriteBase" in row.data:
            row.data["spriteBase"]["layer"] = layer
        acknowledge_geometry(scene, row, before)
        return True
    from .builder_dynamic import set_appearance, set_visibility
    surface = set_visibility if action["type"] == "setVisibility" else set_appearance
    parameter = action["visible"] if action["type"] == "setVisibility" else action["assetId"]
    if surface(scene, row, parameter):
        return True
    if row.kind == "walls" and row.data.get("kind") == "door" or row.kind == "images" and intelligent(row):
        row.data["sprite"] = ({"appearance": "inherit" if parameter else "hidden"}
                              if action["type"] == "setVisibility" else {"appearance": "asset", "assetId": parameter})
        if row.kind == "images":
            from .blueprint_runtime import apply_lever_appearance
            apply_lever_appearance(row)
        return True
    if row.kind != "images":
        return False
    before = deepcopy(row.data)
    if action["type"] == "setVisibility":
        row.data["layer"] = "map" if parameter else "gm-image-layer"
    else:
        from .extra_objects import image
        row.data = image(scene, {"asset_id": parameter}, before)
    acknowledge_geometry(scene, row, before)
    return True
