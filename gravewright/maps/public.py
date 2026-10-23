"""Explicit JSON adapters for authorized public map capabilities.

Only transport names change here. Domain services retain their revision,
permission, receipt, transaction and storage boundaries. In particular, this
adapter must not wrap image rendering in an outer database transaction.
"""
from api import map_builder, map_blueprints, universal_vtt
from gravewright.journals.services import identifier

from . import builder_services, services


_SCENE_KEYS = {"sceneId", "mapId"}


def _fields(payload, required=(), optional=()):
    if (not isinstance(payload, dict) or not set(required) <= payload.keys()
            or payload.keys() - set(required) - set(optional) - _SCENE_KEYS):
        raise services.MapError("Invalid public map command.")


def _scene(payload, scene_id=None, *, required=True):
    values = [identifier(payload[key]) for key in ("sceneId", "mapId")
              if payload.get(key) is not None]
    if scene_id is not None:
        values.append(identifier(scene_id))
    if values and any(value != values[0] for value in values[1:]):
        raise services.MapError("The scene context changed. Reopen this tool.", "conflict")
    if not values and required:
        raise services.MapError("Choose a scene for this operation.")
    return values[0] if values else None


def _request(request_id):
    return {"request_id": str(identifier(request_id))}


def _project_scene(campaign_id, user_id, project_id, target):
    if target is None:
        return
    source = map_builder.detail(campaign_id, user_id, project_id)["project"]
    if source["sceneId"] != str(target):
        raise services.MapError("The scene context changed. Reopen this tool.", "conflict")


def invoke(campaign_id, user_id, domain, method, payload, request_id, scene_id=None):
    """Dispatch a registered capability, preserving campaign and scene authority.

    ``request_id`` belongs to the transport envelope. A caller cannot replace it
    with a second identifier inside ``payload``. ``scene_id`` is an optional
    authoritative mounted context; table-level libraries remain campaign scoped.
    """
    if not isinstance(domain, str) or not isinstance(method, str) or not isinstance(payload, dict):
        raise services.MapError("Invalid public map command.")
    builder_services.authority(campaign_id, user_id)
    target = _scene(payload, scene_id, required=False)
    if domain == "mapBuilder":
        return _builder(campaign_id, user_id, method, payload, request_id, target)
    if domain == "blueprints":
        return _blueprints(campaign_id, user_id, method, payload, request_id, target)
    if domain == "maps" and method == "exportUniversalVtt":
        _fields(payload)
        return universal_vtt.export_map(campaign_id, user_id, _scene(payload, scene_id))
    if domain == "maps" and method == "navigate":
        _fields(payload)
        return services.command(campaign_id, user_id, "navigate",
                                {"mapId": str(target) if target else None}, identifier(request_id))
    raise services.MapError("Unknown public map capability.")


def _builder(campaign_id, user_id, method, payload, request_id, target):
    args = campaign_id, user_id
    if method == "state":
        _fields(payload)
        return map_builder.catalog(*args)
    if method == "read":
        _fields(payload, ("projectId",))
        return map_builder.detail(*args, payload["projectId"])
    if method == "save":
        _fields(payload, ("projectId", "expectedVersion", "document"), ("folderId",))
        return map_builder.save(*args, payload["projectId"], {
            **_request(request_id), "expected_version": payload["expectedVersion"],
            "folder_id": payload.get("folderId"), "document": payload["document"],
        })
    if method in ("generate", "update", "sync"):
        required = ("projectId", "expectedVersion")
        if method != "generate":
            required += ("expectedSceneVersion",)
        _fields(payload, required)
        native = {**_request(request_id), "expected_version": payload["expectedVersion"]}
        if method != "generate":
            _project_scene(*args, payload["projectId"], target)
            native["expected_scene_version"] = payload["expectedSceneVersion"]
            if target is not None:
                native["expected_scene_id"] = str(target)
        operation = {"generate": map_builder.generate, "update": map_builder.update, "sync": map_builder.sync}[method]
        return operation(*args, payload["projectId"], native)
    if method == "adopt":
        _fields(payload, ("expectedSceneVersion",))
        return map_builder.adopt(*args, _scene(payload, target), {
            **_request(request_id), "expected_scene_version": payload["expectedSceneVersion"],
        })
    raise services.MapError("Unknown public map capability.")


def _blueprints(campaign_id, user_id, method, payload, request_id, target):
    args = campaign_id, user_id
    if method == "templates":
        _fields(payload)
        return map_blueprints.template_catalog(*args)
    if method == "readTemplate":
        _fields(payload, ("templateId",))
        return map_blueprints.template_detail(*args, payload["templateId"])
    if method in ("saveTemplate", "deleteTemplate"):
        required = ("templateId", "expectedVersion")
        if method == "saveTemplate":
            required += ("name", "description", "definition")
        _fields(payload, required)
        native = {**_request(request_id), "expected_version": payload["expectedVersion"]}
        if method == "saveTemplate":
            native.update((key, payload[key]) for key in ("name", "description", "definition"))
        return map_blueprints.template_mutate(*args, payload["templateId"], native, delete=method == "deleteTemplate")
    if method == "state":
        _fields(payload)
        return map_blueprints.network_state(*args, _scene(payload, target))
    if method == "save":
        _fields(payload, ("elementId", "expectedVersion", "expectedProjectVersion", "blueprint"))
        return map_blueprints.network_save(*args, _scene(payload, target), payload["elementId"], {
            **_request(request_id), "expected_version": payload["expectedVersion"],
            "expected_project_version": payload["expectedProjectVersion"], "blueprint": payload["blueprint"],
        })
    if method == "test":
        _fields(payload, ("elementId", "expectedVersion", "event"), ("tokenId", "blueprint"))
        return map_blueprints.rehearse(*args, _scene(payload, target), payload["elementId"], {
            **_request(request_id), "expected_version": payload["expectedVersion"], "event": payload["event"],
            **{key: payload[key] for key in ("tokenId", "blueprint") if key in payload},
        })
    if method == "testDraft":
        _fields(payload, ("document", "elementId", "event"), ("actorId",))
        return map_blueprints.rehearse_draft(*args, {
            **_request(request_id), **{key: payload[key] for key in ("document", "elementId", "event", "actorId") if key in payload},
        })
    if method == "control":
        _fields(payload, ("elementId", "expectedVersion", "action"), ("value",))
        return map_blueprints.control(*args, _scene(payload, target), payload["elementId"], {
            **_request(request_id), "expected_version": payload["expectedVersion"], "action": payload["action"],
            **({"value": payload["value"]} if "value" in payload else {}),
        })
    raise services.MapError("Unknown public map capability.")
