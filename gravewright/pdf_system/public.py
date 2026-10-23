"""Authorized PDF-system capabilities shared by public Python and module APIs."""

from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path

from django.db import transaction

from gravewright.actors import services as actors
from gravewright.campaigns.models import Campaign
from gravewright.campaigns.systems import resolve_system_id
from gravewright.dice import services as dice
from gravewright.journals.services import identifier, member
from gravewright.maps.models import Receipt
from gravewright.maps.services import MapError

from . import templates
from .calculated_fields import binding_path, bindings_for_source, normalize_calculated_fields, _read
from .formulas import expand_formula, source_identity
from .schema import SLOTS


def _member(campaign_id, user_id, *, gm=False):
    who = member(campaign_id, user_id)
    if resolve_system_id(who.campaign.system) != "gravewright-pdf-system":
        raise MapError("PDF mappings require the Gravewright PDF System.")
    if gm and who.role != "gm":
        raise MapError("Only the GM can manage PDF mappings.", "forbidden")
    return who


def _source(data):
    pdf = data.get("pdf")
    if not isinstance(pdf, dict):
        raise MapError("Character sheet unavailable.")
    return source_identity("asset:" + pdf["asset"] if pdf.get("asset")
                           else "template:" + (pdf.get("template") or "generic"))


def _guard_source(view, expected):
    actual = _source(view["data"])
    if expected is not None and source_identity(expected) != actual:
        raise MapError("The PDF source changed. Reload the character sheet.", "conflict")
    return actual


def state(campaign_id, user_id, actor_id, token_id=None):
    """Return the native authorized sheet projection with its active PDF source.

    A token context uses the native snapshot/control checks and snapshot name;
    neither the base actor's data nor its name is substituted by this facade.
    """
    _member(campaign_id, user_id)
    view = actors.sheet(campaign_id, user_id, actor_id, token_id)
    view["source"] = _source(view["data"])
    return view


def _mapping(view):
    pdf, source = view["data"]["pdf"], view["source"]
    result = {"format": templates.BUNDLE_FORMAT, "version": 1}
    for key in templates.LAYOUT_KEYS:
        result[key] = [{name: deepcopy(value) for name, value in row.items() if name != "source"}
                       for row in pdf.get(key, []) if row["source"] == source]
    available = bindings_for_source(pdf, source)
    choices = view["data"].get("token", {}).get("bars", {})
    result["bindings"] = {slot: choices.get(slot, "") if choices.get(slot) in available else "" for slot in SLOTS}
    descriptor = next((row for row in pdf.get("sourceMetadata", []) if row["source"] == source), None)
    if descriptor:
        result["document"] = {name: deepcopy(value) for name, value in descriptor.items() if name != "source"}
    return templates.normalize_bundle(result)


def export_mapping(campaign_id, user_id, actor_id, *, source=None, token_id=None):
    """Export one GM-authorized layout without PDF bytes, asset IDs or values."""
    _member(campaign_id, user_id, gm=True)
    view = state(campaign_id, user_id, actor_id, token_id)
    _guard_source(view, source)
    return _mapping(view)


def _locked_view(campaign_id, user_id, actor_id, request_id, token_id):
    if Campaign.objects.select_for_update().filter(pk=campaign_id).first() is None:
        raise MapError("Character sheet unavailable.", "not_found")
    _member(campaign_id, user_id, gm=True)
    view = state(campaign_id, user_id, actor_id, token_id)
    request_id = identifier(request_id)
    receipt = Receipt.objects.filter(campaign_id=campaign_id, user_id=user_id, request_id=request_id).first()
    return view, request_id, deepcopy(receipt.result) if receipt else None


def _save(campaign_id, user_id, view, candidate, request_id, version, sheet_version, token_id):
    if type(version) is not int or version < 1 or type(sheet_version) is not int or sheet_version < 1:
        raise MapError("Invalid character sheet revision.")
    if token_id and view.get("tokenId"):
        candidate["token"]["name"] = view["name"]
    return actors.command(campaign_id, user_id, "sheet.save", {
        "actorId": view["id"], "tokenId": view.get("tokenId"), "name": view["name"], "data": candidate,
        "version": version, "sheetVersion": sheet_version,
    }, request_id)


@transaction.atomic
def configure(campaign_id, user_id, actor_id, changes, request_id, *, version, sheet_version, source, token_id=None):
    """Replace supplied active-source layout sections under native sheet receipts.

    ``changes`` accepts source-free manualFields, fieldActions, calculatedFields,
    fieldBindings, token ``bindings``, and optional ``document`` metadata. Omitted
    sections and all character values are preserved. Revisions are never fetched
    or substituted on the caller's behalf.
    """
    view, request_id, replay = _locked_view(campaign_id, user_id, actor_id, request_id, token_id)
    if replay is not None:
        return replay
    _guard_source(view, source)
    if not isinstance(changes, dict) or set(changes) - {*templates.LAYOUT_KEYS, "bindings", "document"}:
        raise MapError("Invalid PDF mapping definitions.")
    bundle = {**_mapping(view), **deepcopy(changes)}
    if "bindings" not in changes:
        # Portable exports describe only this document; a partial configuration
        # must still preserve the sheet's existing global token selections.
        bundle["bindings"] = deepcopy(view["data"].get("token", {}).get("bars", {}))
    candidate = templates.apply_bundle(view["data"], bundle, source)
    return _save(campaign_id, user_id, view, candidate, request_id, version, sheet_version, token_id)


