"""Validated scene layer commands and recipient-specific render state."""

from django.conf import settings
from copy import deepcopy
import math
from .models import SceneObject, SceneState
from .services import MapError, color, manage
from gravewright.journals.services import identifier


def number(value, low=-1e6, high=1e6):
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or not low <= value <= high
    ):
        raise MapError("Invalid scene coordinate or value.")
    return value


def boolean(value):
    if type(value) is not bool:
        raise MapError("Invalid boolean value.")
    return value


def choice(value, options):
    if not isinstance(value, str) or value not in options:
        raise MapError("Invalid scene option.")
    return value


def wall(raw, previous=None):
    if not isinstance(raw, dict):
        raise MapError("Invalid wall.")
    p = {**(previous or {}), **raw}
    data = {k: number(p.get(k)) for k in ("x1", "y1", "x2", "y2")}
    if math.hypot(data["x2"] - data["x1"], data["y2"] - data["y1"]) < 0.01:
        raise MapError("Wall endpoints must differ.")
    data["kind"] = choice(p.get("kind", "wall"), {"wall", "door"})
    data["presentation"] = choice(
        p.get("presentation", "normal"),
        {"normal", "secret", "window", "bars", "invisible"},
    )
    data["door_state"] = choice(
        p.get("door_state", "closed"), {"open", "closed", "locked"}
    )
    data["discovered"] = boolean(p.get("discovered", False))
    behavior = p.get("behavior", {})
    if not isinstance(behavior, dict):
        raise MapError("Invalid wall behavior.")
    for key in ("movement", "vision", "light", "sound"):
        data[key + "_behavior"] = choice(
            behavior.get(key, p.get(key + "_behavior", "block")),
            {"block", "pass", "attenuate"} if key == "sound" else {"block", "pass"},
        )
    vertical = p.get("vertical", {})
    if not isinstance(vertical, dict):
        raise MapError("Invalid elevation range.")
    for key in ("bottom", "top"):
        value = vertical.get(key, p.get("vertical_" + key))
        data["vertical_" + key] = None if value is None else number(value)
    if (data["vertical_bottom"] is None) != (data["vertical_top"] is None) or (
        data["vertical_bottom"] is not None
        and data["vertical_bottom"] >= data["vertical_top"]
    ):
        raise MapError("Upper height must be greater than lower height.")
    data["blocks_light"] = int(data["light_behavior"] == "block")
    data["blocks_sight"] = int(data["vision_behavior"] == "block")
    return data


def light(raw, previous=None):
    if not isinstance(raw, dict):
        raise MapError("Invalid light.")
    p = {
        "bright_radius": 2,
        "dim_radius": 4,
        "intensity": 0.85,
        "angle": 360,
        "rotation": 0,
        "animation": "none",
        "color": "#ffd8a8",
        "enabled": True,
        "elevation": 0,
        **(previous or {}),
        **raw,
    }
    data = {k: number(p.get(k)) for k in ("x", "y", "elevation")}
    for k, lo, hi in [
        ("bright_radius", 0, 200),
        ("dim_radius", 0, 200),
        ("intensity", 0, 1),
        ("angle", 5, 360),
        ("rotation", -36000, 36000),
    ]:
        data[k] = number(p[k], lo, hi)
    if 0 < data["dim_radius"] < data["bright_radius"]:
        data["dim_radius"] = data["bright_radius"]
    data["rotation"] %= 360
    data["color"] = color(p["color"]).lower()
    data["animation"] = choice(
        p["animation"], {"none", "torch", "pulse", "candle", "fire", "arcane", "smoke"}
    )
    data["enabled"] = boolean(p["enabled"])
    return data


def get_object(scene, pk, kind=None):
    obj = SceneObject.objects.filter(scene=scene, pk=identifier(pk)).first()
    if not obj or (kind and obj.kind != kind):
        raise MapError("Scene object not found.")
    return obj


def entry(obj):
    return {"id": str(obj.pk), **obj.data, "version": obj.version}


