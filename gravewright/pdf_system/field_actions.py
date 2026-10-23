"""GM-authored roll actions bound to one native or manually mapped PDF field."""

from copy import deepcopy

from gravewright.maps.services import MapError

from .formulas import compile_formula, field_references, source_identity

MAX_FIELD_ACTIONS = 256


def _source(value):
    try:
        return source_identity(value)
    except MapError:
        raise MapError("Invalid PDF field action source.") from None


def _formula(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise MapError("Use a PDF field roll formula with 1 to 512 characters.")
    compile_formula(value)
    return value


def _definitions(raw):
    if not isinstance(raw, list) or len(raw) > MAX_FIELD_ACTIONS:
        raise MapError("Use at most 256 PDF field actions.")
    result = []
    keys = set()
    for value in raw:
        if not isinstance(value, dict) or set(value) != {"source", "field", "roll"}:
            raise MapError("Invalid PDF field action.")
        source = _source(value["source"])
        field = value["field"]
        if not isinstance(field, str) or not field.strip() or len(field) > 512 or "\x00" in field:
            raise MapError("Use a PDF field identifier with 1 to 512 characters.")
        key = (source, field)
        if key in keys:
            raise MapError("PDF field actions must be unique for each source and field.")
        keys.add(key)
        roll = value["roll"]
        if not isinstance(roll, dict) or set(roll) != {"formula", "label"}:
            raise MapError("Invalid PDF field roll action.")
        label = roll["label"]
        if not isinstance(label, str) or len(label) > 48 or "\x00" in label:
            raise MapError("Use a PDF field roll label with at most 48 characters.")
        result.append({"source": source, "field": field,
                       "roll": {"formula": _formula(roll["formula"]), "label": label}})
    return result


def normalize_field_actions(pdf, previous=None, *, gm=True):
    """Preserve omitted actions and prohibit non-GM configuration changes.

    Source identities only select a field's configuration; they grant no access
    to PDF assets. A missing native/manual field may retain an archived action.
    """
    old_pdf = (previous or {}).get("pdf", {})
    old_actions = old_pdf.get("fieldActions", [])
    if "fieldActions" not in pdf:
        if "fieldActions" not in old_pdf:
            return
        pdf["fieldActions"] = deepcopy(old_actions)
    definitions = _definitions(pdf["fieldActions"])
    if not gm and definitions != _definitions(old_actions):
        raise MapError("Only the GM can configure PDF field actions.", "forbidden")
    from .calculated_fields import bindings_for_source
    for action in definitions:
        bindings = bindings_for_source(pdf, action["source"])
        if any(reference not in bindings for reference in field_references(action["roll"]["formula"])):
            raise MapError("A referenced PDF field is not available.")
    pdf["fieldActions"] = definitions
