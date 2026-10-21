"""Private durable Blueprint waits, resumed inside campaign write transactions."""

from contextlib import contextmanager
from contextvars import ContextVar
from copy import copy, deepcopy
from datetime import timedelta
import hashlib
import json
import uuid

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from gravewright.campaigns.models import Campaign
from gravewright.journals.services import JournalError, member, writable
from .models import AutomationDelay, Scene, SceneObject
from .services import MapError


MAX_SCENE_PENDING = 64
MAX_CAMPAIGN_PENDING = 256
MAX_DELAY_RESUMPTIONS = 32
TERMINAL_HISTORY = 50
_request_id = ContextVar("blueprint_request_id", default=None)
_chain_ordinal = ContextVar("blueprint_chain_ordinal", default=None)


@contextmanager
def automation_request(request_id):
    """Associate waits with the original receipt without retaining request objects."""
    from .blueprint_world import world_request
    request_id = uuid.UUID(str(request_id))
    if _request_id.get() == request_id:
        with world_request(request_id) as world:
            yield world
        return
    token = _request_id.set(request_id)
    ordinal_token = _chain_ordinal.set(0)
    try:
        with world_request(request_id) as world:
            yield world
    finally:
        _chain_ordinal.reset(ordinal_token)
        _request_id.reset(token)


def current_request_id():
    return _request_id.get() or uuid.uuid4()


def next_chain_ordinal():
    """Distinguish root events in one request while keeping retries reproducible."""
    ordinal = _chain_ordinal.get()
    if ordinal is None:
        return 0
    _chain_ordinal.set(ordinal + 1)
    return ordinal


def semantic_hash(blueprint):
    """Fingerprint normalized behavior; canvas positions and retired events do not apply."""
    from .blueprints import clean_blueprint
    value = clean_blueprint(blueprint)
    for graph in value.get("graphs", {}).values():
        for node in graph.get("nodes", []):
            node.pop("x", None)
            node.pop("y", None)
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=True).encode("ascii")).hexdigest()


def _notify(scene):
    from gravewright.realtime.dispatch import send
    event = {"type": "room.automation", "sceneId": str(scene.pk)}
    transaction.on_commit(lambda: send(scene.campaign_id, event), robust=True)


def pending_delays(scene):
    """GM projection. Reads do not claim, cancel or execute any continuation."""
    return [{"id": str(row.pk), "elementId": str(row.element_id), "event": row.event,
             "nodeId": row.node_id, "dueAt": row.due_at.isoformat(),
             "createdAt": row.created_at.isoformat(), "seconds": row.seconds,
             "actor": {"name": row.user.name, "role": row.role},
             **({"kind": "timer", "name": row.name} if row.kind == "timer" else {})}
            for row in AutomationDelay.objects.filter(scene=scene, status="pending")
            .select_related("user")[:MAX_SCENE_PENDING]]


def _finish(row, status, message="", *, now=None):
    row.status, row.message, row.finished_at = status, message[:240], now or timezone.now()
    row.save(update_fields=["status", "message", "finished_at"])
    stale = list(AutomationDelay.objects.filter(scene_id=row.scene_id)
                 .exclude(status="pending").order_by("-finished_at", "-id")
                 .values_list("pk", flat=True)[TERMINAL_HISTORY:])
    if stale:
        AutomationDelay.objects.filter(pk__in=stale).delete()


def _required_elements(blueprint, event, continuation=None):
    """References needed by remaining execution nodes, including their pure inputs."""
    graph = blueprint["graphs"].get(event, {"nodes": [], "edges": []})
    nodes = {node["id"]: node for node in graph["nodes"]}
    wanted = set()
    pending = (list(continuation["pending"]) if continuation is not None else
               [node["id"] for node in graph["nodes"] if node["type"] == "event"])
    visited = set(continuation["visited"]) if continuation is not None else set()
    while pending:
        identifier = pending.pop()
        if identifier in wanted or identifier in visited:
            continue
        wanted.add(identifier)
        pending.extend(edge["to"] for edge in graph["edges"]
                       if edge["from"] == identifier and edge.get("kind") != "data")
        pending.extend(edge["from"] for edge in graph["edges"]
                       if edge["to"] == identifier and edge.get("kind") == "data")
    required = {"elements": {nodes[key]["targetId"] for key in wanted if nodes[key]["type"] == "reference"},
            "lights": {nodes[key]["targetId"] for key in wanted if nodes[key]["type"] in ("light", "lightReference")},
            "sounds": {nodes[key]["trackId"] for key in wanted if nodes[key]["type"] in ("sound", "soundControl", "soundReference")},
            "assets": {nodes[key]["assetId"] for key in wanted if nodes[key]["type"] == "sprite"
                       and nodes[key].get("appearance") == "asset"},
            "handouts": {nodes[key]["journalId"] for key in wanted if nodes[key]["type"] == "showHandout"},
            "quests": {nodes[key]["journalId"] for key in wanted if nodes[key]["type"] == "setQuestStatus"}}
    required["elements"].update(nodes[key]["destinationId"] for key in wanted if nodes[key]["type"] == "teleport")
    required["assets"].update(nodes[key]["assetId"] for key in wanted if nodes[key]["type"] == "setAppearance")
    for key in wanted:
        node = nodes[key]
        if node["type"] == "elementGroup":
            required[{"element": "elements", "light": "lights", "sound": "sounds"}[node["memberType"]]].update(node["targetIds"])
    return required