def layer_state(scene, who):
    env = SceneState.objects.filter(scene=scene).first()
    result = {
        "containerId": str(scene.campaign_id),
        "blockId": str(scene.block_id),
        "sceneId": str(scene.pk),
        "version": env.version if env else 1,
        "walls": [],
        "lights": [],
        "particles": [],
        "images": [],
        "shaders": [],
        "cards": [],
        "markers": [],
        "spatialSounds": [],
        "vision": __import__("gravewright.tokens.services", fromlist=["vision"]).vision(
            scene, who
        ),
        "zones": [],
        "combat": {
            "active": False,
            "round": 0,
            "combatants": [],
            "current_name": "",
            "combat_id": "",
        },
        "audio": [],
        "drawings": deepcopy(env.drawings)
        if env and env.drawings
        else {"version": 0, "rows": []},
        "lighting": {
            "mode": "none",
            "darkness": 1,
            "lights_out": True,
            **(env.lighting if env else {}),
        },
        "fog": {
            "enabled": False,
            "baseline": "reveal_all",
            "ops": [],
            "version": 1,
            **(env.fog if env else {}),
        },
    }
    for obj in scene.elements.all():
        if obj.kind in result:
            result[obj.kind].append(entry(obj))
    if who.role != "gm":
        result["images"] = [r for r in result["images"] if r.get("layer") != "gm"]
        result["drawings"]["rows"] = [
            r
            for r in result["drawings"].get("rows", [])
            if r.get("audience") == "campaign"
        ]
        # Geometry remains necessary for visibility clipping. Secret and invisible
        # barriers have no interactive door handles until the GM reveals them.
        for w in result["walls"]:
            if w["presentation"] in ("secret", "invisible") and not w["discovered"]:
                w["kind"] = "wall"
    from .zones import visible as zone_visible
    result['zones'] = [{**z,'sceneId':str(scene.pk)} for z in result['zones'] if zone_visible(z,who)]
    result['markers'] = [{**r,'canEdit':who.role=='gm' or r.get('owner')==str(who.user_id)} for r in result['markers']]
    result['capabilities'] = {
        'dynamicLighting': settings.DYNAMIC_LIGHTING_ENABLED,
        'fogExpectedVersion': settings.FOG_REQUIRE_EXPECTED_VERSION,
        'fogMaxOps': settings.FOG_MAX_OPS_PER_COMMAND,
        'fogMaxPoints': settings.FOG_MAX_POLYGON_POINTS,
        'maxMeasurements': settings.BOARD_MEASUREMENTS_MAX_PER_USER,
        'maxMarkers': settings.BOARD_MARKERS_MAX_PER_SCENE,
    }
    if not settings.DYNAMIC_LIGHTING_ENABLED:
        result['lights'] = []
        if result['lighting']['mode'] == 'dynamic':
            result['lighting']['mode'] = 'none'
            result['lighting']['darkness'] = 0
    from gravewright.cards.services import state as card_state
    from gravewright.combat.services import state as combat_state
    cards = card_state(who,str(scene.pk))['cards']
    result['cards'] = [{**c,'can_manage':c['canControl'],'card':{**c,'src':c['frontUrl'] if c['face_state']=='face_up' else c['backUrl']}} for c in cards]
    result['combat'] = combat_state(who,str(scene.pk))
    from gravewright.audio.services import soundscape_state
    result['soundscape'] = soundscape_state(scene)
    lighting = result["lighting"]
    lighting["effective_darkness"] = (
        lighting["darkness"] if lighting["lights_out"] else 0
    )
    return result


