"""Authoritative scene token commands and ephemeral, recipient-filtered motion."""

import itertools
import uuid
from copy import deepcopy

from django.conf import settings
from django.db import transaction

from gravewright.actors import services as actors
from gravewright.campaigns.models import Campaign
from gravewright.journals.services import identifier, member
from gravewright.maps import services as maps
from gravewright.maps.models import Receipt
from gravewright.maps.objects import boolean, choice, number

from .models import Token


def control(row, who):
    return actors.access(row.actor, who, True)


def get(value, who):
    t = (
        Token.objects.select_related("actor", "scene")
        .filter(pk=identifier(value), scene__campaign_id=who.campaign_id)
        .first()
    )
    if not t:
        raise maps.MapError("Token not found.", "not_found")
    maps.scene(t.scene_id, who)
    if t.hidden and who.role != "gm":
        raise maps.MapError("Token not found.", "not_found")
    return t


def data(t):
    """Resolve the authoritative sheet source for a linked or snapshot token."""
    return t.actor.data if t.linked else t.snapshot


def project(t, who):
    """Expose geometry and only the bars, names and conditions this member sees."""
    sheet = data(t)
    config = sheet["token"]
    gm = who.role == "gm"
    own = control(t, who)
    bars = {
        k: {**v, "color": ("#4caf50" if k == "bar_1" else "#3b82f6")}
        for k, v in sheet["bars"].items()
        if gm or own or config["display"].get(k, True)
    }
    return {
        "id": str(t.pk),
        "mapId": str(t.scene_id),
        "actorId": str(t.actor_id),
        "linkMode": "linked" if t.linked else "snapshot",
        "gridX": t.grid_x,
        "gridY": t.grid_y,
        "cells": config["size"],
        "heightCells": config["size"],
        "name": (t.actor.name if t.linked else config.get("name", t.actor.name))
        if gm or own or config["display"].get("name", True)
        else "",
        "imageUrl": actors.image_url(t.actor, "token")
        or actors.image_url(t.actor, "portrait"),
        "version": t.version,
        "hidden": t.hidden,
        "locked": t.locked,
        "rotation": t.rotation,
        "elevation": t.elevation,
        "disposition": t.disposition,
        "canControl": own,
        "canOpenSheet": actors.access(t.actor, who),
        "visionEnabled": t.vision_enabled,
        "visionRange": t.vision_range,
        "bars": bars,
        "conditions": [
            deepcopy(c) for c in t.conditions if gm or c["visible_to"] == "everyone"
        ],
    }


def rows(scene, who):
    return [
        project(t, who)
        for t in scene.tokens.select_related("actor").prefetch_related("actor__assets")
        if not t.hidden or who.role == "gm"
    ]


def state(campaign, user, map_id):
    who = member(campaign, user)
    scene = maps.scene(map_id, who)
    return {"mapId": str(scene.pk), "tokens": rows(scene, who)}


def geometry(scene):
    s = {**maps.DEFAULTS, **scene.settings}
    scale = s["imageScale"]
    return (
        s["gridSize"] * scale,
        s["gridOffsetX"] * scale,
        s["gridOffsetY"] * scale,
        scene.width,
        scene.height,
    )


def vision(scene, who):
    cell, ox, oy, _, _ = geometry(scene)
    return (
        [
            {
                "x": ox + (t.grid_x + data(t)["token"]["size"] / 2) * cell,
                "y": oy + (t.grid_y + data(t)["token"]["size"] / 2) * cell,
                "radius": t.vision_range * cell,
                "elevation": t.elevation,
            }
            for t in scene.tokens.select_related("actor")
            if t.vision_enabled and not t.hidden and control(t, who)
        ]
        if who.role != "gm"
        else []
    )


def position(t, x, y):
    x = number(x, 0)
    y = number(y, 0)
    cell, ox, oy, w, h = geometry(t.scene)
    size = data(t)["token"]["size"]
    if x > max(0, (w - ox) / cell - size) or y > max(0, (h - oy) / cell - size):
        raise maps.MapError("Token is outside the map.")
    return x, y


