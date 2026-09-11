"""Portable Django campaign archives. Only the explicit content graph is accepted."""

import hashlib
import io
import json
import re
import stat
import uuid
import zipfile
from pathlib import PurePosixPath

from django.apps import apps
from django.core import serializers
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import DataError, IntegrityError, models, transaction

from gravewright.accounts.services import AuthError
from gravewright.campaigns.models import Campaign, Membership

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
}
SNAPSHOT_MODELS = {
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
            data = record["fields"]
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
                    payload["campaign"].get("system", "gravewright-pdf-system")
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
                                    if field.null:
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
                        else:
                            kwargs[field_name] = rewrite(value, identifiers, paths)
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