def invalid_reason(row, element=None):
    """Validate authored identity and required native targets, never rebase it."""
    element = element or SceneObject.objects.filter(pk=row.element_id, scene_id=row.scene_id).first()
    blueprint = element.data.get("blueprint") if element is not None else None
    from .blueprint_events import removed_event
    if removed_event(row.event):
        return "The delayed blueprint event was removed."
    from .blueprints import clean_blueprint
    try:
        blueprint = clean_blueprint(blueprint)
    except MapError:
        return "The delayed blueprint changed."
    if semantic_hash(blueprint) != row.graph_hash:
        return "The delayed blueprint changed."
    continuation = row.data.get("continuation")
    if row.kind == "timer":
        from .blueprint_variables import signal_event
        if row.event != "signal:" + row.name or not signal_event(row.event) or continuation is not None:
            return "The delayed blueprint changed."
    elif row.kind != "delay" or not isinstance(continuation, dict) or row.event not in blueprint.get("graphs", {}):
        return "The delayed blueprint changed."
    from .blueprint_actions import live_objects
    from gravewright.audio.models import Track
    from .models import MapAsset
    from gravewright.journals.models import Journal
    required = _required_elements(blueprint, row.event, continuation)
    # Native validation keeps every authored resource binding campaign-local,
    # including those in other events and before the wait. If one disappears,
    # cancel explicitly rather than failing halfway through a resumed effect.
    nodes = [node for graph in blueprint["graphs"].values() for node in graph["nodes"]]
    required["lights"].update(node["targetId"] for node in nodes if node["type"] == "light")
    required["sounds"].update(node["trackId"] for node in nodes if node["type"] in ("sound", "soundControl"))
    required["assets"].update(entry["assetId"] for entry in [*nodes, *blueprint["states"].values()]
                               if entry.get("appearance") == "asset")
    required["assets"].update(node["assetId"] for node in nodes if node["type"] == "setAppearance")
    resources = {"elements": live_objects(row.scene).exclude(kind="lights"),
                 "lights": SceneObject.objects.filter(scene_id=row.scene_id, kind="lights"),
                 "sounds": Track.objects.filter(campaign_id=row.scene.campaign_id),
                 "assets": MapAsset.objects.filter(campaign_id=row.scene.campaign_id, generated_for__isnull=True),
                 "handouts": Journal.objects.filter(campaign_id=row.scene.campaign_id),
                 "quests": Journal.objects.filter(campaign_id=row.scene.campaign_id, type="quest")}
    if any(identifiers != {str(pk) for pk in resources[kind].filter(pk__in=identifiers).values_list("pk", flat=True)}
           for kind, identifiers in required.items() if identifiers):
        return "A delayed blueprint target is missing."
    return None


def _record_cancelled(row, scene, reason):
    from types import SimpleNamespace
    from .blueprint_runtime import element_state, record_run
    try:
        state = element_state(row.element)
    except (KeyError, TypeError):
        state = None
    record_run(scene, SimpleNamespace(user=row.user, role=row.role), row.element, "cancelled", {
        "requested": None, "stateBefore": state, "stateAfter": state, "events": [],
        "message": reason, "delayId": str(row.pk),
        **({"timerName": row.name} if row.kind == "timer" else {})})


def cancel_invalid_delays(scene):
    """Called once per authored native mutation, outside per-object generation loops."""
    changed = False
    rows = list(AutomationDelay.objects.filter(scene=scene, status="pending").select_related("element"))
    for row in rows:
        reason = invalid_reason(row, row.element)
        if reason:
            _finish(row, "cancelled", reason)
            _record_cancelled(row, scene, reason)
            changed = True
    if changed:
        _notify(scene)


def cancel_owned_delays(scene, element_ids):
    """Record cancellation before an explicit destruction cascades its owners."""
    rows = list(AutomationDelay.objects.select_for_update().filter(
        scene=scene, element_id__in=element_ids, status="pending").select_related("element", "user"))
    for row in rows:
        reason = "The owning element was destroyed."
        _finish(row, "cancelled", reason)
        _record_cancelled(row, scene, reason)
    if rows:
        _notify(scene)
    return len(rows)


