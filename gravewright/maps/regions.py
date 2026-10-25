"""Private region and object-area membership from committed token commands."""

from copy import deepcopy
from contextvars import ContextVar
import uuid
import math

from .models import SceneObject
from .services import MapError
from .zones import Geometry


MAX_REGIONS = 128
MAX_PRESENCE_EVENTS = 256
FILTER_DISPOSITIONS = frozenset({"friendly", "neutral", "hostile", "unknown"})
FILTER_VISIBILITY = frozenset({"any", "visible", "hidden"})
_suppressed = ContextVar("presence_suppressed_regions", default=None)


def clean_filters(raw, *, campaign_id=None, scene_id=None):
    """Normalize authored selectors; absent resources remain inert references."""
    if not isinstance(raw, dict) or set(raw) - {"tokenIds", "actorIds", "dispositions", "visibility"}:
        raise MapError("Invalid region filters.")
    result = {"tokenIds": [], "actorIds": [], "dispositions": [], "visibility": raw.get("visibility", "any")}
    for key in ("tokenIds", "actorIds"):
        values = raw.get(key, [])
        if not isinstance(values, list) or len(values) > 64:
            raise MapError("Invalid region filters.")
        try:
            if any(not isinstance(value, str) for value in values):
                raise ValueError
            result[key] = [str(uuid.UUID(value)) for value in values]
        except (ValueError, TypeError, AttributeError):
            raise MapError("Invalid region filters.") from None
        if len(set(result[key])) != len(values):
            raise MapError("Invalid region filters.")
    dispositions = raw.get("dispositions", [])
    if (not isinstance(dispositions, list) or len(dispositions) > 4
            or any(not isinstance(value, str) or value not in FILTER_DISPOSITIONS for value in dispositions)
            or len(set(dispositions)) != len(dispositions)
            or not isinstance(result["visibility"], str) or result["visibility"] not in FILTER_VISIBILITY):
        raise MapError("Invalid region filters.")
    result["dispositions"] = list(dispositions)
    if campaign_id is not None:
        from gravewright.actors.models import Actor
        from gravewright.tokens.models import Token
        actors = Actor.objects.filter(pk__in=result["actorIds"])
        tokens = Token.objects.filter(pk__in=result["tokenIds"])
        if (actors.exclude(campaign_id=campaign_id).exists()
                or tokens.exclude(scene__campaign_id=campaign_id).exists()
                or scene_id is not None and tokens.exclude(scene_id=scene_id).exists()):
            raise MapError("Choose region filters from this campaign and scene.")
    return result


def token_filter(filters=None):
    """Compile one region's AND/OR predicates once per occupancy pass."""
    filters = filters or {}
    tokens, actors = set(filters.get("tokenIds", [])), set(filters.get("actorIds", []))
    dispositions, visibility = set(filters.get("dispositions", [])), filters.get("visibility", "any")
    return lambda token: ((not tokens or str(token.pk) in tokens)
        and (not actors or str(token.actor_id) in actors)
        and (not dispositions or token.disposition in dispositions)
        and (visibility == "any" or token.hidden == (visibility == "hidden")))


def presence_suppressed(row):
    """Runtime presence changes suppress only this command's remaining events."""
    suppressed = _suppressed.get()
    return suppressed is not None and str(row.pk) in suppressed


def set_enabled(scene, row, enabled):
    """Mutate a runtime-owned row in place; its caller persists atomically.

    This controls presence only. Signals and already scheduled continuations
    keep their existing lifecycle. Enabling establishes a quiet baseline.
    """
    if row.scene_id != scene.pk or row.kind != "zones" or not isinstance(row.data.get("region"), dict):
        raise MapError("Choose a presence region.")
    if type(enabled) is not bool:
        raise MapError("Invalid region enabled state.")
    if row.data["enabled"] == enabled:
        return False
    row.data["enabled"] = enabled
    rebaseline_region(scene, row)
    return True


def rebaseline_region(scene, row):
    """Quietly synchronize a runtime-owned region after a configuration change."""
    if row.scene_id != scene.pk or row.kind != "zones" or not isinstance(row.data.get("region"), dict):
        raise MapError("Choose a presence region.")
    baseline(scene, [row])
    if (suppressed := _suppressed.get()) is not None:
        suppressed.add(str(row.pk))


