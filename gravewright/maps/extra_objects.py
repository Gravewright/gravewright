"""Original drawing/image/effect shapes validated at the Django command boundary."""

from copy import deepcopy

from gravewright.journals.services import identifier

from .models import SceneObject
from .objects import boolean, choice, entry, get_object, number
from .services import MapError, color
from .element_names import clean_name, copy_name

PARTICLES = {
    "smoke",
    "ember",
    "dust",
    "arcane",
    "rain",
    "snow",
    "firefly",
    "leaves",
    "bubbles",
    "ash",
    "blood",
    "runes",
}


def effect(kind, raw, previous=None):
    if not isinstance(raw, dict):
        raise MapError("Invalid effect.")
    p = {
        "x": 0,
        "y": 0,
        "color": "#9aa3ad",
        "enabled": True,
        "rotation": 0,
        "scale": 3,
        "density": 0.6,
        "light_response": 0,
        "light_emission": 0,
        "kind": "smoke",
        "name": "Shader",
        "source": "",
        "radius": 0,
        "opacity": 1,
        "intensity": 0.6,
        "speed": 1,
        "blend_mode": "normal",
        **(previous or {}),
        **raw,
    }
    result = {k: number(p[k]) for k in ("x", "y")}
    result.update(color=color(p["color"]), enabled=boolean(p["enabled"]))
    ranges = {
        "rotation": (-36000, 36000),
        "scale": (0.1, 20),
        "light_response": (0, 1),
        "light_emission": (0, 2),
    }
    ranges.update(
        {"density": (0, 1)}
        if kind == "particles"
        else {
            "radius": (0, 1e6),
            "opacity": (0, 1),
            "intensity": (0, 1),
            "speed": (0, 8),
        }
    )
    for k, (lo, hi) in ranges.items():
        result[k] = number(p[k], lo, hi)
    result["rotation"] %= 360
    if kind == "particles":
        result["kind"] = choice(p["kind"], PARTICLES)
        copy_name(result, {**(previous or {}), **raw})
    else:
        result.update(
            name=clean_name(p["name"]),
            blend_mode=choice(p["blend_mode"], {"normal", "add", "screen", "multiply"}),
        )
        source = p["source"]
        if (
            not isinstance(source, str)
            or not source.strip()
            or len(source) > 32000
            or "\x00" in source
        ):
            raise MapError("Invalid shader source.")
        result["source"] = source
    return result


def drawing(raw):
    if not isinstance(raw, dict):
        raise MapError("Invalid drawing.")
    result = {
        "id": str(identifier(raw.get("id"))),
        "kind": choice(
            raw.get("kind"), {"pen", "line", "arrow", "rect", "ellipse", "text"}
        ),
        "audience": choice(raw.get("audience"), {"gm", "campaign"}),
        "color": color(raw.get("color")),
    }
    result["fill"] = "none" if raw.get("fill") == "none" else color(raw.get("fill"))
    for k, lo, hi in [
        ("width", 1, 64),
        ("opacity", 0.05, 1),
        ("fontSize", 8, 144),
        ("rotation", -36000, 36000),
    ]:
        result[k] = number(raw.get(k, 0 if k == "rotation" else None), lo, hi)
    value = raw.get("text", "")
    if not isinstance(value, str) or len(value) > 1000:
        raise MapError("Invalid drawing text.")
    result["text"] = value
    points = raw.get("points")
    if not isinstance(points, list) or not 1 <= len(points) <= 4096:
        raise MapError("Invalid drawing points.")
    if result["kind"] in {"line", "arrow", "rect", "ellipse"} and len(points) != 2:
        raise MapError("Invalid shape endpoints.")
    if any(not isinstance(p, dict) for p in points):
        raise MapError("Invalid points.")
    result["points"] = [
        {"x": number(p.get("x")), "y": number(p.get("y"))} for p in points
    ]
    return result