@transaction.atomic
def apply_mapping(campaign_id, user_id, actor_id, bundle, request_id, *, version, sheet_version, source, token_id=None):
    """Apply a portable mapping to an actor or independent token snapshot."""
    view, request_id, replay = _locked_view(campaign_id, user_id, actor_id, request_id, token_id)
    if replay is not None:
        return replay
    _guard_source(view, source)
    if isinstance(bundle, (str, bytes)):
        bundle = templates.parse_bundle(bundle)
    candidate = templates.apply_bundle(view["data"], bundle, source)
    return _save(campaign_id, user_id, view, candidate, request_id, version, sheet_version, token_id)


def diagnostics(campaign_id, user_id, actor_id, *, source=None, token_id=None, document=None):
    """Inspect saved metadata and calculations without changing sheet data.

    ``document`` is an optional observed page descriptor, not authority to read
    a file. This function never parses PDF bytes or claims an annotation exists.
    """
    view = state(campaign_id, user_id, actor_id, token_id)
    source = _guard_source(view, source)
    issues = []
    pdf = view["data"]["pdf"]
    expected = next((row for row in pdf.get("sourceMetadata", []) if row["source"] == source), None)
    if document is not None:
        observed = templates._document(document)
        if expected:
            if expected["pageCount"] != observed["pageCount"]:
                issues.append({"code": "page-count", "field": "", "message": "The PDF page count differs from the saved mapping. Check the field positions."})
            pages = {row["page"]: row for row in observed.get("pages", [])}
            changed = any(row["page"] in pages and (
                abs(row["width"] - pages[row["page"]]["width"]) > 0.5
                or abs(row["height"] - pages[row["page"]]["height"]) > 0.5
                or row["rotation"] != pages[row["page"]]["rotation"])
                for row in expected.get("pages", []))
            if changed:
                issues.append({"code": "page-geometry", "field": "", "message": "PDF page sizes or rotations differ from the saved mapping. Check the field positions."})
            elif expected.get("fingerprint") and observed.get("fingerprint") and expected["fingerprint"] != observed["fingerprint"]:
                issues.append({"code": "document-changed", "field": "", "message": "This PDF differs from the document used to create the mapping."})
        for field in pdf.get("manualFields", []):
            if field["source"] == source and field["page"] > observed["pageCount"]:
                issues.append({"code": "field-page", "field": "manual_" + field["id"].replace("-", ""),
                               "message": "A mapped field refers to a missing PDF page: {0}.", "params": [field["name"]]})
    candidate = deepcopy(view["data"])
    for issue in normalize_calculated_fields(candidate, view["data"], gm=True):
        issues.append({"code": "calculation-value", **issue})
    return {"source": source, "issues": issues}


def list_templates(campaign_id, user_id):
    return templates.list_templates(campaign_id, user_id)


def read_template(campaign_id, user_id, template_id):
    return templates.project(templates.get_template(campaign_id, user_id, template_id))


def template_command(campaign_id, user_id, action, data, request_id):
    if not isinstance(data, dict):
        raise MapError("Invalid PDF mapping command.")
    return templates.command(campaign_id, user_id, {**deepcopy(data), "action": action, "requestId": str(identifier(request_id))})


def create_template(campaign_id, user_id, name, bundle, request_id):
    return template_command(campaign_id, user_id, "create", {"name": name, "bundle": bundle}, request_id)


def update_template(campaign_id, user_id, template_id, revision, name, bundle, request_id):
    return template_command(campaign_id, user_id, "update", {"id": str(template_id), "revision": revision, "name": name, "bundle": bundle}, request_id)


def delete_template(campaign_id, user_id, template_id, revision, request_id):
    return template_command(campaign_id, user_id, "delete", {"id": str(template_id), "revision": revision}, request_id)


def export_template(campaign_id, user_id, template_id):
    return templates.normalize_bundle(templates.get_template(campaign_id, user_id, template_id).bundle)


def import_template(campaign_id, user_id, name, raw, request_id):
    return template_command(campaign_id, user_id, "import", {"name": name, "bundle": raw}, request_id)


def apply_template(campaign_id, user_id, template_id, revision, targets, request_id):
    return template_command(campaign_id, user_id, "apply", {"id": str(template_id), "revision": revision, "targets": targets}, request_id)