def authentic_context(who, row, token, *, token_id, presence, count):
    """Identity comes from validated server objects, never token payload fields."""
    return {"userId": str(who.user_id), "userName": who.user.name,
            "sourceId": str(row.pk), "tokenId": token_id, "actorId": str(token.actor_id),
            "presence": presence, "count": count}


def projection(data):
    """GM display keeps counts, not the internal token membership ledger."""
    result = deepcopy(data)
    result.pop("areaPresence", None)
    if isinstance(result.get("region"), dict):
        region = result["region"]
        result["region"] = {"name": region["name"], "state": region["state"],
                            "count": len(region.get("occupants", [])),
                            **({"filters": deepcopy(region["filters"])} if "filters" in region else {})}
    return result


def shape(data):
    return {**data, "vertical_bottom": data["vertical"]["bottom"],
            "vertical_top": data["vertical"]["top"]}


def object_area(row):
    """Only authored image-area listeners need a private membership ledger."""
    from .blueprints import has_event_path
    return (row.kind == "images"
            and any(isinstance(row.data.get(kind), dict) for kind in ("lever", "torch"))
            and any(has_event_path(row.data.get("blueprint"), event)
                    for event in ("presence:enter", "presence:exit")))


def presence_rows(scene):
    """Bound the active listeners, keeping ordinary artwork outside the pass."""
    from django.db.models import Q
    candidates = scene.elements.filter(Q(kind="zones", data__region__isnull=False)
        | Q(kind="images", data__blueprint__isnull=False)).order_by("created_at", "id")
    return [row for row in candidates if row.kind == "zones" or object_area(row)]


def object_shape(data):
    """Use an explicit circle or the authored box, independent of fitted art."""
    if "presenceRadius" in data:
        return {"geometry": {"shape": "circle", "x": data["x"], "y": data["y"],
                             "radius": data["presenceRadius"]}, "vertical_bottom": None, "vertical_top": None}
    authored = data.get("torch", data.get("lever", {}))
    width = authored.get("width", data["natural_width"] * data["scale"])
    height = authored.get("height", data["natural_height"] * data["scale"])
    x, y = data["x"], data["y"]
    radians = math.radians(data.get("rotation", 0))
    cosine, sine = math.cos(radians), math.sin(radians)
    if data.get("rotation", 0) % 180 == 0:
        geometry = {"shape": "rect", "x": x - width / 2, "y": y - height / 2,
                    "width": width, "height": height}
    else:
        geometry = {"shape": "polygon", "points": [
            {"x": x + dx * cosine - dy * sine, "y": y + dx * sine + dy * cosine}
            for dx, dy in ((-width / 2, -height / 2), (width / 2, -height / 2),
                           (width / 2, height / 2), (-width / 2, height / 2))]}
    return {"geometry": geometry, "vertical_bottom": None, "vertical_top": None}


def copy_object_radius(result, raw, previous=None):
    """Optional custom presence radius, in native scene pixels; null resets it."""
    value = raw.get("presenceRadius", (previous or {}).get("presenceRadius"))
    if value is not None:
        from .objects import number
        if not any(isinstance(result.get(key), dict) for key in ("lever", "torch")):
            raise MapError("Choose a Smart Object before setting its activation area.")
        result["presenceRadius"] = number(value, .001, 1_000_000)
    return result


def rebaseline_object(scene, row):
    """Quiet image edits update presence without running gameplay events."""
    if row.scene_id != scene.pk or row.kind != "images":
        raise MapError("Choose an object from this scene.")
    if object_area(row):
        if sum(candidate.pk != row.pk for candidate in presence_rows(scene)) >= MAX_REGIONS:
            raise MapError("The scene has too many presence regions.")
        baseline(scene, [row])
    else:
        row.data.pop("areaPresence", None)
    if (suppressed := _suppressed.get()) is not None:
        suppressed.add(str(row.pk))


