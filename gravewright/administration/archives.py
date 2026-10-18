"""Portable Django campaign archives. Only the explicit content graph is accepted."""

import hashlib
import io
import json
import re
import stat
import uuid
import zipfile
from copy import deepcopy
from pathlib import PurePosixPath

from django.apps import apps
from django.core import serializers
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import DataError, IntegrityError, models, transaction

from gravewright.accounts.services import AuthError
from gravewright.campaigns.models import Campaign, Membership
from gravewright.campaigns.systems import default_system_id

MAX_ARCHIVE = 256 * 1024 * 1024
MAX_EXPANDED = 1024 * 1024 * 1024
FORMAT = "gravewright.django-campaign"
GROUPS = {
    "scenes": [
        "gravewright_maps.folder",
        "gravewright_maps.assetfolder",
        "gravewright_maps.mapasset",
        "gravewright_maps.scene",
        "gravewright_maps.tile",
        "gravewright_maps.scenestate",
        "gravewright_maps.sceneobject",
        "gravewright_maps.mapbuilderproject",
    ],
    "actors": [
        "gravewright_actors.folder",
        "gravewright_actors.actor",
        "gravewright_actors.asset",
    ],
    "journals": [
        "gravewright_journals.folder",
        "gravewright_journals.journal",
        "gravewright_journals.asset",
        "gravewright_journals.boardentry",
    ],
    "settings": ["gravewright_maps.broadcast"],
    "items": ["gravewright_items.folder", "gravewright_items.item"],
    "audio": ["gravewright_audio.track", "gravewright_audio.playlist", "gravewright_audio.playback"],
    "cards": ["gravewright_cards.cardasset", "gravewright_cards.deckdefinition", "gravewright_cards.deck", "gravewright_cards.card"],
    "combat": ["gravewright_combat.encounter"],
    "compendiums": ["gravewright_compendiums.pack", "gravewright_compendiums.entry", "gravewright_compendiums.entryasset", "gravewright_compendiums.contentaccess"],
    "blueprintTemplates": ["gravewright_maps.blueprinttemplate"],
}
SNAPSHOT_MODELS = {
    "gravewright_table.documentaccess",
    "gravewright_journals.access",
    "gravewright_chat.message",
    "gravewright_chat.cardattachment",
    "gravewright_chat.recipient",
}
ALLOWED = {label for labels in GROUPS.values() for label in labels} | {
    "gravewright_tokens.token"
}


def options(value=None):
    value = {} if value is None else value
    if (
        not isinstance(value, dict)
        or set(value) - GROUPS.keys()
        or any(type(v) is not bool for v in value.values())
    ):
        raise AuthError("invalid_options")
    return {key: value.get(key, True) for key in GROUPS}


def records(campaign, selected, *, snapshot=False):
    labels = [
        label for group, labels in GROUPS.items() if selected[group] for label in labels
    ]
    if not selected["scenes"]:
        labels = [label for label in labels if label not in ("gravewright_audio.playback", "gravewright_combat.encounter")]
    if selected["actors"] and selected["scenes"]:
        labels.append("gravewright_tokens.token")
    if snapshot:
        labels.extend(sorted(SNAPSHOT_MODELS))
    result = []
    for label in labels:
        model = apps.get_model(label)
        fields = {f.name for f in model._meta.fields}
        lookup = (
            "campaign"
            if "campaign" in fields
            else "deck__campaign"
            if "deck" in fields
            else "pack__campaign"
            if "pack" in fields
            else "scene__campaign"
            if "scene" in fields
            else "journal__campaign"
            if "journal" in fields
            else "message__campaign"
            if "message" in fields
            else "entry__pack__campaign"
            if "entry" in fields
            else "board__campaign"
        )
        for record in serializers.serialize(
            "python", model.objects.filter(**{lookup: campaign})
        ):
            if not selected["audio"] and label in {
                "gravewright_maps.sceneobject", "gravewright_maps.mapbuilderproject"
            }:
                record["fields"] = deepcopy(record["fields"])
                omit_blueprint_audio(record)
            data = record["fields"]
            if label in {"gravewright_maps.sceneobject", "gravewright_maps.mapbuilderproject"}:
                data = record["fields"] = deepcopy(data)
                for field in ("data", "generation"):
                    discard_area_presence(label, field, data.get(field))
            if not snapshot:
                data.pop("permissions", None)
                if record['model']=='gravewright_cards.card':
                    data['owner']=None
                    if data['zone']=='hand' or not selected['scenes']:
                        data['zone']='draw';data['revealed']=False;data['scene']=None
                for key in ("creator", "uploader"):
                    if key in data:
                        data[key] = None
            result.append(record)
    return result


