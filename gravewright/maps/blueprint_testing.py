"""GM rehearsals through the real engine, always discarded at a savepoint."""

from copy import deepcopy
import uuid

from django.db import transaction

from gravewright.audio.models import Playback
from gravewright.campaigns.models import Campaign
from gravewright.journals.services import identifier, member
from gravewright.tokens.models import Token

from . import services
from .blueprint_actions import intelligent
from .blueprint_delays import automation_request
from .blueprint_runtime import clean_native_blueprint, element_kind, element_state, operate
from .models import AutomationDelay, AutomationRun, MapAsset, Scene, SceneObject


def _payload(raw, required, optional=()):
    if (not isinstance(raw, dict) or not set(required) <= raw.keys()
            or raw.keys() - set(required) - set(optional)):
        raise services.MapError("Invalid automation test command.")
    request_id = identifier(raw["request_id"])
    if not isinstance(raw["event"], str) or len(raw["event"]) > 80:
        raise services.MapError("Choose an event defined by this element.")
    return request_id


def _snapshot(scene):
    scene.refresh_from_db()
    elements = {str(row["id"]): {"kind": row["kind"], "data": row["data"], "version": row["version"]}
                for row in SceneObject.objects.filter(scene=scene).values("id", "kind", "data", "version")}
    tokens = {str(row["id"]): {key: value for key, value in row.items() if key != "id"}
              for row in Token.objects.filter(scene=scene).values("id", "grid_x", "grid_y", "elevation", "version")}
    playback = Playback.objects.filter(scene=scene).values("data", "version").first()
    waits = {str(row["id"]): {**{key: value for key, value in row.items() if key not in ("id", "element_id", "due_at")},
                               "elementId": str(row["element_id"]), "dueAt": row["due_at"].isoformat()}
             for row in AutomationDelay.objects.filter(scene=scene).values(
                 "id", "element_id", "kind", "name", "event", "seconds", "status", "due_at")}
    return {"elements": elements, "tokens": tokens, "audio": playback,
            "sceneVariables": deepcopy(scene.settings.get("automationVariables", {})), "scheduled": waits}


def _context(who, row, event, token):
    from .blueprint_context import trigger_context
    region = row.data.get("areaPresence", {}) if row.kind == "images" else row.data.get("region", {})
    result = {"count": len(region.get("occupants", [])),
              "presence": event.split(":", 1)[1] if event in ("presence:enter", "presence:exit") else ""}
    if token is not None:
        result.update(tokenId=str(token.pk), actorId=str(token.actor_id))
    return trigger_context(who, row.pk, result)