def token_point(scene, token, position=None, *, cell=None):
    from gravewright.tokens.services import geometry, presentation
    actual_cell, ox, oy, _, _ = geometry(scene)
    cell = actual_cell if cell is None else cell
    x, y, elevation = position or (token.grid_x, token.grid_y, token.elevation)
    half = presentation(token)["token"]["size"] / 2
    return ox + (x + half) * cell, oy + (y + half) * cell, elevation


def baseline(scene, rows=None, *, cell=None):
    """Editing or importing geometry establishes occupancy without firing events.

    Callers save the supplied rows with the rest of their atomic operation.
    Hidden tokens still have physical presence; only GMs receive the counts.
    """
    rows = list(rows) if rows is not None else presence_rows(scene)
    active = []
    for row in rows:
        if row.kind == "zones" and isinstance(row.data.get("region"), dict) or object_area(row):
            active.append(row)
        else:
            row.data.pop("areaPresence", None)
    rows = active
    if len(rows) > MAX_REGIONS:
        raise MapError("The scene has too many presence regions.")
    if not rows:
        return rows
    points = [(str(token.pk), token, token_point(scene, token, cell=cell))
              for token in scene.tokens.select_related("actor")]
    for row in rows:
        if row.kind == "images":
            zone = object_shape(row.data)
            row.data["areaPresence"] = {"occupants": sorted(key for key, token, point in points
                if Geometry.contains(zone, *point))}
            continue
        zone = shape(row.data)
        accepts = token_filter(row.data["region"].get("filters"))
        occupants = sorted(key for key, token, point in points
                           if row.data["enabled"] and accepts(token) and Geometry.contains(zone, *point))
        row.data["region"].update(occupants=occupants, state="occupied" if occupants else "empty")
        if "arrivalGates" in row.data["region"]:
            inside = {key for key, token, point in points if Geometry.contains(zone, *point)}
            row.data["region"]["arrivalGates"] = [key for key in row.data["region"]["arrivalGates"] if key in inside]
    return rows


def rebaseline(scene):
    """Persist a configuration baseline without running presence graphs."""
    rows = presence_rows(scene)
    before = {row.pk: deepcopy(row.data) for row in rows}
    for row in baseline(scene, rows):
        if row.data != before[row.pk]:
            row.version += 1
            row.save(update_fields=["data", "version"])


def remove_actor_tokens(actors, who):
    """Release physical presence before an actor deletion cascades its tokens."""
    from gravewright.tokens.models import Token
    by_scene = {}
    for token in Token.objects.filter(actor__in=actors).select_related("actor", "scene"):
        scene, changes = by_scene.setdefault(token.scene_id, (token.scene, []))
        changes.append({"token": token, "id": str(token.pk),
                        "before": (token.grid_x, token.grid_y, token.elevation), "after": None})
    for scene, changes in by_scene.values():
        token_events(scene, who, changes)


def token_events(scene, who, changes):
    if not changes:
        return
    marker = _suppressed.set(set()) if _suppressed.get() is None else None
    try:
        from .blueprint_runtime import event_resources
        with event_resources(scene):
            _token_events(scene, who, changes)
    finally:
        if marker is not None:
            _suppressed.reset(marker)