def cancel_delay(scene, data):
    from gravewright.journals.services import identifier
    row = AutomationDelay.objects.select_for_update().filter(
        pk=identifier(data.get("delayId")), scene=scene, status="pending").first()
    if row is None or data.get("expectedDueAt") != row.due_at.isoformat():
        raise MapError("This delay changed. Refresh before cancelling it.", "conflict")
    _finish(row, "cancelled", "Cancelled by the GM.")
    _record_cancelled(row, scene, "Cancelled by the GM.")
    _notify(scene)
    return {"delays": pending_delays(scene)}


def _capacity(scene):
    counts = AutomationDelay.objects.filter(status="pending", scene__campaign_id=scene.campaign_id)
    if counts.count() >= MAX_CAMPAIGN_PENDING or counts.filter(scene=scene).count() >= MAX_SCENE_PENDING:
        raise MapError("Too many pending blueprint delays.")


def control_timer(scene, who, element, event, node, *, chain_id, request_id, budget, context=None):
    """Apply a named timer action immediately, in authored execution order.

    The caller holds the campaign lock and owns the write transaction. Starting
    an existing timer preserves its identity, deadline, authority and budget.
    A restart creates a new logical job; Stop does not emit an event.
    """
    existing = AutomationDelay.objects.select_for_update().filter(
        element=element, scene=scene, kind="timer", name=node["name"], status="pending").first()
    if existing is not None and node["action"] == "start":
        return False
    if existing is not None:
        reason = "Restarted by the blueprint timer." if node["action"] == "restart" else "Stopped by the blueprint timer."
        _finish(existing, "cancelled", reason)
        _record_cancelled(existing, scene, reason)
        _notify(scene)
    if node["action"] == "stop":
        return False
    _capacity(scene)
    data = {"budget": deepcopy(budget), "originEvent": event}
    if context is not None:
        data["context"] = deepcopy(context)
    AutomationDelay.objects.create(scene=scene, element=element, user=who.user, role=who.role,
        kind="timer", name=node["name"], chain_id=chain_id, request_id=request_id,
        event="signal:" + node["name"], node_id=node["id"], graph_hash=semantic_hash(element.data["blueprint"]),
        seconds=node["seconds"], due_at=timezone.now() + timedelta(seconds=node["seconds"]), data=data)
    _notify(scene)
    return True


def restart_timer(scene, data):
    """GM compare-and-swap restart without upgrading the scheduled authority."""
    from gravewright.journals.services import identifier
    row = AutomationDelay.objects.select_for_update().filter(
        pk=identifier(data.get("delayId")), scene=scene, kind="timer", status="pending").first()
    if row is None or data.get("expectedDueAt") != row.due_at.isoformat():
        raise MapError("This timer changed. Refresh before restarting it.", "conflict")
    reason = invalid_reason(row)
    if reason:
        raise MapError(reason, "conflict")
    _finish(row, "cancelled", "Restarted by the GM.")
    _record_cancelled(row, scene, "Restarted by the GM.")
    AutomationDelay.objects.create(scene=scene, element_id=row.element_id, user_id=row.user_id, role=row.role,
        kind="timer", name=row.name, chain_id=row.chain_id, request_id=row.request_id, event=row.event,
        node_id=row.node_id, graph_hash=row.graph_hash, seconds=row.seconds,
        due_at=timezone.now() + timedelta(seconds=row.seconds), data=deepcopy(row.data))
    _notify(scene)
    return {"delays": pending_delays(scene)}


def schedule_delay(scene, who, element, event, delay, *, chain_id, request_id, budget, context=None):
    """Store the checkpoint in the same transaction as effects preceding the wait."""
    _capacity(scene)
    from .blueprints import clean_blueprint
    blueprint = clean_blueprint(element.data["blueprint"])
    checkpoint = deepcopy(delay["continuation"])
    # The evaluator reads only authored references, rather than serializing every
    # element in a large scene into each durable checkpoint.
    refs = {node["targetId"] for node in blueprint["graphs"][event]["nodes"]
            if node["type"] == "reference"}
    checkpoint["doors"] = {key: value for key, value in checkpoint["doors"].items() if key in refs}
    data = {"continuation": checkpoint, "budget": deepcopy(budget)}
    if context is not None:
        data["context"] = deepcopy(context)
    row = AutomationDelay.objects.create(scene=scene, element=element, user=who.user, role=who.role,
        chain_id=chain_id, request_id=request_id, event=event, node_id=delay["nodeId"],
        graph_hash=semantic_hash(blueprint), seconds=delay["seconds"],
        due_at=timezone.now() + timedelta(seconds=delay["seconds"]), data=data)
    _notify(scene)
    return row