def _execute(scene, who, row, payload, *, token=None, source_ids=None):
    blueprint = clean_native_blueprint(payload.get("blueprint", row.data.get("blueprint")),
                                       scene.campaign_id, scene.pk, kind=element_kind(row))
    event = payload["event"]
    if event not in blueprint["graphs"]:
        raise services.MapError("Choose an event defined by this element.")
    if "blueprint" in payload:
        row.data["blueprint"] = blueprint
        row.save(update_fields=["data"])
    before = _snapshot(scene)
    previous_runs = set(AutomationRun.objects.filter(scene=scene).values_list("pk", flat=True))
    error = None
    destruction = {}
    context = _context(who, row, event, token)
    from .blueprint_runtime import rehearsal_scene
    with automation_request(payload["request_id"]), rehearsal_scene(scene):
        try:
            if event == "destroy":
                from .blueprint_lifecycle import destroy_objects
                from .blueprint_delays import cancel_invalid_delays
                destruction = destroy_objects(scene, who, [row], context=context, skip_unbound_teleport=True)
                cancel_invalid_delays(scene)
            else:
                operate(scene, who, row, element_state(row), interact=False, context=context, trigger_event=event,
                        skip_unbound_teleport=True)
        except services.MapError as failure:
            error = failure
    after = _snapshot(scene)
    runs = [{"elementId": str(entry.door_id), "outcome": entry.outcome, **deepcopy(entry.data)}
            for entry in AutomationRun.objects.filter(scene=scene).exclude(pk__in=previous_runs)
            .order_by("created_at", "id")]
    run = (getattr(error, "automation_run", None) if error is not None else
           next((entry for entry in runs if entry["elementId"] == str(row.pk)), None))
    run = deepcopy(run or {"stateBefore": element_state(row), "stateAfter": element_state(row), "events": []})
    changes = {}
    for kind in ("elements", "tokens"):
        changes[kind] = []
        for key in dict.fromkeys([*before[kind], *after[kind]]):
            old, value = before[kind].get(key), after[kind].get(key)
            if old == value:
                continue
            changes[kind].append({"id": key, **({"kind": (value or old)["kind"]} if kind == "elements" else {}),
                **({"sourceId": source_ids[key]} if source_ids and key in source_ids else {}),
                "before": old, "after": value})
    for kind in ("audio", "sceneVariables"):
        changes[kind] = {"before": before[kind], "after": after[kind]}
    scheduled = [{"id": key, "before": before["scheduled"].get(key), "after": after["scheduled"].get(key)}
                 for key in dict.fromkeys([*before["scheduled"], *after["scheduled"]])
                 if after["scheduled"].get(key) != before["scheduled"].get(key)]
    steps = [step for entry in [*runs, *([run] if error else [])]
             for graph in entry.get("events", []) for step in graph.get("steps", [])]
    warnings = []
    if destruction.get("cancelledWaits"):
        warnings.append("destruction-timing-cancelled")
    if any(step["type"] in ("delay", "timer") for step in steps):
        warnings.append("timing-not-advanced")
    if any(step["type"] in ("showMessage", "showHandout", "cameraFocus") for step in steps):
        warnings.append("presentation-not-delivered")
    if scene.settings.get("automationPaused") is True:
        warnings.append("automation-paused")
    if any(step.get("skipped") == "missing-test-token" for step in steps):
        warnings.append("missing-test-token")
    if error is not None:
        # A real command would roll back the whole chain, including earlier actions.
        changes = {"elements": [], "tokens": [], **{kind: {"before": before[kind], "after": before[kind]}
                    for kind in ("audio", "sceneVariables")}}
        scheduled = []
    result = {"ok": error is None, "dryRun": True, "sceneId": str(scene.pk), "elementId": str(row.pk),
              "event": event, "run": run, "runs": runs, "changes": changes, "scheduled": scheduled,
              "warnings": warnings}
    if error is not None:
        result["error"] = {"message": str(error), "code": error.code}
    if source_ids is not None:
        result["sourceIds"] = source_ids
    return result


def run(campaign_id, user_id, scene_id, element_id, payload):
    """Rehearse a chosen native graph without receipts, effects or notifications."""
    _payload(payload, ("request_id", "event", "expected_version"), ("tokenId", "blueprint"))
    if type(payload["expected_version"]) is not int or payload["expected_version"] < 1:
        raise services.MapError("Invalid automation test command.")
    element_id = identifier(element_id)
    with transaction.atomic():
        Campaign.objects.select_for_update().get(pk=campaign_id)
        who = member(campaign_id, user_id)
        services.manage(who)
        scene = services.scene(scene_id, who)
        row = SceneObject.objects.select_for_update().filter(scene=scene, pk=element_id).first()
        if row is None or not intelligent(row):
            raise services.MapError("Choose an editable element from this scene.", "not_found")
        if row.version != payload["expected_version"]:
            raise services.MapError("The object changed. Refresh the scene network before editing.", "conflict")
        token = None
        if "tokenId" in payload:
            token = Token.objects.filter(pk=identifier(payload["tokenId"]), scene=scene,
                                         actor__campaign_id=campaign_id).first()
            if token is None:
                raise services.MapError("Choose a test token from this scene.")
        result = _execute(scene, who, row, payload, token=token)
        transaction.set_rollback(True)
    return result


