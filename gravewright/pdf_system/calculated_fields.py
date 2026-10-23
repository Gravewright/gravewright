"""Validated original PDF field addresses and authoritative calculated values."""

import re
from copy import deepcopy

from gravewright.maps.services import MapError

from .formulas import calculate_formula, compile_formula, field_references, number_text, numeric_value, source_identity

MAX_FIELD_BINDINGS = 1024
MAX_CALCULATED_FIELDS = 256
SLOT_PATHS = {
    "bar1Value": "sheet.bars.bar_1.value", "bar1Max": "sheet.bars.bar_1.max",
    "bar2Value": "sheet.bars.bar_2.value", "bar2Max": "sheet.bars.bar_2.max",
    "initiative": "sheet.init", "defense": "sheet.ac",
}
PROTECTED = {"__proto__", "prototype", "constructor"}
FIELD_PATH = re.compile(r"sheet\.fields\.([A-Za-z0-9_-]{1,512})\Z")


def _field(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 512 or "\x00" in value:
        raise MapError("Invalid PDF field identifier.")
    return value


def _bindings(raw):
    if not isinstance(raw, list) or len(raw) > MAX_FIELD_BINDINGS:
        raise MapError("Use at most 1024 PDF field bindings.")
    result, keys = [], set()
    required = {"source", "field", "path", "type", "name"}
    for binding in raw:
        if not isinstance(binding, dict) or not required <= set(binding) or set(binding) - required - {"readOnly"}:
            raise MapError("Invalid PDF field binding.")
        clean = deepcopy(binding)
        clean["source"] = source_identity(clean["source"])
        clean["field"] = _field(clean["field"])
        key = (clean["source"], clean["field"])
        if key in keys:
            raise MapError("PDF field bindings must be unique for each source and field.")
        keys.add(key)
        path = clean["path"]
        match = FIELD_PATH.fullmatch(path) if isinstance(path, str) else None
        if not match and path not in SLOT_PATHS.values() or match and match[1] in PROTECTED:
            raise MapError("Invalid PDF field binding path.")
        if not isinstance(clean["type"], str) or clean["type"] not in {"string", "number", "boolean"}:
            raise MapError("Invalid PDF field binding type.")
        if not match and clean["type"] != "number":
            raise MapError("Invalid PDF field binding type.")
        clean["name"] = _field(clean["name"])
        if "readOnly" in clean and type(clean["readOnly"]) is not bool:
            raise MapError("Invalid PDF field read-only setting.")
        result.append(clean)
    return result


def normalize_field_bindings(pdf, previous=None, *, gm=True):
    old_pdf = (previous or {}).get("pdf", {})
    old = old_pdf.get("fieldBindings", [])
    if "fieldBindings" not in pdf:
        if "fieldBindings" not in old_pdf:
            return
        pdf["fieldBindings"] = deepcopy(old)
    clean = _bindings(pdf["fieldBindings"])
    if not gm and clean != _bindings(old):
        raise MapError("Only the GM can configure PDF field bindings.", "forbidden")
    pdf["fieldBindings"] = clean


def bindings_for_source(pdf, source):
    result = {entry["field"]: entry for entry in pdf.get("fieldBindings", []) if entry["source"] == source}
    for field in pdf.get("manualFields", []):
        if field["source"] != source:
            continue
        name = "manual_" + field["id"].replace("-", "")
        result[name] = {"source": source, "field": name, "path": "sheet.fields." + name,
                        "type": "boolean" if field["type"] == "checkbox" else "number" if field["type"] == "number" else "string",
                        "name": field["name"], "readOnly": False, "multiline": field["type"] == "multiline", "manual": True}
    return result


def binding_path(data, binding):
    choices = data.get("token", {}).get("bars", {})
    matches = [path for slot, path in SLOT_PATHS.items() if choices.get(slot) == binding["field"]]
    if matches:
        return matches[0] if binding.get("manual") else matches[-1]
    return binding["path"]


def _read(data, path):
    cursor = data
    for key in path.split(".")[1:]:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return cursor


def _write(data, path, value):
    keys = path.split(".")[1:]
    cursor = data
    for key in keys[:-1]:
        if not isinstance(cursor.get(key), dict):
            cursor[key] = {}
        cursor = cursor[key]
    cursor[keys[-1]] = value


def _definitions(raw):
    if not isinstance(raw, list) or len(raw) > MAX_CALCULATED_FIELDS:
        raise MapError("Use at most 256 calculated PDF fields.")
    result, keys = [], set()
    for row in raw:
        if not isinstance(row, dict) or set(row) != {"source", "field", "formula"}:
            raise MapError("Invalid calculated PDF field.")
        clean = {"source": source_identity(row["source"]), "field": _field(row["field"]), "formula": row["formula"]}
        key = (clean["source"], clean["field"])
        if key in keys:
            raise MapError("Calculated PDF fields must be unique for each source and field.")
        keys.add(key)
        compile_formula(clean["formula"], dice=False, allow_value=False)
        result.append(clean)
    return result


def calculation_order(definitions, bindings, data):
    targets = {entry["field"]: entry for entry in definitions}
    addresses = {}
    for name in targets:
        binding = bindings.get(name)
        if not binding:
            raise MapError("A calculated PDF field is not available.")
        if binding["type"] == "boolean" or binding.get("multiline") or binding.get("readOnly"):
            raise MapError("This PDF field cannot be calculated.")
        path = binding_path(data, binding)
        if path in addresses:
            raise MapError("Calculated PDF fields must use different value addresses.")
        addresses[path] = name
    order, visiting, visited = [], set(), set()

    def visit(name):
        if name in visiting:
            raise MapError("Calculated PDF fields cannot contain circular references.")
        if name in visited:
            return
        visiting.add(name)
        for reference in field_references(targets[name]["formula"], allow_value=False):
            if reference not in bindings:
                raise MapError("A referenced PDF field is not available.")
            dependency = addresses.get(binding_path(data, bindings[reference]))
            if dependency:
                visit(dependency)
        visiting.remove(name)
        visited.add(name)
        order.append(targets[name])

    for name in targets:
        visit(name)
    return order


def normalize_calculated_fields(data, previous=None, *, gm=True):
    """Recompute active-source outputs; failed inputs preserve server-owned values.

    Return display diagnostics without preventing unrelated field edits from
    saving. Syntax, references, cycles and configuration authorization still fail
    validation. Runtime failures never trust a submitted calculated value.
    """
    pdf = data["pdf"]
    old_pdf = (previous or {}).get("pdf", {})
    old = old_pdf.get("calculatedFields", [])
    if "calculatedFields" not in pdf:
        if "calculatedFields" not in old_pdf:
            return []
        pdf["calculatedFields"] = deepcopy(old)
    definitions = _definitions(pdf["calculatedFields"])
    if not gm and definitions != _definitions(old):
        raise MapError("Only the GM can configure calculated PDF fields.", "forbidden")
    pdf["calculatedFields"] = definitions
    active = source_identity("asset:" + pdf["asset"]) if pdf.get("asset") else "template:" + (pdf.get("template") or "generic")
    orders = {}
    for source in dict.fromkeys(entry["source"] for entry in definitions):
        bindings = bindings_for_source(pdf, source)
        orders[source] = calculation_order([entry for entry in definitions if entry["source"] == source], bindings,
                                            data if source == active else {"token": {"bars": {}}})
    bindings = bindings_for_source(pdf, active)
    previous_bindings = bindings_for_source(old_pdf, active)
    errors = []
    for entry in orders.get(active, []):
        name = entry["field"]
        binding = bindings[name]
        path = binding_path(data, binding)
        value_type = "number" if path in SLOT_PATHS.values() else binding["type"]
        try:
            value = calculate_formula(entry["formula"], lambda reference: _read(data, binding_path(data, bindings[reference])))
            value = number_text(value) if value_type == "string" else value
        except MapError as error:
            old_binding = previous_bindings.get(name, binding)
            value = _read(previous or {}, binding_path(previous or {}, old_binding))
            if value is None:
                value = "0" if value_type == "string" else 0
            elif value_type == "string":
                value = str(value)
            else:
                try:
                    value = numeric_value(value)
                except MapError:
                    value = 0
            errors.append({"field": name, "message": str(error)})
        _write(data, path, value)
    return errors
