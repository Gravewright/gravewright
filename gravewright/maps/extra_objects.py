"""Original drawing/image/effect shapes validated at the Django command boundary."""

from copy import deepcopy

from gravewright.journals.services import identifier

from .models import SceneObject
from .objects import boolean, choice, entry, get_object, number
from .services import MapError, color, title

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
    else:
        result.update(
            name=title(p["name"]),
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

    p = {**(previous or {}), **raw}
    asset = MapAsset.objects.filter(
        pk=identifier(p.get("asset_id")), campaign_id=scene.campaign_id
    ).first()
    if asset is None:
        raise MapError("Image not found.")
    return {
        "asset_id": str(asset.pk),
        "scene_id": str(scene.pk),
        "src": f"/game/map-assets/{asset.pk}",
        "natural_width": asset.width,
        "natural_height": asset.height,
        "x": number(p.get("x", 0)),
        "y": number(p.get("y", 0)),
        "rotation": number(p.get("rotation", 0)) % 360,
        "scale": number(p.get("scale", 1), 0.001, 100),
        "z_index": number(p.get("z_index", 0), -10000, 10000),
        "layer": choice(p.get("layer", "map"), {"map", "gm"}),
    }


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
            scene.elements.filter(kind=area).delete()
            return {}
        if action == "create":
            if scene.elements.count() >= 5000:
                raise MapError("Scene object limit reached.")
            obj = SceneObject.objects.create(scene=scene, kind=area, data=validate(p))
        elif action in ("update", "delete"):
            obj = get_object(scene, p.get(idkey, p.get("id")), area)
            expected = p.get("expected_version", p.get("version"))
            if expected is not None and expected != obj.version:
                raise MapError("The object changed.", "conflict")
            if action == "delete":
                obj.delete()
                return {}
            obj.data = validate(p, obj.data)
            obj.version += 1
            obj.save()
        else:
            raise MapError("Unknown object command.")
        return {key: entry(obj)}
    if area == "effects":
        if action == "clear":
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