def update_chain_budget(chain_id, budget):
    """Synchronize sibling waits under their shared campaign lock."""
    for row in AutomationDelay.objects.filter(chain_id=chain_id, status="pending"):
        row.data["budget"] = deepcopy(budget)
        row.save(update_fields=["data"])


def _resume(row, now):
    from . import services
    from .blueprint_runtime import automation_paused, operate, record_run
    who = member(row.scene.campaign_id, row.user_id)
    writable(who)
    if row.role == "gm" and who.role != "gm":
        raise MapError("The delayed blueprint no longer has its original permissions.", "forbidden")
    # A later promotion must not grant a player-started continuation GM powers.
    who = copy(who)
    who.role = row.role
    scene = services.scene(row.scene_id, who)
    if automation_paused(scene):
        return "paused"
    element = SceneObject.objects.get(pk=row.element_id, scene=scene)
    reason = invalid_reason(row, element)
    if reason:
        _finish(row, "cancelled", reason, now=now)
        record_run(scene, who, element, "cancelled", {"requested": None,
            "stateBefore": None, "stateAfter": None, "events": [], "message": reason,
            "delayId": str(row.pk), **({"timerName": row.name} if row.kind == "timer" else {})})
        _notify(scene)
        return "cancelled"
    # An Empty Object is a private controller, whose authored area or signal
    # event may legitimately continue for the original player after a wait.
    private_controller = element.kind == "images" and element.data.get("empty") is True
    if who.role != "gm" and (element.data.get("layer") in ("gm", "gm-image-layer") and not private_controller
            or element.kind == "walls" and element.data.get("presentation") in ("secret", "invisible")
            and not element.data.get("discovered")):
        raise MapError("The delayed blueprint is no longer accessible.", "forbidden")
    with transaction.atomic():
        row.status = "running"
        row.save(update_fields=["status"])
        with automation_request(row.request_id):
            ordinal = row.data["budget"].get("randomRoot", 0)
            if type(ordinal) is not int or not 0 <= ordinal <= 1_000_000:
                raise MapError("Invalid blueprint random state.")
            _chain_ordinal.set(ordinal + 1)
            result = operate(scene, who, element, None, interact=False, resume=row)
        _finish(row, "completed", now=now)
        from .models import Receipt
        Receipt.objects.get_or_create(campaign_id=scene.campaign_id, user_id=row.user_id,
            request_id=row.pk, defaults={"result": {"delayId": str(row.pk), "completed": True}})
        from gravewright.realtime.dispatch import changed
        changed(scene.campaign_id, row.user_id, "maps", "objects", row.pk, result)
    _notify(scene)
    return "completed"


def process_due_delays(*, limit=20, now=None):
    """Run due work independently of connected browsers; safe across worker races.

    A job and every resumed effect commit together. A process ending inside the
    transaction leaves its row pending, so restarting the host can retry it.
    """
    now = now or timezone.now()
    if type(limit) is not int or not 1 <= limit <= 256:
        raise ValueError("Invalid delay batch size.")
    stats = {"processed": 0, "completed": 0, "cancelled": 0, "failed": 0, "paused": 0}
    unpaused = Q(scene__settings__automationPaused=False) | ~Q(scene__settings__has_key="automationPaused")
    ids = list(AutomationDelay.objects.filter(status="pending", due_at__lte=now).filter(unpaused)
               .values_list("pk", "scene__campaign_id")[:limit])
    for identifier, campaign_id in ids:
        with transaction.atomic():
            if not Campaign.objects.select_for_update().filter(pk=campaign_id).exists():
                continue
            row = AutomationDelay.objects.select_for_update().select_related("scene", "element", "user").filter(
                pk=identifier, status="pending", due_at__lte=now).first()
            if row is None:
                continue
            stats["processed"] += 1
            try:
                # A savepoint discards every resumed effect on a domain failure,
                # while the enclosing transaction may record the failed job.
                with transaction.atomic():
                    outcome = _resume(row, now)
            except (MapError, JournalError, Scene.DoesNotExist, SceneObject.DoesNotExist) as error:
                row.refresh_from_db()
                outcome = "cancelled" if getattr(error, "code", None) in ("forbidden", "not_found", "not_a_member") else "failed"
                _finish(row, outcome, str(error), now=now)
                from .blueprint_runtime import record_run
                from gravewright.campaigns.models import Membership
                actor = Membership.objects.select_related("user").filter(
                    campaign_id=campaign_id, user_id=row.user_id).first()
                if actor is not None:
                    record_run(row.scene, actor, row.element, outcome, {"requested": None,
                        "stateBefore": None, "stateAfter": None, "events": [],
                        "message": str(error), "delayId": str(row.pk),
                        **({"timerName": row.name} if row.kind == "timer" else {})})
                _notify(row.scene)
            stats[outcome] += 1
    return stats
