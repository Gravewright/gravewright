"""Authenticated binary domain operations over the native upload/file handlers."""
import json
from copy import copy

from django.http import Http404, JsonResponse, QueryDict
from django.views.decorators.http import require_POST

from gravewright.campaigns.views import authenticated
from gravewright.journals.services import JournalError, identifier, member, writable
from gravewright.maps.services import MapError, manage
from .packages import ModuleFailure

OPERATIONS = {
    ("maps", "upload"), ("maps", "importUniversalVtt"),
    ("library", "upload"), ("library", "download"),
    ("actors", "uploadAsset"), ("actors", "uploadImage"), ("actors", "downloadAsset"),
    ("audio", "upload"), ("cards", "uploadAsset"),
    ("journals", "uploadAsset"), ("journals", "downloadAsset"),
}


def invoke(request, campaign_id, domain, method, payload, upload=None, *, request_id=None, scene_id=None):
    """Retain campaign/mount scope and each file handler's ownership and limits.

    Uploads create files and normally have no retry receipt. Universal VTT import
    uses its native request UUID. No outer transaction encloses image decoding,
    map tiling, media inspection or the handlers' file-cleanup boundaries.
    """
    if (domain, method) not in OPERATIONS:
        raise ModuleFailure("unavailable")
    if not isinstance(payload, dict):
        raise ModuleFailure("invalid_data")
    who = member(campaign_id, request.user.pk)
    campaign_id = who.campaign_id
    if scene_id is not None and any(payload.get(key) is not None and str(payload[key]) != str(scene_id)
                                    for key in ("sceneId", "mapId")):
        raise ModuleFailure("stale_context")
    target = copy(request)
    target.POST = QueryDict(mutable=True)
    for key, value in payload.items():
        if value is not None and key not in {"file", "sceneId", "mapId", "requestId"}:
            target.POST[key] = json.dumps(value) if isinstance(value, (dict, list, bool)) else str(value)
    if method.startswith("download"):
        target.method = "GET"
        asset_id = identifier(payload.get("id"))
        if domain == "actors":
            from gravewright.actors.models import Asset
            from gravewright.actors.views import asset
            row = Asset.objects.filter(pk=asset_id, campaign_id=campaign_id).first()
            if row is None:
                raise ModuleFailure("not_found")
            return asset(target, asset_id)
        if domain == "journals":
            from gravewright.journals.models import Asset
            from gravewright.journals.views import asset
            if not Asset.objects.filter(pk=asset_id, journal__campaign_id=campaign_id).exists():
                raise ModuleFailure("not_found")
            return asset(target, asset_id)
        kind = payload.get("kind", "image")
        if kind == "image":
            from gravewright.maps.models import MapAsset
            from gravewright.maps.assets import file
            if not MapAsset.objects.filter(pk=asset_id, campaign_id=campaign_id).exists():
                raise ModuleFailure("not_found")
            return file(target, asset_id)
        if kind == "audio":
            from gravewright.audio.models import Track
            from gravewright.table.media import audio_file
            # The file library only lists audio to its GM; keep that boundary.
            manage(who)
            if not Track.objects.filter(pk=asset_id, campaign_id=campaign_id).exists():
                raise ModuleFailure("not_found")
            return audio_file(target, asset_id)
        if kind == "pdf":
            from gravewright.actors.models import Asset
            from gravewright.actors.views import asset
            manage(who)
            if not Asset.objects.filter(pk=asset_id, campaign_id=campaign_id, kind="pdf").exists():
                raise ModuleFailure("not_found")
            return asset(target, asset_id)
        raise ModuleFailure("invalid_data")
    writable(who)
    if upload is None:
        raise ModuleFailure("invalid_data")
    if (domain, method) not in {("actors", "uploadImage"), ("journals", "uploadAsset")}:
        manage(who)
    if domain == "maps" and method == "importUniversalVtt":
        from gravewright.maps.universal_vtt_views import import_map
        target.POST["request_id"] = str(identifier(request_id))
        response = import_map(target, campaign_id)
    elif domain == "maps":
        from gravewright.maps.views import upload as upload_map
        target._files = request.FILES.copy()
        target._files.setlist("map", [upload])
        response = upload_map(target, campaign_id)
    elif domain == "library":
        from gravewright.maps.assets import upload as upload_library
        if "folderId" in payload:
            target.POST["folder_id"] = payload["folderId"] or ""
        response = upload_library(target, campaign_id)
    elif domain == "actors":
        from gravewright.actors.views import upload as upload_actor
        if method == "uploadImage":
            from gravewright.actors.services import get
            get(payload.get("id"), who, True)
            if payload.get("kind") not in {"portrait", "token"}:
                raise ModuleFailure("invalid_data")
            target.POST["actorId"] = payload["id"]
        else:
            # An asset upload never turns into an actor image through metadata.
            target.POST.pop("actorId", None)
            target.POST.pop("kind", None)
        if "folderId" in payload:
            target.POST["folder_id"] = payload["folderId"] or ""
        response = upload_actor(target, campaign_id)
    elif domain in {"audio", "cards"}:
        from gravewright.table.media import upload as upload_media
        if "folderId" in payload:
            target.POST["folder_id"] = payload["folderId"] or ""
        response = upload_media(target, campaign_id, "audio" if domain == "audio" else "card-asset")
    else:
        from gravewright.journals.services import get
        from gravewright.journals.views import upload as upload_journal
        get(payload.get("journalId"), who, True)
        target.POST["campaign_id"] = str(campaign_id)
        target.POST["journal_id"] = payload["journalId"]
        response = upload_journal(target)
    if response.status_code >= 400:
        try:
            body = json.loads(response.content)
        except (ValueError, UnicodeError):
            body = {}
        code = {403: "permission_denied", 404: "not_found", 409: "conflict"}.get(response.status_code, "invalid_data")
        raise ModuleFailure(code,
                            body.get("message") or body.get("error") or "Invalid file operation.")
    return JsonResponse({"value": json.loads(response.content)}, status=response.status_code)


@require_POST
@authenticated
def call(request, table_id, module_id=None):
    """Share binary APIs with native pages and activation/lease-bound modules."""
    try:
        if request.content_type == "multipart/form-data":
            raw = request.POST.get("metadata", "")
            if len(raw.encode("utf-8")) > 1_100_000:
                raise ModuleFailure("invalid_data")
            data = json.loads(raw)
            upload = request.FILES.get("file")
        else:
            from gravewright.accounts.views import read_json
            data, upload = read_json(request), None
        allowed = {"domain", "method", "payload", "requestId"}
        if module_id is not None:
            allowed |= {"mountId", "moduleSetRevision", "sceneId"}
        if not isinstance(data, dict) or set(data) - allowed:
            raise ModuleFailure("invalid_data")
        scene_id = None
        if module_id is not None:
            from .views import identity
            _, _, scene_id = identity(request, table_id, module_id, data)
        response = invoke(request, table_id, data.get("domain"), data.get("method"), data.get("payload", {}),
                          upload, request_id=data.get("requestId"), scene_id=scene_id)
        response["Cache-Control"] = "private, no-store"
        return response
    except ModuleFailure:
        raise
    except Http404:
        raise ModuleFailure("not_found") from None
    except (JournalError, MapError) as error:
        code = "permission_denied" if error.code in {"forbidden", "not_a_member", "gm_required"} else "not_found" if error.code == "not_found" else "conflict" if error.code == "conflict" else "invalid_data"
        raise ModuleFailure(code, str(error)) from None
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise ModuleFailure("invalid_data") from None