def discard_area_presence(model, field, value):
    """Occupancy is recomputed from scene geometry, never exported as token IDs."""
    if not isinstance(value, dict):
        return
    if model == "gravewright_maps.sceneobject" and field == "data":
        value.pop("areaPresence", None)
    elif model == "gravewright_maps.mapbuilderproject" and field == "generation":
        for record in value.get("objects", []):
            if isinstance(record, dict) and isinstance(record.get("data"), dict):
                record["data"].pop("areaPresence", None)


def omit_blueprint_audio(record):
    """Remove excluded audio dependencies from exported graph copies only."""
    from gravewright.maps.blueprint_runtime import detach_blueprint_sound
    from gravewright.maps.services import MapError

    data = record["fields"]
    if record["model"] == "gravewright_maps.sceneobject":
        candidates = [data.get("data", {})]
    else:
        candidates = [*data.get("document", {}).get("doors", []), *data.get("document", {}).get("decorations", []),
                      *data.get("document", {}).get("regions", [])]
        candidates.extend(row.get("data", {}) for row in data.get("generation", {}).get("objects", []))
        generated = data.get("generation", {}).get("dynamicDocument", {})
        candidates.extend(row for kind in ("doors", "decorations", "regions") for row in generated.get(kind, []))
    for candidate in candidates:
        blueprint = candidate.get("blueprint")
        if not isinstance(blueprint, dict):
            continue
        tracks = {
            node["trackId"] for graph in blueprint.get("graphs", {}).values()
            for node in graph["nodes"] if node.get("type") in ("sound", "soundControl")
        }
        for track_id in tracks:
            try:
                detach_blueprint_sound(blueprint, track_id)
            except MapError as error:
                raise AuthError("blueprint_audio_cleanup_limit") from error