def blocked(t, a, b, walls=None):
    cell, ox, oy, _, _ = geometry(t.scene)
    size = data(t)["token"]["size"]
    ax = ox + (a[0] + size / 2) * cell
    ay = oy + (a[1] + size / 2) * cell
    rx = (b[0] - a[0]) * cell
    ry = (b[1] - a[1]) * cell
    for obj in walls if walls is not None else t.scene.elements.filter(kind="walls"):
        w = obj.data
        if (
            w.get("movement_behavior") == "pass"
            or (w["kind"] == "door" and w["door_state"] == "open")
            or (
                w.get("vertical_bottom") is not None
                and t.elevation < w["vertical_bottom"]
            )
            or (w.get("vertical_top") is not None and t.elevation > w["vertical_top"])
        ):
            continue
        sx = w["x2"] - w["x1"]
        sy = w["y2"] - w["y1"]
        den = rx * sy - ry * sx
        if abs(den) < 1e-9:
            continue
        qx = w["x1"] - ax
        qy = w["y1"] - ay
        if 0 <= (qx * sy - qy * sx) / den <= 1 and 0 <= (qx * ry - qy * rx) / den <= 1:
            return True
    return False


def movement(t, who, raw, start=None, limit=512, walls=None):
    """Validate control, revision, bounds and path collisions without saving a move."""
    if not control(t, who) or t.locked:
        raise maps.MapError("Token is locked or not controlled.", "forbidden")
    actors.revision(t, raw.get("expectedVersion", raw.get("version")))
    end = position(t, raw.get("gridX"), raw.get("gridY"))
    path = raw.get("path", [])
    if not isinstance(path, list) or len(path) > limit:
        raise maps.MapError("Invalid movement path.")
    points = [start or (t.grid_x, t.grid_y)]
    for p in path:
        if isinstance(p, dict):
            points.append(position(t, p.get("gridX"), p.get("gridY")))
        elif isinstance(p, list) and len(p) == 2:
            points.append(position(t, *p))
        else:
            raise maps.MapError("Invalid movement path.")
    points.append(end)
    cached_walls = (
        list(t.scene.elements.filter(kind="walls"))
        if who.role != "gm" and walls is None
        else []
    )
    if who.role != "gm" and any(
        blocked(t, a, b, walls if walls is not None else cached_walls)
        for a, b in itertools.pairwise(points)
    ):
        raise maps.MapError("Movement blocked by a wall.", "blocked")
    return end