def _token_events(scene, who, changes):
    """Apply one validated command's membership, graphs and effects atomically.

    Regions are evaluated in creation order, then each accepted path in order.
    Crossing a rectangle in one accepted segment enters and leaves it. Preview
    positions never call this function. The token centre determines presence.
    """
    from .blueprint_runtime import automation_paused, operate
    from .blueprint_world import token_relocated
    rows = presence_rows(scene)
    if len(rows) > MAX_REGIONS:
        raise MapError("The scene has too many presence regions.")
    if not rows:
        return
    # Accepted coordinates and token size do not change between listeners. Keep
    # the original change dictionaries for teleport/cancellation bookkeeping.
    paths = []
    for change in changes:
        token, before, after = (change[name] for name in ("token", "before", "after"))
        start = token_point(scene, token, before) if before is not None else None
        finish = token_point(scene, token, after) if after is not None else None
        points = [start] if start is not None else []
        if start is not None and finish is not None:
            for point in change.get("path", []):
                x, y = (point["gridX"], point["gridY"]) if isinstance(point, dict) else point
                points.append(token_point(scene, token, (x, y, before[2])))
        if finish is not None:
            points.append(finish)
        paths.append((change, start, finish, points))
    events = 0
    for row in rows:
        if presence_suppressed(row):
            continue
        # Earlier regions may have signalled this region and changed its memory.
        # Refresh before evaluating so its old prefetched data cannot overwrite it.
        try:
            row.refresh_from_db(fields=["data", "version"])
        except SceneObject.DoesNotExist:
            continue
        is_object = row.kind == "images"
        if is_object and not object_area(row):
            continue
        previous = deepcopy(row.data)
        ledger = row.data.setdefault("areaPresence", {"occupants": []}) if is_object else row.data["region"]
        occupants = set(ledger.get("occupants", []))
        zone = object_shape(row.data) if is_object else shape(row.data)
        accepts = token_filter(None if is_object else ledger.get("filters"))
        halted = False

        def synchronize(*, state=True):
            current = row.data.setdefault("areaPresence", {}) if is_object else row.data["region"]
            current["occupants"] = sorted(occupants)
            if not is_object and state:
                current["state"] = "occupied" if occupants else "empty"

        def transition(key, entered, token):
            nonlocal events, halted
            if halted:
                return
            if (key in occupants) == entered:
                return
            events += 1
            if events > MAX_PRESENCE_EVENTS:
                raise MapError("The movement crosses too many presence regions.")
            occupants.add(key) if entered else occupants.discard(key)
            synchronize(state=False)
            target = "occupied" if occupants else "empty"
            if isinstance(row.data.get("blueprint"), dict) and not automation_paused(scene):
                operate(scene, who, row, None if is_object else target, interact=False,
                        presence_event="presence:enter" if entered else "presence:exit",
                        context=authentic_context(who, row, token, token_id=key,
                            presence="enter" if entered else "exit", count=len(occupants)))
                halted = presence_suppressed(row)
                if token_relocated(key) and not change.get("teleport"):
                    # Arrival/departure graphs have already persisted a newer
                    # ledger. Do not restore this command's old movement path.
                    try:
                        row.refresh_from_db(fields=["data", "version"])
                    except SceneObject.DoesNotExist:
                        halted = True
                        return
                    occupants.clear()
                    occupants.update(row.data.get("areaPresence" if is_object else "region", {}).get("occupants", []))
            elif not is_object:
                row.data["region"]["state"] = target

        for change, start, finish, points in paths:
            if halted:
                break
            token, key, before, after = (change[name] for name in ("token", "id", "before", "after"))
            if token_relocated(key) and not change.get("teleport"):
                continue
            if not is_object and "arrivalGates" in row.data["region"] and (after is None
                    or not Geometry.contains(zone, *finish)):
                row.data["region"]["arrivalGates"] = [value for value in row.data["region"]["arrivalGates"] if value != key]
            if not is_object and not row.data["enabled"] or not accepts(token):
                occupants.discard(key)
                continue
            # A changed token size is a new baseline, not a synthetic movement.
            was = start is not None and Geometry.contains(zone, *start)
            occupants.add(key) if was else occupants.discard(key)
            synchronize()
            if after is None:
                transition(key, False, token)
                continue
            if start is None:
                transition(key, Geometry.contains(zone, *finish), token)
                continue
            for a, b in zip(points, points[1:]):
                if halted or token_relocated(key) and not change.get("teleport"):
                    break
                was, now = Geometry.contains(zone, *a), Geometry.contains(zone, *b)
                within = ((zone["vertical_bottom"] is None or b[2] >= zone["vertical_bottom"])
                          and (zone["vertical_top"] is None or b[2] <= zone["vertical_top"]))
                if was != now:
                    transition(key, now, token)
                elif not was and within and not change.get("teleport") and Geometry.crosses(zone, a, b, b[2]):
                    transition(key, True, token)
                    transition(key, False, token)
        if halted:
            continue
        synchronize()
        if row.data != previous:
            # A second token changes membership even when its state stays occupied.
            current = SceneObject.objects.filter(pk=row.pk).first()
            if current is None:
                continue
            if current.data != row.data:
                row.version = current.version + 1
                row.save(update_fields=["data", "version"])
