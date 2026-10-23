"""Portable mapping validation and revisioned, campaign-scoped layout storage."""

import json
import math
from copy import deepcopy

from django.db import transaction

from gravewright.actors import services as actors
from gravewright.campaigns.models import Campaign
from gravewright.campaigns.systems import resolve_system_id
from gravewright.journals.services import identifier, member
from gravewright.maps.models import Receipt
from gravewright.maps.services import MapError, title

from .field_actions import _source
from .models import MappingTemplate
from .schema import SLOTS, normalize

BUNDLE_FORMAT = "gravewright.pdf-mapping"
MAX_BUNDLE_BYTES = 1_000_000
MAX_TEMPLATES = 128
LAYOUT_KEYS = ("manualFields", "fieldActions", "calculatedFields", "fieldBindings")


def _finite_json(value):
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
        if len(encoded.encode("utf-8")) > MAX_BUNDLE_BYTES:
            raise MapError("Use a mapping JSON file no larger than 1 MB.")
    except (TypeError, ValueError, RecursionError, UnicodeError):
        raise MapError("Invalid PDF mapping JSON.") from None


def parse_bundle(raw):
    """Decode bounded JSON; duplicate keys and non-finite constants are rejected."""
    if not isinstance(raw, (bytes, str)):
        raise MapError("Use a mapping JSON file no larger than 1 MB.")
    try:
        size = len(raw.encode("utf-8")) if isinstance(raw, str) else len(raw)
    except UnicodeError:
        raise MapError("Invalid PDF mapping JSON.") from None
    if size > MAX_BUNDLE_BYTES:
        raise MapError("Use a mapping JSON file no larger than 1 MB.")

    def pairs(entries):
        result = {}
        for key, value in entries:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    try:
        value = json.loads(raw, object_pairs_hook=pairs,
                           parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (ValueError, UnicodeError, RecursionError):
        raise MapError("Invalid PDF mapping JSON.") from None
    return normalize_bundle(value)


def normalize_bundle(raw):
    """Validate layout-only JSON, using a synthetic source that contains no asset ID."""
    _finite_json(raw)
    allowed = {"format", "version", *LAYOUT_KEYS, "bindings", "document"}
    if (not isinstance(raw, dict) or set(raw) - allowed
            or raw.get("format") != BUNDLE_FORMAT or type(raw.get("version")) is not int
            or raw["version"] != 1):
        raise MapError("Unsupported PDF mapping format or version.")
    pdf = {}
    for key in LAYOUT_KEYS:
        entries = raw.get(key, [])
        if not isinstance(entries, list) or len(entries) > (1024 if key == "fieldBindings" else 256):
            raise MapError("Invalid PDF mapping definitions.")
        if any(not isinstance(entry, dict) or "source" in entry for entry in entries):
            raise MapError("Portable PDF mappings must not contain document sources.")
        if entries or key in ("manualFields", "fieldActions"):
            pdf[key] = [{**deepcopy(entry), "source": "template:portable"} for entry in entries]
    clean = normalize({"pdf": pdf})
    result = {"format": BUNDLE_FORMAT, "version": 1}
    for key in LAYOUT_KEYS:
        result[key] = [{k: deepcopy(v) for k, v in entry.items() if k != "source"}
                       for entry in clean["pdf"].get(key, [])]
    bindings = raw.get("bindings", {})
    if not isinstance(bindings, dict) or set(bindings) - set(SLOTS):
        raise MapError("Invalid PDF mapping token bindings.")
    for slot, field in bindings.items():
        if (not isinstance(field, str) or len(field) > 512 or "\x00" in field
                or field and not field.strip()):
            raise MapError("Invalid PDF mapping token bindings.")
    result["bindings"] = deepcopy(bindings)
    if "document" in raw:
        result["document"] = _document(raw["document"])
    _finite_json(result)
    return result


def _document(raw):
    if (not isinstance(raw, dict) or set(raw) - {"pageCount", "pages", "fingerprint"}
            or type(raw.get("pageCount")) is not int or not 1 <= raw["pageCount"] <= 100000
            or not isinstance(raw.get("pages", []), list) or len(raw.get("pages", [])) > 1024):
        raise MapError("Invalid PDF mapping document metadata.")
    if "fingerprint" in raw and (not isinstance(raw["fingerprint"], str)
                                 or len(raw["fingerprint"]) > 128 or "\x00" in raw["fingerprint"]):
        raise MapError("Invalid PDF mapping document metadata.")
    seen = set()
    for page in raw.get("pages", []):
        if (not isinstance(page, dict) or set(page) != {"page", "width", "height", "rotation"}
                or type(page["page"]) is not int or not 1 <= page["page"] <= raw["pageCount"]
                or page["page"] in seen or type(page["rotation"]) is not int
                or page["rotation"] not in (0, 90, 180, 270)):
            raise MapError("Invalid PDF mapping document metadata.")
        seen.add(page["page"])
        for key in ("width", "height"):
            if type(page[key]) not in (int, float) or not math.isfinite(page[key]) or not 0 < page[key] <= 32768:
                raise MapError("Invalid PDF mapping document metadata.")
    return deepcopy(raw)


def authorize(campaign_id, user_id):
    who = member(campaign_id, user_id)
    if who.role != "gm":
        raise MapError("Only the GM can manage PDF mappings.", "forbidden")
    if resolve_system_id(who.campaign.system) != "gravewright-pdf-system":
        raise MapError("PDF mappings require the Gravewright PDF System.")
    return who


def project(row):
    return {"id": str(row.pk), "name": row.name, "revision": row.revision,
            "bundle": deepcopy(row.bundle)}


def list_templates(campaign_id, user_id):
    authorize(campaign_id, user_id)
    return {"items": [project(row) for row in MappingTemplate.objects.filter(campaign_id=campaign_id)]}


def get_template(campaign_id, user_id, template_id):
    authorize(campaign_id, user_id)
    row = MappingTemplate.objects.filter(campaign_id=campaign_id, pk=identifier(template_id)).first()
    if row is None:
        raise MapError("PDF mapping not found.", "not_found")
    return row


def apply_bundle(data, bundle, source):
    """Replace only one document's layout; retain values, media, notes and canonical bars."""
    bundle = normalize_bundle(bundle)
    source = _source(source)
    candidate = deepcopy(data)
    pdf = candidate.get("pdf")
    if not isinstance(pdf, dict):
        raise MapError("Character sheet unavailable.")
    current = "asset:" + pdf["asset"] if pdf.get("asset") else "template:" + (pdf.get("template") or "generic")
    if source != _source(current):
        raise MapError("The PDF source changed. Reload the character sheet.", "conflict")
    for key in LAYOUT_KEYS:
        incoming = [{**deepcopy(entry), "source": source} for entry in bundle[key]]
        # A stable manual UUID already attached to another document must not be
        # silently reassigned or duplicated by applying a portable layout.
        if key == "manualFields":
            occupied = {entry["id"] for entry in pdf.get(key, []) if entry["source"] != source}
            if any(entry["id"] in occupied for entry in incoming):
                raise MapError("This mapping's field identifiers are already used by another PDF.")
        retained = [entry for entry in pdf.get(key, []) if entry.get("source") != source]
        if incoming or key in pdf:
            pdf[key] = retained + incoming
    candidate["token"]["bars"] = {slot: bundle["bindings"].get(slot, "") for slot in SLOTS}
    if "document" in bundle:
        document = bundle["document"]
        pdf["sourceMetadata"] = [entry for entry in pdf.get("sourceMetadata", []) if entry["source"] != source]
        pdf["sourceMetadata"].append({"source": source, "pageCount": document["pageCount"],
                                      "pages": deepcopy(document.get("pages", [])),
                                      "fingerprint": document.get("fingerprint", "")})
    return normalize(candidate, data, gm=True)


@transaction.atomic
def command(campaign_id, user_id, payload):
    if Campaign.objects.select_for_update().filter(pk=campaign_id).first() is None:
        raise MapError("PDF mapping not found.", "not_found")
    who = authorize(campaign_id, user_id)
    if not isinstance(payload, dict):
        raise MapError("Invalid PDF mapping command.")
    request_id = identifier(payload.get("requestId"))
    receipt = Receipt.objects.filter(campaign_id=campaign_id, user_id=user_id, request_id=request_id).first()
    if receipt:
        return receipt.result
    action = payload.get("action")
    if action in ("create", "import"):
        if MappingTemplate.objects.filter(campaign_id=campaign_id).count() >= MAX_TEMPLATES:
            raise MapError("Use at most 128 PDF mapping templates in a campaign.")
        raw_bundle = payload.get("bundle")
        clean_bundle = parse_bundle(raw_bundle) if action == "import" and isinstance(raw_bundle, (str, bytes)) else normalize_bundle(raw_bundle)
        row = MappingTemplate.objects.create(campaign_id=campaign_id, name=title(payload.get("name")),
                                              bundle=clean_bundle)
        result = project(row)
    elif action in ("update", "delete", "apply"):
        row = get_template(campaign_id, user_id, payload.get("id"))
        if type(payload.get("revision")) is not int or payload["revision"] != row.revision:
            raise MapError("This PDF mapping was changed in another window. Reload the library.", "conflict")
        if action == "update":
            row.name = title(payload.get("name"))
            row.bundle = normalize_bundle(payload.get("bundle"))
            row.revision += 1
            row.save()
            result = project(row)
        elif action == "delete":
            result = {"id": str(row.pk), "deleted": True}
            row.delete()
        else:
            targets = payload.get("targets")
            if not isinstance(targets, list) or not 1 <= len(targets) <= 100:
                raise MapError("Choose between 1 and 100 characters for this mapping.")
            seen, prepared = set(), []
            for target in targets:
                if not isinstance(target, dict) or set(target) != {"actorId", "version", "sheetVersion", "source"}:
                    raise MapError("Invalid PDF mapping target.")
                actor = actors.get(target["actorId"], who, True)
                if actor.pk in seen:
                    raise MapError("Choose each character only once.")
                seen.add(actor.pk)
                actors.revision(actor, target["version"])
                actors.revision(actor, target["sheetVersion"], "sheet_version")
                prepared.append((actor, apply_bundle(actor.data, row.bundle, target["source"])))
            items = []
            for actor, candidate in prepared:
                saved = actors.save_sheet(who, {"actorId": str(actor.pk), "name": actor.name, "data": candidate,
                                                "version": actor.version, "sheetVersion": actor.sheet_version})
                items.append({"actorId": str(actor.pk), **saved})
            result = {"items": items}
    else:
        raise MapError("Unknown PDF mapping command.")
    Receipt.objects.create(campaign_id=campaign_id, user_id=user_id, request_id=request_id, result=result)
    if action == "apply":
        from gravewright.realtime.dispatch import changed
        changed(campaign_id, user_id, "actors", "pdf-mapping.apply", request_id, result)
    return result
