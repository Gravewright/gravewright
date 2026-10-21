"""Authorized presentations and transactional, same-scene token transport."""

from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
import math
import uuid

from django.db import transaction
from django.db.models import F

from .services import MapError


@dataclass
class WorldRequest:
    request_id: str
    teleported: set = field(default_factory=set)
    pending: deque = field(default_factory=deque)
    changed: dict = field(default_factory=dict)
    material_crops: dict = field(default_factory=dict)
    flushing: bool = False


_request = ContextVar("blueprint_world_request", default=None)


@contextmanager
def world_request(request_id):
    active = _request.get()
    if active is not None and active.request_id == str(request_id):
        yield active
        return
    state = WorldRequest(str(request_id))
    marker = _request.set(state)
    try:
        yield state
        from gravewright.realtime.dispatch import changed
        for scene, who in state.changed.values():
            teleports = [{"id": str(token_id), "version": version} for token_id, version in
                         scene.tokens.filter(pk__in=state.teleported).values_list("pk", "version")]
            changed(scene.campaign_id, who.user_id, "tokens", "teleport", request_id,
                    {"mapId": str(scene.pk), "teleports": teleports})
    finally:
        _request.reset(marker)


def world_operation(function):
    """Run arrivals only after an operation has persisted its native object cache."""
    @wraps(function)
    def execute(*args, **kwargs):
        from .blueprint_delays import current_request_id
        active = _request.get()
        with world_request(active.request_id if active is not None else current_request_id()) as state:
            result = function(*args, **kwargs)
            if not state.flushing:
                state.flushing = True
                try:
                    from .regions import token_events
                    while state.pending:
                        scene, who, change = state.pending.popleft()
                        _gate_arrivals(scene, change["token"])
                        token_events(scene, who, [change])
                finally:
                    state.flushing = False
            return result
    return execute


def token_relocated(token_id):
    active = _request.get()
    return active is not None and str(token_id) in active.teleported


def material_crop(asset_id, load):
    """Cache bounded crop metadata per command, never decoded images or bytes."""
    active, key = _request.get(), str(asset_id)
    if active is not None and key in active.material_crops:
        return list(active.material_crops[key])
    value = load()
    if active is not None:
        if len(active.material_crops) >= 256:
            active.material_crops.pop(next(iter(active.material_crops)))
        active.material_crops[key] = tuple(value)
    return list(value)


def presentation_catalog(who):
    from gravewright.campaigns.models import Membership
    from gravewright.journals.models import Journal
    from .services import manage
    manage(who)
    return {
        "users": [{"id": str(row.user_id), "name": row.user.name, "role": row.role}
                  for row in Membership.objects.filter(campaign_id=who.campaign_id, user__is_active=True)
                  .select_related("user").order_by("user__name", "user_id")],
        "handouts": [{"id": str(row.pk), "name": row.title, "type": row.type}
                     for row in Journal.objects.filter(campaign_id=who.campaign_id).order_by("title", "id")],
    }


def presentation_for(campaign_id, user_id, payload):
    """Recheck the recipient at delivery without creating any resource grant."""
    from gravewright.journals import services as journals
    from . import services
    try:
        who = journals.member(campaign_id, user_id)
        services.scene(payload["sceneId"], who)
        if payload["type"] == "roll" and who.role == "streamer":
            return None
        if payload["type"] == "handout":
            journals.get(payload["journalId"], who)
        return payload
    except (journals.JournalError, MapError, KeyError):
        return None


