"""Native PDF character data; independent of the sheet's browser implementation."""

import json
from copy import deepcopy

from gravewright.maps.objects import boolean, number
from gravewright.maps.services import MapError, color

SLOTS = ("bar1Value", "bar1Max", "bar2Value", "bar2Max", "initiative", "defense")


def defaults():
    return {
        "pdf": {
            "template": "generic",
            "page": 1,
            "zoom": 1,
            "spread": False,
            "asset": "",
            "textColor": "#111111",
        },
        "fields": {},
        "effects": [],
        "ac": 0,
        "init": 0,
        "bio": "",
        "history": "",
        "notes": "",
        "token": {
            "size": 1,
            "bars": dict.fromkeys(SLOTS, ""),
            "display": {"name": True, "bar_1": True, "bar_2": True},
        },
        "bars": {k: {"value": 0, "max": 0} for k in ("bar_1", "bar_2")},
    }


def normalize(raw, previous=None, gm=True):
    """Validate PDF sheet fields, token mappings and GM-controlled effect data."""
    if not isinstance(raw, dict) or len(json.dumps(raw, allow_nan=False)) > 500_000:
        raise MapError("Invalid character sheet.")

    def merge(base, value):
        if not isinstance(value, dict):
            raise MapError("Invalid character sheet object.")
        for k, v in value.items():
            if k in {"__proto__", "constructor", "prototype"}:
                raise MapError("Invalid field name.")
            if isinstance(v, dict):
                base[k] = merge(
                    base.get(k, {}) if isinstance(base.get(k, {}), dict) else {}, v
                )
            else:
                base[k] = deepcopy(v)
        return base

    data = merge(defaults(), raw)
    if set(data) - set(defaults()):
        raise MapError("Unknown character sheet property.")
    if not gm and "effects" not in raw:
        data["effects"]=deepcopy((previous or {}).get("effects",[]))
    effects=data["effects"]
    if not isinstance(effects,list) or len(effects)>128 or any(not isinstance(e,dict) for e in effects):
        raise MapError("Invalid active effects.")
    if not gm and effects != (previous or {}).get("effects",[]):
        raise MapError("Only the GM can edit active effects.")
    for key, allowed in [
        ("pdf", {"template", "page", "zoom", "spread", "asset", "textColor"}),
        ("token", {"name", "size", "bars", "display"}),
        ("bars", {"bar_1", "bar_2"}),
    ]:
        if not isinstance(data[key], dict) or set(data[key]) - allowed:
            raise MapError("Unknown character sheet property.")
    if (
        not isinstance(data["fields"], dict)
        or not isinstance(data["token"]["bars"], dict)
        or not isinstance(data["token"]["display"], dict)
    ):
        raise MapError("Invalid token mapping.")
    if set(data["token"]["bars"]) - set(SLOTS) or set(data["token"]["display"]) - {
        "name",
        "bar_1",
        "bar_2",
    }:
        raise MapError("Invalid token mapping.")
    for bar in data["bars"].values():
        if not isinstance(bar, dict) or set(bar) != {"value", "max"}:
            raise MapError("Invalid token bar.")
    pdf = data["pdf"]
    pdf["zoom"] = number(pdf["zoom"], 0.1, 8)
    pdf["page"] = number(pdf["page"], 1, 100000)
    if type(pdf["page"]) is not int:
        raise MapError("Invalid PDF page.")
    boolean(pdf["spread"])
    color(pdf["textColor"])
    for key in ("asset", "template"):
        if not isinstance(pdf[key], str) or len(pdf[key]) > 120:
            raise MapError("Invalid PDF source.")
    number(data["init"])
    number(data["ac"])
    token = data["token"]
    size = number(token["size"], 1, 100)
    if type(size) is not int:
        raise MapError("Invalid token size.")
    if not gm and previous and size != previous["token"]["size"]:
        raise MapError("Only the GM can change token size.", "forbidden")
    if not isinstance(token.get("name", ""), str) or len(token.get("name", "")) > 191:
        raise MapError("Invalid token name.")
    for key in SLOTS:
        if not isinstance(token["bars"].get(key, ""), str):
            raise MapError("Invalid bar mapping.")
    for k in ("name", "bar_1", "bar_2"):
        boolean(token["display"][k])
    for bar in data["bars"].values():
        number(bar["value"])
        number(bar["max"])
    for k in ("bio", "history", "notes"):
        if not isinstance(data[k], (str, dict)):
            raise MapError("Invalid notes.")
        if isinstance(data[k], dict):
            from gravewright.journals.documents import validate_document

            data[k] = validate_document({"doc": data[k]})["doc"]
    return data
