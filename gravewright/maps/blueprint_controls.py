"""Revision-checked GM controls over the scene's existing native elements."""
from copy import deepcopy

from django.db import transaction
from gravewright.campaigns.models import Campaign
from gravewright.journals.services import identifier, member
from gravewright.realtime.dispatch import changed

from . import objects, services
from .blueprint_actions import change_visual, intelligent, movable
from .blueprint_runtime import automation_paused, element_kind, element_state, operate
from .builder_services import fingerprint, record, replay
from .models import MapAsset, SceneObject, SceneState


def control(campaign_id, user_id, scene_id, element_id, payload):
    if (not isinstance(payload, dict) or not {"request_id", "expected_version", "action"} <= payload.keys()
            or payload.keys() - {"request_id", "expected_version", "action", "value"}
            or type(payload["expected_version"]) is not int or payload["expected_version"] < 1
            or payload["action"] not in ("state", "interact", "flame", "visibility", "appearance", "interaction", "region")
            or ("value" in payload) == (payload["action"] == "interact")):
        raise services.MapError("Invalid scene control command.")
    request_id, element_id, scene_id = map(identifier, (payload["request_id"], element_id, scene_id))
    digest = fingerprint(f"scene-control:{scene_id}", element_id, payload)
    with transaction.atomic():
        Campaign.objects.select_for_update().get(pk=campaign_id)
        who = member(campaign_id, user_id)
        services.manage(who)
        scene = services.scene(scene_id, who)
        cached = replay(campaign_id, user_id, request_id, digest)
        if cached is not None:
            return cached
        row = SceneObject.objects.select_for_update().filter(scene=scene, pk=element_id).first()
        if row is None or not movable(row):
            raise services.MapError("Choose an element from this scene.", "not_found")
        if row.version != payload["expected_version"]:
            raise services.MapError("This object changed. Refresh the scene controls.", "conflict")
        action, value = payload["action"], payload.get("value")
        before = deepcopy(row.data)
        from .blueprint_delays import automation_request, cancel_invalid_delays
        with automation_request(request_id):
            if action in ("state", "interact", "flame"):
                if not intelligent(row) or row.kind == "zones":
                    raise services.MapError("This control requires a door, lever or torch.")
                kind = element_kind(row)
                if action == "flame":
                    if kind != "torch" or type(value) is not bool:
                        raise services.MapError("Choose a torch and a flame state.")
                    objects.apply(scene, who, "images", "torch-light", {"image_id": str(row.pk), "lit": value})
                elif kind == "door":
                    target = element_state(row) if action == "interact" else value
                    if target not in ("open", "closed", "locked"):
                        raise services.MapError("Invalid door state.")
                    if action == "state" and row.data.get("blueprint") is not None:
                        operate(scene, who, row, target, interact=False)
                        environment, _ = SceneState.objects.get_or_create(scene=scene)
                        environment.version += 1
                        environment.save(update_fields=["version"])
                    else:
                        objects.apply(scene, who, "walls", "door", {"wall_id": str(row.pk), "door_state": target})
                else:
                    if action == "state" and value not in ("off", "on"):
                        raise services.MapError("Invalid mechanism state.")
                    if action == "state" and row.data.get("blueprint") is not None:
                        operate(scene, who, row, value, interact=False)
                    elif action == "interact" or value != element_state(row):
                        objects.apply(scene, who, "images", "interact", {"image_id": str(row.pk)})
                row.refresh_from_db()
            elif action in ("visibility", "appearance"):
                if action == "visibility":
                    if type(value) is not bool:
                        raise services.MapError("Invalid artwork visibility.")
                    supported = change_visual(scene, row, {"type": "setVisibility", "visible": value})
                elif value is None:
                    if "surface" in row.data:
                        for key in ("materialId", "materialCrop"):
                            row.data["surface"].pop(key, None)
                    elif intelligent(row):
                        row.data.pop("sprite", None)
                        if row.kind == "images":
                            from .blueprint_runtime import apply_lever_appearance
                            apply_lever_appearance(row)
                    else:
                        raise services.MapError("This element has no restorable appearance.")
                    supported = True
                else:
                    asset_id = identifier(value)
                    if not MapAsset.objects.filter(pk=asset_id, campaign_id=campaign_id, generated_for__isnull=True).exists():
                        raise services.MapError("Choose an image from this campaign.")
                    supported = change_visual(scene, row, {"type": "setAppearance", "assetId": str(asset_id)})
                if not supported:
                    raise services.MapError("This element does not support artwork controls.")
            elif action == "interaction":
                if not intelligent(row) or row.kind == "zones" or type(value) is not bool:
                    raise services.MapError("This element does not support player interaction controls.")
                row.data["interactionEnabled"] = value
            else:
                if row.kind != "zones" or "region" not in row.data or type(value) is not bool:
                    raise services.MapError("Choose a presence region and its enabled state.")
                from .regions import set_enabled
                set_enabled(scene, row, value)
            if row.data != before and action not in ("state", "interact", "flame"):
                if "torch" in row.data:
                    from .torches import sync_components
                    sync_components(row, before, remember=True)
                row.version += 1
                row.save(update_fields=["data", "version"])
            cancel_invalid_delays(scene)
        result = {"elementId": str(row.pk), "version": row.version, "action": action}
        record(campaign_id, user_id, request_id, digest, result)
        changed(campaign_id, user_id, "maps", "objects", request_id, result)
        return result