def image(scene, raw, previous=None):
    from .models import MapAsset

    if "areaPresence" in raw:
        raise MapError("Object area membership cannot be edited.")
    if (previous or {}).get("empty") is True or "empty" in raw:
        from .empty_objects import image as empty_image
        return empty_image(scene, raw, previous)
    p = {**(previous or {}), **raw}
    asset = MapAsset.objects.filter(
        pk=identifier(p.get("asset_id")), campaign_id=scene.campaign_id
    ).first()
    if asset is None:
        raise MapError("Image not found.")
    if asset.generated_for_id is not None and (previous or {}).get("asset_id") != str(asset.pk):
        raise MapError("Generated map artwork cannot be reused as an asset.")
    if "surface" in raw or "surfacePlane" in raw:
        raise MapError("Generated map artwork cannot be changed directly.")
    element_key = "torch" if isinstance((previous or {}).get("torch"), dict) else "lever"
    lever = (previous or {}).get(element_key)
    layer = "gm-image-layer" if p.get("layer") == "gm" else choice(p.get("layer", "map"), {"map", "gm-image-layer"})
    sprite_base = (previous or {}).get("spriteBase")
    has_sprite = isinstance(sprite_base, dict) and not isinstance(lever, dict)
    scale_limits = (0.001, 100)
    if isinstance(lever, dict) or has_sprite:
        from .blueprint_runtime import MAX_LEVER_DIMENSION, MIN_LEVER_DIMENSION
        # State and action artwork fit a bounded authored box even when their
        # pixel dimensions differ. Images without an override keep the native
        # scale contract; the final stored box remains bounded below.
        scale_limits = (MIN_LEVER_DIMENSION / max(asset.width, asset.height),
                        MAX_LEVER_DIMENSION / min(asset.width, asset.height))
    result = {
        "asset_id": str(asset.pk),
        "scene_id": str(scene.pk),
        "src": f"/game/map-assets/{asset.pk}",
        "natural_width": asset.width,
        "natural_height": asset.height,
        "x": number(p.get("x", 0)),
        "y": number(p.get("y", 0)),
        "rotation": number(p.get("rotation", 0)) % 360,
        "scale": number(p.get("scale", 1), *scale_limits),
        "z_index": number(p.get("z_index", 0), -10000, 10000),
        "layer": layer,
    }
    copy_name(result, p)
    if isinstance(lever, dict):
        # A lever's state and graphs are kept through GM edits; authored payloads
        # cannot set them. Its box follows the edited image so later state images
        # appear at the size the GM chose.
        from .blueprint_runtime import clean_lever, clean_sprite
        from .torches import clean_native
        clean_element = clean_native if element_key == "torch" else clean_lever
        lever = clean_element(lever)
        if result["asset_id"] != previous.get("asset_id"):
            lever.update(width=result["natural_width"] * result["scale"],
                         height=result["natural_height"] * result["scale"])
        elif result["scale"] != previous.get("scale"):
            # Dragging sends an unchanged scale too. A real resize scales the
            # full authored box, including space around a differently shaped
            # state image, so the next state keeps the same proportions.
            ratio = result["scale"] / number(previous.get("scale"), *scale_limits)
            lever.update(width=lever["width"] * ratio, height=lever["height"] * ratio)
        if raw.get("asset_id") is not None and str(raw["asset_id"]) != str(previous.get("asset_id")):
            lever["baseAssetId"] = result["asset_id"]
        if raw.get("layer") is not None:
            lever["baseLayer"] = result["layer"]
        if element_key == "torch" and raw.get("rotation") is not None:
            lever["baseRotation"] = (result["rotation"] - (90 if lever["state"] == "on" else 0)) % 360
        result[element_key] = clean_element(lever)
        for key in ("blueprint",):
            if previous.get(key) is not None:
                result[key] = previous[key]
        if "blueprint" in raw:
            from .blueprint_runtime import clean_native_blueprint
            result["blueprint"] = clean_native_blueprint(raw["blueprint"], scene.campaign_id, scene.pk, kind=element_key)
        sprite = clean_sprite(previous.get("sprite"))
        if sprite is not None:
            result["sprite"] = sprite
    elif "blueprint" in raw:
        raise MapError("Only interactive images can have a blueprint.")
    elif has_sprite:
        from .blueprint_runtime import clean_sprite
        sprite = clean_sprite(previous.get("sprite"))
        if (sprite is None or set(sprite_base) != {"assetId", "layer", "width", "height"}
                or sprite_base["layer"] not in {"map", "gm-image-layer"}):
            raise MapError("Invalid image appearance snapshot.")
        changed_asset = result["asset_id"] != previous.get("asset_id")
        changed_layer = result["layer"] != previous.get("layer")
        if changed_asset or changed_layer and sprite["appearance"] == "hidden":
            # A replacement adopts the displayed artwork. Keep a validated
            # snapshot when its fitted scale exceeds the native scale range,
            # so subsequent moves and archive validation still accept it.
            if not .001 <= result["scale"] <= 100:
                result["spriteBase"] = {"assetId": result["asset_id"], "layer": result["layer"],
                    "width": number(result["natural_width"] * result["scale"], .001, 1_000_000),
                    "height": number(result["natural_height"] * result["scale"], .001, 1_000_000)}
                result["sprite"] = {"appearance": "asset", "assetId": result["asset_id"]}
        else:
            base = {**deepcopy(sprite_base), "assetId": str(identifier(sprite_base["assetId"]))}
            ratio = result["scale"] / number(previous.get("scale"), *scale_limits)
            for dimension in ("width", "height"):
                base[dimension] = number(number(base[dimension], .001, 1_000_000) * ratio, .001, 1_000_000)
            if changed_layer:
                base["layer"] = result["layer"]
            result["sprite"] = sprite
            result["spriteBase"] = base
    if "interactionEnabled" in raw:
        result["interactionEnabled"] = boolean(raw["interactionEnabled"])
    if isinstance((previous or {}).get("surface"), dict):
        result["surface"] = deepcopy(previous["surface"])
    if isinstance((previous or {}).get("surfacePlane"), dict):
        result["surfacePlane"] = deepcopy(previous["surfacePlane"])
    from .blueprint_variables import copy_runtime
    from .blueprint_actions import preserve_interaction
    if previous and "areaPresence" in previous:
        result["areaPresence"] = deepcopy(previous["areaPresence"])
    return preserve_interaction(previous, copy_runtime(previous, result))