def _draft_surfaces(document, scene):
    """Create metadata-only dynamic targets; rehearsal never renders or writes art."""
    from .builder_dynamic import plan
    from .element_names import copy_name
    sources = {row["id"]: row for kind in ("floors", "walls") for row in document[kind]}
    result = []
    for plane in plan(document):
        if not plane["dynamic"]:
            continue
        left, top, right, bottom = plane["bounds"]
        source = sources[plane["sourceId"]]
        material = MapAsset.objects.filter(pk=source["assetId"], campaign_id=scene.campaign_id).first() if source["assetId"] else None
        base = MapAsset.objects.create(campaign_id=scene.campaign_id, generated_for=scene,
            name="Rehearsal surface", file=material.file.name if material else "", width=right-left, height=bottom-top)
        row = SceneObject(id=uuid.uuid5(scene.pk, plane["sourceId"]), scene=scene, kind="images", data={
            "asset_id": str(base.pk), "scene_id": str(scene.pk), "src": "", "natural_width": right-left,
            "natural_height": bottom-top, "x": (left+right)/2, "y": (top+bottom)/2,
            "scale": 1, "rotation": 0, "layer": "map", "z_index": -9000,
            "surface": {**plane["surface"], "maskId": str(base.pk)}})
        row.builder_source_id = plane["sourceId"]
        copy_name(row.data, source)
        result.append(row)
    return result


def run_draft(campaign_id, user_id, payload):
    """Build an ephemeral native scene from a validated unsaved Builder document."""
    request_id = _payload(payload, ("request_id", "document", "elementId", "event"), ("actorId",))
    source_id = str(identifier(payload["elementId"]))
    from .builder_services import clean_document, native_objects, remap_native_blueprints
    from .regions import baseline
    with transaction.atomic():
        Campaign.objects.select_for_update().get(pk=campaign_id)
        who = member(campaign_id, user_id)
        services.manage(who)
        document = clean_document(payload["document"], who)
        scene = Scene.objects.create(id=uuid.uuid5(request_id, "blueprint-rehearsal"), campaign=who.campaign,
            name=document["name"], visibility="gm", width=document["columns"]*document["cellSize"],
            height=document["rows"]*document["cellSize"], settings=services.settings({"gridSize": document["cellSize"]}))
        rows = native_objects(document, scene)
        rows.extend(_draft_surfaces(document, scene))
        remap_native_blueprints(rows, document)
        selected = next((row for row in rows if row.builder_source_id == source_id and intelligent(row)), None)
        if selected is None:
            raise services.MapError("Choose an editable element from this scene.", "not_found")
        token = None
        if "actorId" in payload:
            from gravewright.actors.models import Actor
            actor = Actor.objects.filter(pk=identifier(payload["actorId"]), campaign_id=campaign_id).first()
            if actor is None:
                raise services.MapError("Choose a test actor from this campaign.")
            token = Token.objects.create(id=uuid.uuid5(scene.pk, "rehearsal-token"), scene=scene, actor=actor,
                                         grid_x=0, grid_y=0)
            if geometry := selected.data.get("geometry"):
                from gravewright.tokens.services import presentation
                cell, size = document["cellSize"], presentation(token)["token"]["size"]
                token.grid_x = (geometry["x"] + geometry["width"] / 2) / cell - size / 2
                token.grid_y = (geometry["y"] + geometry["height"] / 2) / cell - size / 2
                token.save(update_fields=["grid_x", "grid_y"])
            elif selected.kind == "images":
                from gravewright.tokens.services import presentation
                cell, size = document["cellSize"], presentation(token)["token"]["size"]
                token.grid_x = selected.data["x"] / cell - size / 2
                token.grid_y = selected.data["y"] / cell - size / 2
                token.save(update_fields=["grid_x", "grid_y"])
        baseline(scene, rows)
        SceneObject.objects.bulk_create(rows)
        result = _execute(scene, who, selected, payload, token=token,
                          source_ids={str(row.pk): row.builder_source_id for row in rows})
        result.update(mode="draft", sourceElementId=source_id)
        transaction.set_rollback(True)
    return result