def export_campaign(campaign, selected=None, *, include_files=True, snapshot=False, resource=None):
    """Build a bounded ZIP of allowlisted content and checksummed file payloads.
    
    Portable exports remove user-specific grants; snapshot mode additionally
    keeps chat and access records for restoration within the campaign."""
    selected = options(selected)
    with transaction.atomic():
        Campaign.objects.select_for_update().get(pk=campaign.pk)
        rows = records(campaign, selected, snapshot=snapshot)
        if resource is not None:
            if resource[0]=='gravewright_cards.deck':
                for record in rows:
                    if record['model']=='gravewright_cards.card':
                        record['fields'].update(zone='draw',owner=None,scene=None,revealed=False)
            from gravewright.compendiums.graph import select
            rows = select(rows, resource)
        payload = {
            "format": FORMAT,
            "version": 1,
            "campaign": {
                "id": str(campaign.pk),
                "name": campaign.name,
                "description": campaign.description,
                "system": campaign.system,
                "image_url": campaign.image_url,
                "cover": campaign.cover.name if include_files and resource is None else "",
            },
            "records": rows,
        }
        if resource is not None:payload['resource']={'model':resource[0],'id':resource[1]}
        files = {}
        if include_files and campaign.cover and resource is None:
            files[campaign.cover.name] = None
        for record in rows:
            model = apps.get_model(record["model"])
            for field in model._meta.fields:
                if isinstance(field, models.FileField) and record["fields"].get(
                    field.name
                ):
                    if include_files:
                        files[record["fields"][field.name]] = None
                    else:
                        record["fields"][field.name] = ""
        blobs = {}
        for name in files:
            with default_storage.open(name, "rb") as source:
                raw = source.read(MAX_EXPANDED + 1)
            if len(raw) > MAX_EXPANDED:
                raise AuthError("archive_too_large", 413)
            path = "files/" + hashlib.sha256(name.encode()).hexdigest()
            files[name] = path
            blobs[path] = raw
        payload["files"] = files
        raw = json.dumps(
            payload, cls=serializers.json.DjangoJSONEncoder, separators=(",", ":")
        ).encode()
        blobs["campaign.json"] = raw
        if sum(map(len, blobs.values())) > MAX_EXPANDED:
            raise AuthError("archive_too_large", 413)
        manifest = {
            "format": FORMAT,
            "version": 1,
            "files": {
                name: {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
                for name, raw in blobs.items()
            },
        }
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            for name, raw in blobs.items():
                archive.writestr(name, raw)
        if output.tell() > MAX_ARCHIVE:
            raise AuthError("archive_too_large", 413)
        return output.getvalue()


def read_archive(raw):
    """Validate ZIP paths, size bounds, checksums and content metadata before import."""
    if len(raw) > MAX_ARCHIVE:
        raise AuthError("archive_too_large", 413)
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
        entries = archive.infolist()
        if len(entries) > 50000 or sum(e.file_size for e in entries) > MAX_EXPANDED:
            raise ValueError()
        names = set()
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in entry.filename
                or entry.is_dir()
                or entry.flag_bits & 1
                or stat.S_ISLNK(entry.external_attr >> 16)
                or entry.filename.casefold() in names
            ):
                raise ValueError()
            names.add(entry.filename.casefold())
        if archive.getinfo("manifest.json").file_size > 8 * 1024 * 1024:
            raise ValueError()
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != FORMAT or manifest.get("version") != 1:
            raise ValueError()
        blobs = {}
        if set(archive.namelist()) != set(manifest["files"]) | {"manifest.json"}:
            raise ValueError()
        for name, spec in manifest["files"].items():
            blob = archive.read(name)
            if (
                len(blob) != spec["bytes"]
                or hashlib.sha256(blob).hexdigest() != spec["sha256"]
            ):
                raise ValueError()
            blobs[name] = blob
        if len(blobs["campaign.json"]) > 32 * 1024 * 1024:
            raise ValueError()
        payload = json.loads(blobs.pop("campaign.json"))
        if (
            payload["format"] != FORMAT
            or payload["version"] != 1
            or len(payload["records"]) > 100000
        ):
            raise ValueError()
        for record in payload["records"]:
            if record["model"] not in ALLOWED | SNAPSHOT_MODELS or not isinstance(
                record["fields"], dict
            ):
                raise ValueError()
        if set(payload["files"].values()) != set(blobs):
            raise ValueError()
        return payload, blobs
    except (
        KeyError,
        AttributeError,
        TypeError,
        ValueError,
        zipfile.BadZipFile,
        RuntimeError,
        OverflowError,
    ):
        raise AuthError("invalid_archive") from None