def apply(scene, who, area, action, p):
    if (
        not isinstance(area, str)
        or not isinstance(action, str)
        or not isinstance(p, dict)
    ):
        raise MapError("Invalid scene command.")
    if not settings.DYNAMIC_LIGHTING_ENABLED and (
        area == 'lights' or area == 'lighting' and p.get('mode') == 'dynamic'
    ):
        raise MapError('Dynamic lighting is disabled.', 'forbidden')
    env, _ = SceneState.objects.get_or_create(scene=scene)
    result = {}
    if area == "zones":
        from .zones import apply as zones
        result=zones(scene,who,action,p)
        env.version+=1;env.save()
        return result
    if area == "soundscape":
        from gravewright.audio.services import set_soundscape
        if action != 'set':raise MapError('Unknown soundscape command.')
        return set_soundscape(scene, who, p)
    if area == "markers":
        if action != "replace":raise MapError("Unknown marker command.")
        from .markers import replace
        return replace(scene,who,env,p)
    if area in ("drawings", "images", "particles", "shaders", "effects"):
        from .extra_objects import apply as extra

        result = extra(scene, who, env, area, action, p)
        env.version += 1
        env.save()
        return result
    if area == "walls" and action == "door":
        obj = get_object(scene, p.get("wall_id"), "walls")
        target = choice(p.get("door_state"), {"open", "closed", "locked"})
        if obj.data["kind"] != "door":
            raise MapError("Choose a door.")
        if who.role != "gm" and (
            obj.data["door_state"] == "locked"
            or target == "locked"
            or (
                obj.data["presentation"] in ("secret", "invisible")
                and not obj.data["discovered"]
            )
        ):
            raise MapError("This door cannot be operated.")
        obj.data["door_state"] = target
        obj.version += 1
        obj.save()
        result = {"wall": entry(obj)}
    else:
        manage(who)
        if area in ("walls", "lights"):
            validator = wall if area == "walls" else light
            key = "wall" if area == "walls" else "light"
            if action == "clear":
                scene.elements.filter(kind=area).delete()
            elif action == "create":
                if scene.elements.count() >= 5000:
                    raise MapError("Scene object limit reached.")
                obj = SceneObject.objects.create(
                    scene=scene, kind=area, data=validator(p)
                )
                result = {key: entry(obj)}
            elif action in ("update", "delete"):
                obj = get_object(scene, p.get(key + "_id", p.get("id")), area)
                if action == "delete":
                    obj.delete()
                else:
                    if "version" in p and p["version"] != obj.version:
                        raise MapError(
                            "This object changed. Reopen it and try again.", "conflict"
                        )
                    obj.data = validator(p, obj.data)
                    obj.version += 1
                    obj.save()
                    result = {key: entry(obj)}
            elif area == "walls" and action in ("move-node", "move-endpoint"):
                to_x = number(p.get("to_x"))
                to_y = number(p.get("to_y"))
                rows = (
                    [get_object(scene, p.get("wall_id"), "walls")]
                    if action == "move-endpoint"
                    else list(scene.elements.filter(kind="walls"))
                )
                endpoint = p.get("endpoint")
                if action == "move-endpoint" and endpoint not in (1, 2):
                    raise MapError("Invalid endpoint.")
                from_x = number(p.get("from_x", 0))
                from_y = number(p.get("from_y", 0))
                for obj in rows:
                    data = deepcopy(obj.data)
                    changed = False
                    for n in (1, 2):
                        if (action == "move-endpoint" and n == endpoint) or (
                            action == "move-node"
                            and math.hypot(
                                data[f"x{n}"] - from_x, data[f"y{n}"] - from_y
                            )
                            <= 1
                        ):
                            data[f"x{n}"] = to_x
                            data[f"y{n}"] = to_y
                            changed = True
                    if changed:
                        obj.data = wall(data)
                        obj.version += 1
                        obj.save()
            elif area == "walls" and action == "split":
                obj = get_object(scene, p.get("wall_id"), "walls")
                if obj.data["kind"] != "wall":
                    raise MapError("Doors cannot be split.")
                x, y = number(p.get("x")), number(p.get("y"))
                w = obj.data
                dx = w["x2"] - w["x1"]
                dy = w["y2"] - w["y1"]
                t = ((x - w["x1"]) * dx + (y - w["y1"]) * dy) / (dx * dx + dy * dy)
                if not 0.001 < t < 0.999:
                    raise MapError("Choose a point inside the wall.")
                x = w["x1"] + t * dx
                y = w["y1"] + t * dy
                SceneObject.objects.create(
                    scene=scene, kind="walls", data=wall({**w, "x1": x, "y1": y})
                )
                obj.data = wall({**w, "x2": x, "y2": y})
                obj.version += 1
                obj.save()
            else:
                raise MapError("Unknown object command.")
        elif area == "light-selection":
            if action == "clear":
                scene.elements.filter(kind="lights").delete()
            elif action == "paste":
                rows = p.get("effects")
                if (
                    not isinstance(rows, list)
                    or not 1 <= len(rows) <= 500
                    or scene.elements.count() + len(rows) > 5000
                ):
                    raise MapError("Invalid light selection.")
                result = {"effects": []}
                for row in rows:
                    if not isinstance(row, dict) or row.get("kind") != "light":
                        raise MapError("Invalid light selection.")
                    obj = SceneObject.objects.create(
                        scene=scene, kind="lights", data=light(row.get("data"))
                    )
                    result["effects"].append({"kind": "light", "id": str(obj.pk)})
            elif action in ("transform", "delete"):
                refs = p.get("effects")
                if not isinstance(refs, list) or not 1 <= len(refs) <= 500:
                    raise MapError("Invalid light selection.")
                for ref in refs:
                    if not isinstance(ref, dict) or ref.get("kind") != "light":
                        raise MapError("Invalid light selection.")
                    obj = get_object(scene, ref.get("id"), "lights")
                    if action == "delete":
                        obj.delete()
                    else:
                        obj.data = light(
                            {
                                **obj.data,
                                "x": obj.data["x"] + number(p.get("dx", 0)),
                                "y": obj.data["y"] + number(p.get("dy", 0)),
                                "rotation": (
                                    obj.data["rotation"] + number(p.get("rotation", 0))
                                )
                                % 360,
                            }
                        )
                        obj.version += 1
                        obj.save()
            else:
                raise MapError("Unknown light selection command.")
        elif area == "wall-selection":
            if action == "clear":
                scene.elements.filter(kind="walls").delete()
            elif action == "paste":
                rows = p.get("walls")
                if not isinstance(rows, list) or not 1 <= len(rows) <= 500:
                    raise MapError("Invalid wall selection.")
                if scene.elements.count() + len(rows) > 5000:
                    raise MapError("Scene object limit reached.")
                result = {
                    "walls": [
                        str(
                            SceneObject.objects.create(
                                scene=scene, kind="walls", data=wall(w)
                            ).pk
                        )
                        for w in rows
                    ]
                }
            elif action in ("move", "delete"):
                ids = p.get("wall_ids")
                if not isinstance(ids, list) or not 1 <= len(ids) <= 500:
                    raise MapError("Invalid wall selection.")
                rows = [get_object(scene, pk, "walls") for pk in ids]
                for obj in rows:
                    if action == "delete":
                        obj.delete()
                    else:
                        dx, dy = number(p.get("dx")), number(p.get("dy"))
                        obj.data = wall(
                            {
                                **obj.data,
                                **{
                                    f"{axis}{n}": obj.data[f"{axis}{n}"]
                                    + (dx if axis == "x" else dy)
                                    for n in (1, 2)
                                    for axis in ("x", "y")
                                },
                            }
                        )
                        obj.version += 1
                        obj.save()
            else:
                raise MapError("Unknown wall selection command.")
        elif area == "lighting" and action == "update":
            env.lighting = {
                "mode": choice(p.get("mode"), {"none", "manual", "dynamic"}),
                "darkness": number(p.get("darkness", 1), 0, 1),
                "lights_out": boolean(p.get("lights_out", True)),
            }
        elif area == "fog":
            fog = {
                "enabled": False,
                "baseline": "reveal_all",
                "ops": [],
                "version": 1,
                **env.fog,
            }
            expected = p.get('expected_version')
            if (settings.FOG_REQUIRE_EXPECTED_VERSION or expected is not None) and (
                type(expected) is not int or expected != fog['version']
            ):
                raise MapError('Manual lighting changed. Refresh and try again.', 'conflict')
            if action == "enable":
                fog.update(
                    enabled=True,
                    baseline=choice(p.get("initial"), {"hide_all", "reveal_all"}),
                    ops=[],
                )
            elif action == "disable":
                fog["enabled"] = False
            elif action == "reset":
                fog.update(
                    baseline=choice(p.get("to"), {"hide_all", "reveal_all"}), ops=[]
                )
            elif action == "paint":
                if not fog["enabled"]:
                    raise MapError("Manual lighting is not active in this scene.")
                ops = p.get("ops")
                if not isinstance(ops, list) or not 1 <= len(ops) <= settings.FOG_MAX_OPS_PER_COMMAND:
                    raise MapError("Invalid brush stroke.")
                if len(fog["ops"]) + len(ops) > 10000:
                    raise MapError("Reset manual lighting before adding more strokes.")
                for op in ops:
                    if not isinstance(op, dict):
                        raise MapError("Invalid brush stroke.")
                    mode = choice(op.get("mode"), {"hide", "reveal"})
                    shape = choice(op.get("shape"), {"circle", "square", "polygon"})
                    geom = op.get("geom")
                    if not isinstance(geom, dict):
                        raise MapError("Invalid brush geometry.")
                    if shape == "polygon":
                        points = geom.get("points_cells")
                        if (
                            not isinstance(points, list)
                            or not 3 <= len(points) <= settings.FOG_MAX_POLYGON_POINTS
                            or any(
                                not isinstance(pt, list) or len(pt) != 2
                                for pt in points
                            )
                        ):
                            raise MapError("Invalid brush polygon.")
                        clean = {
                            "points_cells": [[number(x, -settings.FOG_MAX_COORDINATE_ABS, settings.FOG_MAX_COORDINATE_ABS), number(y, -settings.FOG_MAX_COORDINATE_ABS, settings.FOG_MAX_COORDINATE_ABS)] for x, y in points]
                        }
                    else:
                        radius = "radius_cells" if shape == "circle" else "size_cells"
                        clean = {
                            k: number(geom.get(k), -settings.FOG_MAX_COORDINATE_ABS, settings.FOG_MAX_COORDINATE_ABS)
                            for k in ("center_x_cells", "center_y_cells")
                        }
                        clean[radius] = number(geom.get(radius), 0.01, 1000)
                    fog["ops"].append({"mode": mode, "shape": shape, "geom": clean})
            else:
                raise MapError("Unknown manual lighting command.")
            fog["version"] += 1
            env.fog = fog
        else:
            raise MapError("Unknown scene area.")
    env.version += 1
    env.save()
    return result