def present(scene, who, node, context):
    """Queue one plain, recipient-filtered presentation after the whole commit."""
    from gravewright.campaigns.models import Membership
    from gravewright.realtime.dispatch import send
    audience = node["audience"]
    members = Membership.objects.filter(campaign_id=scene.campaign_id, user__is_active=True)
    if node["type"] == "requestRoll":
        members = members.exclude(role="streamer")
    if audience["scope"] == "trigger":
        members = members.filter(user_id=context["userId"])
    elif audience["scope"] == "players":
        members = members.exclude(role="gm")
    else:
        members = members.filter(user_id__in=audience["userIds"])
    entry = {"id": str(uuid.uuid4()), "sceneId": str(scene.pk),
             "type": {"showMessage": "message", "showHandout": "handout", "requestRoll": "roll",
                      "cameraFocus": "camera"}[node["type"]]}
    if node["type"] == "showMessage":
        entry["text"] = node["text"]
    elif node["type"] == "showHandout":
        entry["journalId"] = node["journalId"]
    elif node["type"] == "requestRoll":
        entry.update({key: node[key] for key in ("expression", "label", "visibility")})
    else:
        from gravewright.tokens.services import geometry
        cell, ox, oy, width, height = geometry(scene)
        x, y = ox + node["focusX"] * cell, oy + node["focusY"] * cell
        if not 0 <= x <= width or not 0 <= y <= height:
            raise MapError("Camera focus is outside the map.")
        entry.update(x=x, y=y)
    recipients = [str(user_id) for user_id in members.values_list("user_id", flat=True)
                  if presentation_for(scene.campaign_id, user_id, entry) is not None]
    if recipients:
        transaction.on_commit(lambda: send(scene.campaign_id, {"type": "room.automation_presentation",
            "payload": entry, "recipients": recipients}), robust=True)
    return len(recipients)


def set_quest_status(scene, who, node):
    """Execute a GM-authored status command through the owning journal service.

    Saving a Blueprint requires a GM. Its specific quest/status binding is the
    delegated capability; interacting players never receive general journal
    write access. An active campaign GM must still authorize the journal command.
    The caller's map transaction contains its receipt and notifications too.
    """
    from gravewright.campaigns.models import Membership
    from gravewright.journals import services as journals
    from gravewright.journals.models import Journal
    quest = Journal.objects.select_for_update().filter(
        pk=node["journalId"], campaign_id=scene.campaign_id, type="quest").first()
    if quest is None:
        raise MapError("Choose a quest from this campaign.")
    authority = (who if who.role == "gm" else Membership.objects.filter(
        campaign_id=scene.campaign_id, role="gm", user__is_active=True).order_by("id").first())
    if authority is None:
        raise MapError("An active campaign GM is required to update this quest.", "forbidden")
    if isinstance(quest.data, dict) and quest.data.get("status") == node["status"]:
        return {"journalId": str(quest.pk), "status": node["status"], "version": quest.version, "changed": False}
    try:
        result = journals.command(scene.campaign_id, authority.user_id, "status",
            {"journal_id": str(quest.pk), "status": node["status"], "version": quest.version}, uuid.uuid4())
    except journals.JournalError as error:
        raise MapError(str(error), error.code) from None
    return {"journalId": str(quest.pk), "status": node["status"], "version": result["version"], "changed": True}


def _wall_blocks(wall, token, left, top, right, bottom):
    from .zones import Geometry
    data = wall.data
    if (data.get("movement_behavior") == "pass" or data["kind"] == "door" and data["door_state"] == "open"
            or data.get("vertical_bottom") is not None and token.elevation < data["vertical_bottom"]
            or data.get("vertical_top") is not None and token.elevation > data["vertical_top"]):
        return False
    # A wall on the footprint boundary is valid; a segment through its interior is not.
    epsilon = 1e-7
    zone = {"geometry": {"shape": "rect", "x": left + epsilon, "y": top + epsilon,
                        "width": right - left - 2 * epsilon, "height": bottom - top - 2 * epsilon},
            "vertical_bottom": None, "vertical_top": None}
    a, b = (data["x1"], data["y1"]), (data["x2"], data["y2"])
    return (Geometry.contains(zone, *a, token.elevation) or Geometry.contains(zone, *b, token.elevation)
            or Geometry.crosses(zone, a, b, token.elevation))


