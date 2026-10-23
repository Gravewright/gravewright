"""Validate the PDF system's GM-authored, source-bound overlay fields."""

import re
from copy import deepcopy
from uuid import UUID

from gravewright.maps.objects import boolean, number
from gravewright.maps.services import MapError

MAX_MANUAL_FIELDS = 256
FIELD_KEYS = {"id", "source", "page", "type", "name", "x", "y", "width", "height"}
FIELD_TYPES = {"text", "number", "checkbox", "multiline"}


def _uuid(value):
    if not isinstance(value, str):
        raise MapError("Invalid manual PDF field identifier.")
    try:
        return str(UUID(value))
    except (ValueError, AttributeError):
        raise MapError("Invalid manual PDF field identifier.") from None


def _definitions(raw):
    if not isinstance(raw, list) or len(raw) > MAX_MANUAL_FIELDS:
        raise MapError("Use at most 256 manual PDF fields.")
    result = []
    identifiers = set()
    for value in raw:
        if not isinstance(value, dict) or set(value) != FIELD_KEYS:
            raise MapError("Invalid manual PDF field.")
        field = deepcopy(value)
        field["id"] = _uuid(field["id"])
        if field["id"] in identifiers:
            raise MapError("Manual PDF field identifiers must be unique.")
        identifiers.add(field["id"])
        source = field["source"]
        if not isinstance(source, str):
            raise MapError("Invalid manual PDF field source.")
        if source.startswith("asset:"):
            field["source"] = "asset:" + _uuid(source[6:])
        elif not re.fullmatch(r"template:[A-Za-z0-9_-]{1,120}", source):
            raise MapError("Invalid manual PDF field source.")
        if type(field["page"]) is not int or not 1 <= field["page"] <= 100000:
            raise MapError("Invalid manual PDF field page.")
        if not isinstance(field["type"], str) or field["type"] not in FIELD_TYPES:
            raise MapError("Invalid manual PDF field type.")
        name = field["name"]
        if not isinstance(name, str) or not name.strip() or len(name) > 120:
            raise MapError("Use a manual PDF field name with 1 to 120 characters.")
        for key in ("x", "y"):
            number(field[key], 0, 1)
        for key in ("width", "height"):
            number(field[key], 0.001, 1)
        if field["x"] + field["width"] > 1 or field["y"] + field["height"] > 1:
            raise MapError("Manual PDF fields must fit inside their page.")
        result.append(field)
    return result


def normalize_manual_fields(pdf, fields, previous=None, *, gm=True):
    """Keep omitted layouts, authorize definition edits and validate stored values.

    Definitions use top-left coordinates normalized to the displayed PDF page.
    Their source is a display binding, never authority to read a PDF asset.
    Old values deliberately survive removal of a definition or PDF source.
    """
    old_pdf = (previous or {}).get("pdf", {})
    old_fields = old_pdf.get("manualFields", [])
    if "manualFields" not in pdf:
        if "manualFields" in old_pdf:
            pdf["manualFields"] = deepcopy(old_fields)
        else:
            return
    definitions = _definitions(pdf["manualFields"])
    if not gm and definitions != _definitions(old_fields):
        raise MapError("Only the GM can map PDF fields.", "forbidden")
    pdf["manualFields"] = definitions
    for field in definitions:
        key = "manual_" + field["id"].replace("-", "")
        if key not in fields:
            continue
        value = fields[key]
        if field["type"] == "checkbox":
            boolean(value)
        elif field["type"] == "number":
            number(value)
        elif not isinstance(value, str) or len(value) > 20000:
            raise MapError("Invalid manual PDF field value.")