def rewrite(value, identifiers, paths):
    if isinstance(value, dict):
        return {
            identifiers.get(k, k): rewrite(v, identifiers, paths)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [rewrite(v, identifiers, paths) for v in value]
    if isinstance(value, str):
        if value in paths:
            return paths[value]
        if value in identifiers:
            return identifiers[value]
        # IDs are also embedded in authenticated asset URLs and rich-text pages.
        return re.sub(
            r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            lambda match: identifiers.get(match[0], match[0]),
            value,
        )
    return value


def preserve_shader_text(record, field_name, rewritten):
    """Shader names and GLSL are authored text, not embedded resource references."""
    original = record["fields"][field_name]
    candidates = []
    if (record["model"] == "gravewright_maps.sceneobject" and field_name == "data"
            and record["fields"].get("kind") == "shaders"):
        candidates.append((original, rewritten))
    elif record["model"] == "gravewright_maps.mapbuilderproject" and isinstance(original, dict) and isinstance(rewritten, dict):
        if field_name == "document":
            candidates.extend(zip(original.get("shaders", []), rewritten.get("shaders", [])))
        elif field_name == "generation":
            candidates.extend((before.get("data"), after.get("data"))
                              for before, after in zip(original.get("objects", []), rewritten.get("objects", []))
                              if isinstance(before, dict) and isinstance(after, dict) and before.get("kind") == "shaders")
            candidates.extend(zip(original.get("dynamicDocument", {}).get("shaders", []),
                                  rewritten.get("dynamicDocument", {}).get("shaders", [])))
    for before, after in candidates:
        if isinstance(before, dict) and isinstance(after, dict):
            for key in ("name", "source"):
                if isinstance(before.get(key), str):
                    after[key] = before[key]


def preserve_blueprint_values(before, after):
    """Typed values and signal names are authored text, never resource IDs."""
    if isinstance(before, list) and isinstance(after, list):
        for original, rewritten in zip(before, after):
            preserve_blueprint_values(original, rewritten)
    elif isinstance(before, dict) and isinstance(after, dict):
        if "automationMemory" in before:
            from gravewright.maps.blueprint_memory import clean_memory
            from gravewright.maps.services import MapError
            try:
                after["automationMemory"] = clean_memory(before["automationMemory"])
            except MapError:
                raise AuthError("invalid_archive") from None
        if "automationVariables" in before:
            from gravewright.maps.blueprint_variables import clean_store
            from gravewright.maps.services import MapError
            try:
                after["automationVariables"] = clean_store(before["automationVariables"])
            except MapError:
                raise AuthError("invalid_archive") from None
        if before.get("type") in ("getVariable", "setVariable", "compareValue", "emitEvent", "timer", "switch", "elementGroup"):
            if "name" in before:
                after["name"] = before["name"]
            if before.get("valueType") == "text":
                for key in ("default", "value", "expected"):
                    if key in before:
                        after[key] = before[key]
                if before.get("type") == "switch" and isinstance(before.get("cases"), list):
                    after["cases"] = deepcopy(before["cases"])
        if isinstance(before.get("graphs"), dict) and isinstance(after.get("graphs"), dict):
            # A signal name may itself contain text resembling a UUID.
            after["graphs"] = {key: rewrite_graph for key, rewrite_graph in
                               zip(before["graphs"], after["graphs"].values())}
            # Node identities are local authored labels. Rewriting UUID-looking
            # substrings would disconnect them from their preserved progress.
            for original, rewritten in zip(before["graphs"].values(), after["graphs"].values()):
                if not isinstance(original, dict) or not isinstance(rewritten, dict):
                    continue
                for source, target in zip(original.get("nodes", []), rewritten.get("nodes", [])):
                    if isinstance(source, dict) and isinstance(target, dict) and "id" in source:
                        target["id"] = source["id"]
                for source, target in zip(original.get("edges", []), rewritten.get("edges", [])):
                    if isinstance(source, dict) and isinstance(target, dict):
                        for key in ("from", "to"):
                            if key in source:
                                target[key] = source[key]
        if before.get("type") == "event" and isinstance(before.get("event"), str):
            after["event"] = before["event"]
        if before.get("type") == "showMessage" and isinstance(before.get("text"), str):
            after["text"] = before["text"]
        for key, value in before.items():
            if key not in ("automationVariables", "automationMemory") and key in after:
                preserve_blueprint_values(value, after[key])


def remap_omitted_bindings(record, field_name, rewritten, model_ids, inert_ids):
    """Keep excluded typed resources inert without rewriting authored text."""
    original = record["fields"].get(field_name)
    candidates = []
    source_destinations = {}
    if record["model"] == "gravewright_maps.sceneobject" and field_name == "data":
        candidates.append((original, rewritten, False))
    elif (record["model"] == "gravewright_maps.mapbuilderproject"
          and isinstance(original, dict) and isinstance(rewritten, dict)):
        if field_name == "document":
            source_destinations = {before["id"]: after["id"] for before, after in
                                   zip(original.get("regions", []), rewritten.get("regions", []))}
            for kind in ("doors", "decorations", "regions"):
                candidates.extend((before, after, kind == "regions")
                                  for before, after in zip(original.get(kind, []), rewritten.get(kind, [])))
        elif field_name == "generation":
            source_destinations = {before["id"]: after["id"] for before, after in zip(
                original.get("dynamicDocument", {}).get("regions", []), rewritten.get("dynamicDocument", {}).get("regions", []))}
            candidates.extend((before.get("data"), after.get("data"), False)
                              for before, after in zip(original.get("objects", []), rewritten.get("objects", []))
                              if isinstance(before, dict) and isinstance(after, dict))
            for kind in ("doors", "decorations", "regions"):
                candidates.extend((before, after, kind == "regions") for before, after in zip(
                    original.get("dynamicDocument", {}).get(kind, []), rewritten.get("dynamicDocument", {}).get(kind, [])))

    def binding(identifier, model):
        try:
            key = (model, str(uuid.UUID(identifier)))
        except (ValueError, TypeError, AttributeError):
            return identifier
        if key in model_ids:
            return str(model_ids[key])
        if key not in inert_ids:
            inert_ids[key] = str(uuid.uuid4())
        return inert_ids[key]

    for before, after, source_region in candidates:
        if not isinstance(before, dict) or not isinstance(after, dict):
            continue
        blueprint, copied = before.get("blueprint"), after.get("blueprint")
        if isinstance(blueprint, dict) and isinstance(copied, dict):
            graphs, copied_graphs = blueprint.get("graphs"), copied.get("graphs")
            for graph, copy in zip(graphs.values() if isinstance(graphs, dict) else (),
                                   copied_graphs.values() if isinstance(copied_graphs, dict) else ()):
                if not isinstance(graph, dict) or not isinstance(copy, dict):
                    continue
                for node, cloned in zip(graph.get("nodes", []), copy.get("nodes", [])):
                    if not isinstance(node, dict) or not isinstance(cloned, dict):
                        continue
                    if node.get("type") == "soundReference":
                        cloned["trackId"] = binding(node.get("trackId"), "gravewright_audio.track")
                    elif (node.get("type") == "elementGroup" and node.get("memberType") == "sound"
                          and isinstance(node.get("targetIds"), list)):
                        cloned["targetIds"] = [binding(identifier, "gravewright_audio.track")
                                               for identifier in node.get("targetIds", [])]
                    elif node.get("type") == "teleport":
                        cloned["destinationId"] = source_destinations.get(node.get("destinationId")) or binding(
                            node.get("destinationId"), "gravewright_maps.sceneobject")
                    elif node.get("type") == "showHandout":
                        cloned["journalId"] = binding(node.get("journalId"), "gravewright_journals.journal")
                    if node.get("type") in ("showMessage", "showHandout", "cameraFocus"):
                        audience = node.get("audience", {})
                        if audience.get("scope") == "users" and isinstance(audience.get("userIds"), list):
                            cloned["audience"]["userIds"] = [binding(identifier, "gravewright_accounts.user")
                                                              for identifier in audience["userIds"]]
        region, copied_region = (before, after) if source_region else (before.get("region"), after.get("region"))
        if not isinstance(region, dict) or not isinstance(copied_region, dict):
            continue
        if isinstance(region.get("arrivalGates"), list):
            copied_region["arrivalGates"] = [str(model_ids[("gravewright_tokens.token", identifier)])
                                             for identifier in region["arrivalGates"]
                                             if ("gravewright_tokens.token", identifier) in model_ids]
        filters, copied_filters = region.get("filters"), copied_region.get("filters")
        if isinstance(filters, dict) and isinstance(copied_filters, dict):
            for key, model in (("actorIds", "gravewright_actors.actor"), ("tokenIds", "gravewright_tokens.token")):
                if isinstance(filters.get(key), list):
                    copied_filters[key] = [binding(identifier, model) for identifier in filters[key]]


def import_campaign(raw, user, title="", *, target=None, merge=False):
    """Import a validated content graph, remapping identifiers and stored file paths."""
    payload, blobs = read_archive(raw)
    name = title or payload["campaign"]["name"]
    if not isinstance(name, str) or not 2 <= len(name.strip()) <= 80:
        raise AuthError("invalid_container_name")
    if target is None or merge:
        payload["records"] = [
            r for r in payload["records"] if r["model"] not in SNAPSHOT_MODELS
        ]
    created_files = []
    try:
        with transaction.atomic():
            if target:
                campaign = Campaign.objects.select_for_update().get(pk=target.pk)
                # Remove only native content, preserving members, codes and backup history.
                for label in ([] if merge else reversed(list(ALLOWED | SNAPSHOT_MODELS))):
                    model = apps.get_model(label)
                    if any(f.name == "campaign" for f in model._meta.fields):
                        model.objects.filter(campaign=campaign).delete()
            else:
                campaign = Campaign.objects.create(owner=user, name=name.strip())
                Membership.objects.create(campaign=campaign, user=user, role="gm")
            if not merge:
                campaign.name = name.strip()
                campaign.description = str(payload["campaign"].get("description", ""))[:500]
                campaign.system = str(
                    payload["campaign"].get("system", default_system_id())
                )[:120]
                campaign.image_url = str(payload["campaign"].get("image_url", ""))[:2048]
            identifiers = {str(payload["campaign"]["id"]): str(campaign.pk)}
            model_ids = {}
            for record in payload["records"]:
                model = apps.get_model(record["model"])
                key = (record["model"], str(record["pk"]))
                if key in model_ids:
                    raise AuthError("invalid_archive")
                new_id = (
                    str(record["pk"])
                    if target and not merge
                    else str(uuid.uuid4())
                    if isinstance(model._meta.pk, models.UUIDField)
                    else None
                )
                model_ids[key] = new_id
                if new_id:
                    if isinstance(model._meta.pk, models.UUIDField):
                        identifiers[str(record["pk"])] = new_id
                if "block_id" in record["fields"]:
                    identifiers[str(record["fields"]["block_id"])] = (
                        str(record["fields"]["block_id"])
                        if target and not merge
                        else str(uuid.uuid4())
                    )
            inert_ids = {}
            paths = {}
            for old, archive_path in payload["files"].items():
                suffix = PurePosixPath(old).suffix.lower()
                if suffix not in {
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".webp",
                    ".gif",
                    ".pdf",
                    ".avif",
                    ".bin", ".mp3", ".ogg", ".wav", ".flac", ".zip",
                }:
                    raise AuthError("invalid_archive")
                path = default_storage.save(
                    f"imports/{campaign.pk}/{uuid.uuid4().hex}{suffix}",
                    ContentFile(blobs[archive_path]),
                )
                created_files.append(path)
                paths[old] = path
            if not merge:campaign.cover = paths.get(payload["campaign"].get("cover"), "")
            campaign.save()
            pending = list(payload["records"])
            while pending:
                progress = False
                for record in pending[:]:
                    model = apps.get_model(record["model"])
                    fields = record["fields"]
                    valid_fields = {
                        f.name: f for f in model._meta.fields if not f.primary_key
                    }
                    if set(fields) - valid_fields.keys():
                        raise AuthError("invalid_archive")
                    kwargs = {}
                    defer = False
                    for field_name, value in fields.items():
                        field = valid_fields[field_name]
                        if field.is_relation and value is not None:
                            label = field.related_model._meta.label_lower
                            if label == "gravewright_campaigns.campaign":
                                value = campaign.pk
                            elif label == "gravewright_accounts.user":
                                value = value if target and not merge else user.pk
                            else:
                                key = (label, str(value))
                                if key not in model_ids:
                                    if (record["model"] == "gravewright_maps.mapasset"
                                            and field_name == "generated_for"):
                                        raise AuthError("invalid_archive")
                                    elif field.null:
                                        value = None
                                    else:
                                        raise AuthError("invalid_archive")
                                elif model_ids[key] is None or any(
                                    r["model"] == label and str(r["pk"]) == str(value)
                                    for r in pending
                                ):
                                    defer = True
                                    break
                                else:
                                    value = model_ids[key]
                            kwargs[field.attname] = value
                        elif isinstance(field, models.FileField):
                            kwargs[field_name] = paths.get(value, "")
                        elif field_name == "permissions":
                            kwargs[field_name] = value if target and not merge else {}
                        elif record["model"] == "gravewright_maps.blueprinttemplate" and field_name == "definition":
                            from gravewright.maps.blueprint_templates import clean_definition
                            from gravewright.maps.services import MapError
                            try:
                                kwargs[field_name] = clean_definition(value)
                            except MapError:
                                raise AuthError("invalid_archive") from None
                        else:
                            kwargs[field_name] = rewrite(value, identifiers, paths)
                            preserve_shader_text(record, field_name, kwargs[field_name])
                            if record["model"] in ("gravewright_maps.scene", "gravewright_maps.sceneobject",
                                                   "gravewright_maps.mapbuilderproject"):
                                preserve_blueprint_values(value, kwargs[field_name])
                                remap_omitted_bindings(record, field_name, kwargs[field_name], model_ids, inert_ids)
                                discard_area_presence(record["model"], field_name, kwargs[field_name])
                            if (record["model"] == "gravewright_maps.mapbuilderproject"
                                    and field_name == "document" and isinstance(value, dict)
                                    and isinstance(value.get("assets"), list)):
                                # Family names are authored labels, even when they contain an ID.
                                for original, rewritten in zip(value["assets"], kwargs[field_name]["assets"]):
                                    if isinstance(original, dict) and isinstance(original.get("family"), str):
                                        rewritten["family"] = original["family"]
                    if defer:
                        continue
                    pkfield = model._meta.pk
                    if pkfield.is_relation:
                        key = (
                            pkfield.related_model._meta.label_lower,
                            str(record["pk"]),
                        )
                        if pkfield.related_model is Campaign:
                            kwargs[pkfield.attname] = campaign.pk
                        elif key not in model_ids:
                            raise AuthError("invalid_archive")
                        elif any(
                            r["model"] == key[0] and str(r["pk"]) == key[1]
                            for r in pending
                        ):
                            continue
                        else:
                            kwargs[pkfield.attname] = model_ids[key]
                    elif (target and not merge) or isinstance(pkfield, models.UUIDField):
                        kwargs["pk"] = model_ids[(record["model"], str(record["pk"]))]
                    obj = model(**kwargs)
                    obj.save(force_insert=True)
                    model_ids[(record["model"], str(record["pk"]))] = obj.pk
                    pending.remove(record)
                    progress = True
                if not progress:
                    raise AuthError("invalid_archive")
            from gravewright.maps.surface_validation import validate_campaign_surfaces
            from gravewright.maps.blueprint_actions import validate_campaign_sprites
            from gravewright.maps.builder_services import validate_imported_projects
            from gravewright.maps.services import MapError
            try:
                validate_campaign_surfaces(campaign)
                validate_campaign_sprites(campaign)
                validate_imported_projects(campaign)
                from gravewright.maps.models import Scene
                from gravewright.maps.regions import MAX_REGIONS, baseline, presence_rows
                imported_scenes = [pk for (model, _), pk in model_ids.items() if model == "gravewright_maps.scene"]
                for scene in Scene.objects.filter(campaign=campaign, pk__in=imported_scenes):
                    listeners = presence_rows(scene)
                    objects = [row for row in listeners if row.kind == "images"]
                    if objects and len(listeners) > MAX_REGIONS:
                        raise MapError("The scene has too many presence regions.")
                    for row in baseline(scene, objects):
                        row.version += 1
                        row.save(update_fields=["data", "version"])
            except MapError:
                raise AuthError("invalid_archive") from None
            if merge:
                campaign.imported_references=model_ids
                root=payload.get('resource')
                if root:
                    key=(root.get('model'),str(root.get('id')))
                    if key not in model_ids:raise AuthError('invalid_archive')
                    campaign.imported_resource=model_ids[key]
            return campaign
    except Exception as error:
        for path in created_files:
            default_storage.delete(path)
        if isinstance(
            error,
            (
                ValidationError,
                IntegrityError,
                DataError,
                ValueError,
                TypeError,
                KeyError,
            ),
        ):
            raise AuthError("invalid_archive") from None
        raise