def _placement(scene, token, region):
    from gravewright.tokens.services import geometry, position, presentation
    cell, ox, oy, width, height = geometry(scene)
    size = presentation(token)["token"]["size"]
    rect = region.data["geometry"]
    first_x, first_y = math.ceil((rect["x"] - ox) / cell), math.ceil((rect["y"] - oy) / cell)
    last_x = min(math.floor((rect["x"] + rect["width"] - ox) / cell - size), math.floor((width - ox) / cell - size))
    last_y = min(math.floor((rect["y"] + rect["height"] - oy) / cell - size), math.floor((height - oy) / cell - size))
    occupants = [(other.grid_x, other.grid_y, presentation(other)["token"]["size"])
                 for other in scene.tokens.exclude(pk=token.pk).select_related("actor")]
    walls = list(scene.elements.filter(kind="walls"))
    attempts = 0
    for y in range(max(0, first_y), last_y + 1):
        for x in range(max(0, first_x), last_x + 1):
            attempts += 1
            if attempts > 40_000 or attempts * max(1, len(occupants) + len(walls)) > 2_000_000:
                raise MapError("The teleport destination has no available placement.")
            try:
                position(token, x, y)
            except MapError:
                continue
            if any(x < px + footprint and x + size > px and y < py + footprint and y + size > py
                   for px, py, footprint in occupants):
                continue
            left, top = ox + x * cell, oy + y * cell
            if any(_wall_blocks(wall, token, left, top, left + size * cell, top + size * cell) for wall in walls):
                continue
            return x, y
    raise MapError("The teleport destination has no available placement.")


def _gate_arrivals(scene, token):
    from .regions import shape, token_point
    from .zones import Geometry
    token_id, point = str(token.pk), token_point(scene, token)
    for arrival in scene.elements.filter(kind="zones", data__region__isnull=False):
        if arrival.data["enabled"] and Geometry.contains(shape(arrival.data), *point):
            gates = arrival.data["region"].setdefault("arrivalGates", [])
            if token_id not in gates:
                gates.append(token_id)
                arrival.version += 1
                arrival.save(update_fields=["data", "version"])


def teleport(scene, who, node, context):
    """Transport only the authenticated trigger token, retaining its identity."""
    from gravewright.tokens import services as tokens
    from .models import SceneObject
    if not context.get("tokenId"):
        raise MapError("Teleport requires the triggering token.")
    state = _request.get()
    if state is None:
        raise MapError("Teleport requires an automation request.")
    token_id = context["tokenId"]
    if token_id in state.teleported:
        return {"skipped": "already-transported", "tokenId": token_id}
    source = SceneObject.objects.filter(pk=context["sourceId"], scene=scene, kind="zones").first()
    if source is not None and token_id in source.data.get("region", {}).get("arrivalGates", []):
        return {"skipped": "arrival-gate", "tokenId": token_id}
    token = tokens.get(token_id, who)
    if token.scene_id != scene.pk or str(token.actor_id) != context.get("actorId"):
        raise MapError("The triggering token is no longer available in this scene.")
    if not tokens.control(token, who) or token.locked:
        raise MapError("Token is locked or not controlled.", "forbidden")
    region = SceneObject.objects.filter(scene=scene, pk=node["destinationId"], kind="zones").first()
    if (region is None or not isinstance(region.data.get("region"), dict) or not region.data["enabled"]
            or region.data["geometry"]["shape"] != "rect"
            or region.data["vertical"]["bottom"] is not None and token.elevation < region.data["vertical"]["bottom"]
            or region.data["vertical"]["top"] is not None and token.elevation > region.data["vertical"]["top"]):
        raise MapError("The teleport destination is unavailable.")
    before = token.grid_x, token.grid_y, token.elevation
    x, y = _placement(scene, token, region)
    if not tokens.Token.objects.filter(pk=token.pk, scene=scene, version=token.version).update(
            grid_x=x, grid_y=y, version=F("version") + 1):
        raise MapError("The triggering token changed. Try again.", "conflict")
    token.grid_x, token.grid_y, token.version = x, y, token.version + 1
    from .zones import movement_events
    movement_events(scene, token, before, teleport=True)
    state.teleported.add(token_id)
    state.pending.append((scene, who, {"token": token, "id": token_id, "before": before,
                                      "after": (x, y, token.elevation), "teleport": True}))
    state.changed[str(scene.pk)] = (scene, who)
    return {"tokenId": token_id, "destinationId": str(region.pk), "gridX": x, "gridY": y}