@lru_cache(maxsize=1)
def _canonical_fields():
    path = Path(__file__).parent / "static" / "gravewright_pdf_system" / "assets" / "pdf-fields.gw.json"
    return json.loads(path.read_text(encoding="utf-8"))["templates"]["generic"]["fields"]


def roll_field(campaign_id, user_id, actor_id, field, request_id, *, source=None, token_id=None, visibility="public", map_id=None):
    """Roll a persisted action using authorized current values and native dice receipts."""
    view = state(campaign_id, user_id, actor_id, token_id)
    if not view["canEdit"]:
        raise MapError("Sheet is read only.", "forbidden")
    request_id = identifier(request_id)
    # A completed retry must not expand a newly edited formula or draw again.
    from gravewright.chat.models import Message
    previous = Message.objects.filter(campaign_id=campaign_id, author_id=user_id, request_id=request_id).first()
    if previous and previous.roll:
        return dice.roll(campaign_id, user_id, previous.roll["expression"], request_id,
                         label=previous.roll["label"], visibility=previous.visibility, map_id=map_id)
    source = _guard_source(view, source)
    action = next((row["roll"] for row in view["data"]["pdf"].get("fieldActions", [])
                   if row["source"] == source and row["field"] == field), None)
    if not action:
        raise MapError("A referenced PDF field is not available.", "not_found")
    bindings = bindings_for_source(view["data"]["pdf"], source)

    def resolve(reference):
        if reference not in bindings:
            raise MapError("A referenced PDF field is not available.")
        return _read(view["data"], binding_path(view["data"], bindings[reference]))

    binding = bindings.get(field)
    if binding:
        value = _read(view["data"], binding_path(view["data"], binding))
    else:
        original = _canonical_fields().get(field, {})
        if not original:
            raise MapError("A referenced PDF field is not available.", "not_found")
        value = view["name"] if original.get("path") == "core.name" else _read(view["data"], original["path"]) if original.get("path") else None
    expression = expand_formula(action["formula"], resolve, value=value)
    label = action["label"] or str(binding["name"] if binding else field)[:48]
    return dice.roll(campaign_id, user_id, expression, request_id, label=label, visibility=visibility, map_id=map_id)


def _payload(value):
    if not isinstance(value, dict):
        raise MapError("Invalid PDF mapping command.")
    return value


def operations():
    """Stable package-owned methods for the host's generic system API dispatcher."""
    def actor_read(function):
        def handler(campaign_id, user_id, payload, request_id, scene_id=None):
            p = _payload(payload)
            if function is state:
                return state(campaign_id, user_id, p.get("actorId"), p.get("tokenId"))
            return function(campaign_id, user_id, p.get("actorId"), source=p.get("source"), token_id=p.get("tokenId"),
                            **({"document": p.get("document")} if function is diagnostics else {}))
        return handler

    def actor_write(function):
        def handler(campaign_id, user_id, payload, request_id, scene_id=None):
            p = _payload(payload)
            return function(campaign_id, user_id, p.get("actorId"), p.get("changes") if function is configure else p.get("bundle"), request_id,
                            version=p.get("version"), sheet_version=p.get("sheetVersion"), source=p.get("source"), token_id=p.get("tokenId"))
        return handler

    def mutate_template(action):
        def handler(campaign_id, user_id, payload, request_id, scene_id=None):
            return template_command(campaign_id, user_id, action, _payload(payload), request_id)
        return handler

    def roll(campaign_id, user_id, payload, request_id, scene_id=None):
        p = _payload(payload)
        return roll_field(campaign_id, user_id, p.get("actorId"), p.get("field"), request_id, source=p.get("source"),
                          token_id=p.get("tokenId"), visibility=p.get("visibility", "public"),
                          map_id=scene_id if scene_id is not None else p.get("mapId", p.get("sceneId")))

    return {
        "pdf.read": {"effect": "read", "handler": actor_read(state)},
        "pdf.configure": {"effect": "write", "handler": actor_write(configure)},
        "pdf.exportMapping": {"effect": "read", "handler": actor_read(export_mapping)},
        "pdf.applyMapping": {"effect": "write", "handler": actor_write(apply_mapping)},
        "pdf.diagnostics": {"effect": "read", "handler": actor_read(diagnostics)},
        "pdf.roll": {"effect": "write", "handler": roll},
        "pdf.templates.list": {"effect": "read", "handler": lambda c, u, p, r, scene_id=None: list_templates(c, u)},
        "pdf.templates.read": {"effect": "read", "handler": lambda c, u, p, r, scene_id=None: read_template(c, u, _payload(p).get("id"))},
        "pdf.templates.export": {"effect": "read", "handler": lambda c, u, p, r, scene_id=None: export_template(c, u, _payload(p).get("id"))},
        **{f"pdf.templates.{action}": {"effect": "write", "handler": mutate_template(action)}
           for action in ("create", "update", "delete", "import", "apply")},
    }
