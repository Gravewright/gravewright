"""Explicit, system-owned operations shared by Python and leased browser callers."""
import json
import re
from copy import deepcopy

from gravewright.journals.services import identifier, member, writable
from gravewright.maps.services import MapError, scene
from .systems import resolve_system_id

_providers = {}
# A 1 MB mapping JSON remains bounded separately by its owning system. Carrying
# that original text inside JSON can double its size through string escaping.
MAX_PAYLOAD_BYTES = 2 * 1_000_000 + 4096


def register_api(system_id, operations):
    """Register trusted callbacks at app startup, without querying campaign data.

    Each operation declares ``effect`` (read/write), ``handler`` and an optional
    English ``description``. Handlers receive campaign/user IDs, a copied payload,
    request UUID and authoritative scene ID. They own resource authorization,
    transactions, revision checks, receipts and post-commit notifications.
    """
    if (not isinstance(system_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{0,119}", system_id)
            or not isinstance(operations, dict) or len(operations) > 128):
        raise ValueError("Invalid system API registration.")
    clean = {}
    for name, operation in operations.items():
        if (not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,119}", name)
                or not isinstance(operation, dict) or set(operation) - {"effect", "handler", "description"}
                or operation.get("effect") not in {"read", "write"} or not callable(operation.get("handler"))
                or not isinstance(operation.get("description", ""), str)
                or len(operation.get("description", "")) > 500):
            raise ValueError("Invalid system API operation.")
        clean[name] = {**operation, "description": operation.get("description", "")}
    _providers[system_id] = clean


def capabilities(campaign_id, user_id):
    """Describe only the current campaign system; this grants no permissions."""
    who = member(campaign_id, user_id)
    system_id = resolve_system_id(who.campaign.system)
    return {"systemId": system_id, "operations": [
        {"name": name, "effect": operation["effect"], "description": operation["description"]}
        for name, operation in sorted(_providers.get(system_id, {}).items())
    ]}


def call(campaign_id, user_id, operation, payload, request_id=None, *, scene_id=None):
    """Call the active system's allowlisted operation with current permissions.

    A request UUID is mandatory for writes. Streamers are always read-only.
    A mounted scene cannot be replaced through either scene alias in payload.
    Unsupported operations fail rather than falling back to another system.
    """
    who = member(campaign_id, user_id)
    if not isinstance(operation, str):
        raise MapError("Invalid system API operation.")
    callback = _providers.get(resolve_system_id(who.campaign.system), {}).get(operation)
    if callback is None:
        raise MapError("This operation is not supported by the campaign system.", "not_found")
    try:
        valid = isinstance(payload, dict) and len(json.dumps(payload, allow_nan=False).encode("utf-8")) <= MAX_PAYLOAD_BYTES
    except (TypeError, ValueError, UnicodeError, RecursionError):
        valid = False
    if not valid:
        raise MapError("Invalid system API payload.")
    if scene_id is not None:
        scene_id = scene(scene_id, who).pk
        if any(payload.get(key) is not None and str(payload[key]) != str(scene_id) for key in ("sceneId", "mapId")):
            raise MapError("The scene context changed. Reopen the integration.", "conflict")
    if callback["effect"] == "write":
        writable(who)
        request_id = identifier(request_id)
    elif request_id is not None:
        request_id = identifier(request_id)
    return callback["handler"](who.campaign_id, who.user_id, deepcopy(payload), request_id, scene_id)
