"""Bounded immutable trigger metadata for Blueprint values and durable work."""

from copy import deepcopy

from .blueprint_variables import typed_value
from .services import MapError


CONTEXT_TYPES = {"event": "text", "sourceId": "text", "userId": "text", "userName": "text",
                 "tokenId": "text", "actorId": "text", "presence": "text", "count": "number",
                 "hasToken": "boolean", "state": "state", "previous": "state"}
TRIGGER_FIELDS = ("sourceId", "userId", "userName", "tokenId", "actorId", "presence", "count", "hasToken")


def clean_event_context(raw, *, event, state, previous):
    """Copy scalar preview/trigger data; graph identity always comes from the evaluator."""
    if raw is None:
        raw = {}
    if not isinstance(raw, dict) or set(raw) - set(CONTEXT_TYPES):
        raise MapError("Invalid blueprint event context.")
    result = {key: False if kind == "boolean" else 0 if kind == "number" else ""
              for key, kind in CONTEXT_TYPES.items() if kind != "state"}
    for key in TRIGGER_FIELDS:
        if key not in raw:
            continue
        try:
            result[key] = typed_value(raw[key], CONTEXT_TYPES[key])
        except MapError:
            raise MapError("Invalid blueprint event context.") from None
    if type(result["count"]) is not int or not 0 <= result["count"] <= 1_000_000:
        raise MapError("Invalid blueprint event context.")
    if "hasToken" not in raw:
        result["hasToken"] = bool(result["tokenId"])
    result.update(event=event, state=state, previous=previous)
    return deepcopy(result)


def trigger_context(who, source_id, raw=None, *, resumed=False):
    """Build trusted metadata from the command actor and server-owned presence data."""
    from gravewright.journals.services import identifier
    raw = deepcopy(raw or {})
    raw.pop("event", None)
    raw.pop("state", None)
    raw.pop("previous", None)
    if not resumed:
        raw.update(userId=str(who.user_id), userName=who.user.name, sourceId=str(source_id))
    else:
        raw.setdefault("userId", str(who.user_id))
        raw.setdefault("userName", who.user.name)
        raw.setdefault("sourceId", str(source_id))
    clean = clean_event_context(raw, event="", state="", previous="")
    if clean["userId"] != str(who.user_id):
        raise MapError("Invalid blueprint event context.")
    for key in ("userId", "sourceId", "tokenId", "actorId"):
        if clean[key]:
            clean[key] = str(identifier(clean[key]))
    if clean["presence"] not in ("", "enter", "exit") or type(clean["count"]) is not int:
        raise MapError("Invalid blueprint event context.")
    clean["hasToken"] = bool(clean["tokenId"])
    return {key: clean[key] for key in TRIGGER_FIELDS}