def apply(scene, who, env, area, action, p):
    if who.role != "gm":
        raise MapError("Only the GM can edit this layer.", "forbidden")
    if area == "drawings":
        if action != "replace":
            raise MapError("Invalid drawing command.")
        old = env.drawings or {"version": 0, "rows": []}
        if p.get("expected_version") != old["version"]:
            raise MapError("Drawings changed. Refresh and try again.", "conflict")
        rows = p.get("rows")
        if not isinstance(rows, list) or len(rows) > 500:
            raise MapError("Use up to 500 drawings.")
        cleaned = [drawing(r) for r in rows]
        if sum(len(r["points"]) for r in cleaned) > 50000:
            raise MapError("Drawing point limit reached.")
        if len({r["id"] for r in cleaned}) != len(cleaned):
            raise MapError("Duplicate drawing identifier.")
        env.drawings = {"version": old["version"] + 1, "rows": cleaned}
        return deepcopy(env.drawings)
    if area in ("particles", "shaders", "images"):
        key = {"particles": "emitter", "shaders": "shader", "images": "image"}[area]
        idkey = "placement_id" if area == "images" else key + "_id"
        validate = lambda raw, previous=None: (
            image(scene, raw, previous)
            if area == "images"
            else effect(area, raw, previous)
        )
        if action == "clear":
            from .torches import detach_component
            if area == "images":
                from .blueprint_lifecycle import destroy_objects
                destroy_objects(scene, who, scene.elements.filter(kind=area))
            else:
                for row in list(scene.elements.filter(kind=area)):
                    detach_component(scene, row.pk)
                scene.elements.filter(kind=area).delete()
            return {}
        if action == "duplicate" and area == "images":
            from .torches import duplicate
            parent = get_object(scene, p.get("image_id"), "images")
            if not isinstance(parent.data.get("torch"), dict):
                raise MapError("Choose a torch.")
            return {"image": entry(duplicate(parent, p))}
        if action == "create":
            if scene.elements.count() >= 5000:
                raise MapError("Scene object limit reached.")
            obj = SceneObject(scene=scene, kind=area, data=validate(p))
            if area == "images":
                from .regions import rebaseline_object
                rebaseline_object(scene, obj)
            obj.save()
        elif action in ("update", "delete"):
            obj = get_object(scene, p.get(idkey, p.get("id")), area)
            expected = p.get("expected_version", p.get("version"))
            if expected is not None and (type(expected) is not int or expected != obj.version):
                raise MapError("The object changed.", "conflict")
            if action == "delete":
                from .torches import detach_component
                if area == "images":
                    from .blueprint_lifecycle import destroy_objects
                    destroy_objects(scene, who, [obj])
                else:
                    detach_component(scene, obj.pk)
                    obj.delete()
                return {}
            before = deepcopy(obj.data)
            obj.data = validate(p, obj.data)
            if area == "images":
                from .torches import sync_components
                sync_components(obj, before)
                from .regions import rebaseline_object
                rebaseline_object(scene, obj)
            else:
                from .torches import gate_edit
                gate_edit(scene, obj, p)
            obj.version += 1
            obj.save()
        else:
            raise MapError("Unknown object command.")
        return {key: entry(obj)}
    if area == "effects":
        if action == "clear":
            from .torches import detach_component
            for child in list(scene.elements.filter(kind__in=("particles", "shaders"))):
                detach_component(scene, child.pk)
            scene.elements.filter(kind__in=("particles", "shaders")).delete()
            return {}
        rows = p.get("effects")
        if not isinstance(rows, list) or not 1 <= len(rows) <= 500:
            raise MapError("Invalid effect selection.")
        if action == "paste" and scene.elements.count() + len(rows) > 5000:
            raise MapError("Scene object limit reached.")
        result = []
        for ref in rows:
            if not isinstance(ref, dict):
                raise MapError("Invalid effect reference.")
            kind = {"particle": "particles", "shader": "shaders"}.get(ref.get("kind"))
            if not kind:
                raise MapError("Invalid effect kind.")
            if action == "paste":
                obj = SceneObject.objects.create(
                    scene=scene, kind=kind, data=effect(kind, ref.get("data"))
                )
            elif action in ("transform", "delete"):
                obj = get_object(scene, ref.get("id"), kind)
                if action == "delete":
                    from .torches import detach_component
                    detach_component(scene, obj.pk)
                    obj.delete()
                    continue
                obj.data = effect(
                    kind,
                    {
                        **obj.data,
                        "x": obj.data["x"] + number(p.get("dx", 0)),
                        "y": obj.data["y"] + number(p.get("dy", 0)),
                        "rotation": obj.data["rotation"] + number(p.get("rotation", 0)),
                    },
                )
                obj.version += 1
                obj.save()
            else:
                raise MapError("Unknown effect command.")
            result.append({"kind": ref["kind"], "id": str(obj.pk)})
        return {"effects": result}
    raise MapError("Unknown scene command.")