@transaction.atomic
def command(campaign, user, action, raw, request_id):
    """Persist changes once; receipt replays rebuild the current visible token state."""
    Campaign.objects.select_for_update().get(pk=campaign)
    who = member(campaign, user)
    from gravewright.journals.services import writable
    writable(who)
    if not isinstance(raw, dict):
        raise maps.MapError("Invalid token command.")
    scene = maps.scene(raw.get("mapId"), who)
    request_id = identifier(request_id)
    previous = Receipt.objects.filter(
        campaign_id=campaign, user_id=user, request_id=request_id
    ).first()
    if previous:
        visible = rows(scene, who)
        return {
            "tokens": visible,
            "createdIds": [
                i
                for i in previous.result.get("createdIds", [])
                if i in {t["id"] for t in visible}
            ],
        }
    created = []
    if action == "place":
        maps.manage(who)
        actor = actors.get(raw.get("actorId"), who)
        existing = list(actor.tokens.all())
        linked = not existing
        for t in existing:
            if t.linked:
                t.snapshot = deepcopy(actor.data)
                t.snapshot["token"]["name"] = actor.name
                t.linked = False
                t.version += 1
                t.save()
        snapshot = deepcopy(actor.data)
        snapshot["token"]["name"] = actor.name
        t = Token(
            scene=scene, actor=actor, linked=linked, snapshot={} if linked else snapshot
        )
        t.grid_x, t.grid_y = position(t, raw.get("gridX"), raw.get("gridY"))
        t.save()
        created = [str(t.pk)]
    elif action == "move":
        t = get(raw.get("id"), who)
        if t.scene_id != scene.pk:
            raise maps.MapError("Token is not in this scene.")
        before=(t.grid_x,t.grid_y,t.elevation)
        t.grid_x, t.grid_y = movement(t, who, raw)
        t.version += 1
        t.save()
        from gravewright.maps.zones import movement_events
        movement_events(scene,t,before)
    else:
        ids = raw.get("tokenIds")
        if (
            not isinstance(ids, list)
            or not 1 <= len(ids) <= 100
            or len(set(map(str, ids))) != len(ids)
        ):
            raise maps.MapError("Invalid token selection.")
        if action == "duplicate" and len(ids) > settings.TOKEN_CREATE_MANY_MAX:
            raise maps.MapError("Token creation limit exceeded.")
        selected = [get(i, who) for i in ids]
        if any(t.scene_id != scene.pk for t in selected):
            raise maps.MapError("Token is not in this scene.")
        rotate = (
            action == "configure"
            and isinstance(raw.get("values"), dict)
            and set(raw["values"]) == {"rotation"}
        )
        if not rotate:
            maps.manage(who)
        for t in selected:
            if action == "remove":
                t.delete()
                continue
            if action == "duplicate":
                snapshot = deepcopy(data(t))
                snapshot["token"]["name"] = snapshot["token"].get("name", t.actor.name)
                t.pk = uuid.uuid4()
                t.linked = False
                t.snapshot = snapshot
                t.version = 1
                t.sheet_version = 1
                cell, ox, oy, w, h = geometry(scene)
                size = snapshot["token"]["size"]
                t.grid_x = min(t.grid_x + 1, max(0, (w - ox) / cell - size))
                t.grid_y = min(t.grid_y + 1, max(0, (h - oy) / cell - size))
                created.append(str(t.pk))
            elif action == "hidden":
                t.hidden = boolean(raw.get("hidden"))
            elif action == "vision":
                t.vision_enabled = boolean(raw.get("enabled"))
                t.vision_range = number(raw.get("range"), 0)
            elif action == "configure":
                if len(selected) != 1 or not control(t, who):
                    raise maps.MapError("Select one controlled token.")
                actors.revision(t, raw.get("expectedVersion"))
                values = raw.get("values")
                if not isinstance(values, dict) or set(values) - {
                    "rotation",
                    "elevation",
                    "locked",
                    "disposition",
                }:
                    raise maps.MapError("Invalid token configuration.")
                for k, v in values.items():
                    setattr(
                        t,
                        k,
                        boolean(v)
                        if k == "locked"
                        else choice(v, {"friendly", "neutral", "hostile", "unknown"})
                        if k == "disposition"
                        else number(v) % 360
                        if k == "rotation"
                        else number(v),
                    )
            elif action == "condition-add":
                if len(t.conditions) >= 100:
                    raise maps.MapError("Too many conditions.")
                t.conditions.append(
                    {
                        "condition_id": uuid.uuid4().hex,
                        "label": maps.title(raw.get("label")),
                        "kind": choice(
                            raw.get("kind"), {"neutral", "positive", "negative"}
                        ),
                        "visible_to": choice(raw.get("visibility"), {"everyone", "gm"}),
                    }
                )
            elif action == "condition-remove":
                t.conditions = [
                    c
                    for c in t.conditions
                    if c["condition_id"] != raw.get("conditionId")
                ]
            else:
                raise maps.MapError("Unknown token command.")
            t.version += 1
            t.save()
    result = {"tokens": rows(scene, who), "createdIds": created}
    Receipt.objects.create(
        campaign_id=campaign, user_id=user, request_id=request_id, result={"createdIds": created}
    )
    from gravewright.realtime.dispatch import changed
    changed(campaign,user,'tokens',action,request_id,result)
    return result


def preview(campaign, user, map_id, positions, previous):
    """Validate transient drag coordinates without changing persisted positions."""
    who = member(campaign, user)
    scene = maps.scene(map_id, who)
    if not isinstance(positions, list) or not 1 <= len(positions) <= 100:
        raise maps.MapError("Invalid drag preview.")
    result = []
    seen = set()
    available = {str(t.pk): t for t in scene.tokens.select_related("actor")}
    walls = list(scene.elements.filter(kind="walls")) if who.role != "gm" else []
    for p in positions:
        if not isinstance(p, dict):
            raise maps.MapError("Invalid drag preview.")
        t = available.get(str(identifier(p.get("id"))))
        if t is None or (t.hidden and who.role != "gm"):
            raise maps.MapError("Token not available.")
        t.scene = scene
        if t.scene_id != scene.pk or t.pk in seen:
            raise maps.MapError("Invalid drag scope.")
        seen.add(t.pk)
        x, y = movement(t, who, p, previous.get(str(t.pk)), 16, walls)
        result.append({"id": str(t.pk), "gridX": x, "gridY": y, "version": t.version})
    return result


def motion_for(campaign, user, map_id, positions):
    """A preview carries only coordinates, never another recipient's sheet projection."""
    who = member(campaign, user)
    scene = maps.scene(map_id, who)
    queryset = scene.tokens.filter(pk__in=[p["id"] for p in positions])
    if who.role != "gm":
        queryset = queryset.filter(hidden=False)
    versions = {
        str(pk): version for pk, version in queryset.values_list("pk", "version")
    }
    return [p for p in positions if versions.get(p["id"]) == p["version"]]
