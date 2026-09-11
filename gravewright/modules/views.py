"""Django transport for the original signed browser-module contract."""

import json
import mimetypes
from datetime import timedelta
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from django.conf import settings
from django.db import transaction
from django.http import FileResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from gravewright.accounts.views import read_json
from gravewright.administration.views import audit, owner
from gravewright.campaigns.models import Membership
from gravewright.campaigns.services import get_campaign
from gravewright.campaigns.views import authenticated

from .models import ContextLease, Package
from .packages import MAX_ARCHIVE, ModuleFailure, compatible, host, safe_path


class HTTPSRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https":
            raise ModuleFailure("permission_denied")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url, limit):
    """Fetch a bounded catalog/archive while keeping redirects on HTTPS."""
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ModuleFailure("invalid_data")
    try:
        with build_opener(HTTPSRedirects()).open(
            Request(url, headers={"User-Agent": "Gravewright-Marketplace/1"}),
            timeout=30,
        ) as response:
            raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ModuleFailure("invalid_data")
        return raw
    except ModuleFailure:
        raise
    except Exception:
        raise ModuleFailure("unavailable") from None


def catalog(engine):
    """Validate the configured publisher catalog and apply its signed revocations."""
    if not settings.GRAVEWRIGHT_MARKETPLACE_URL:
        raise ModuleFailure("unavailable")
    try:
        rows = json.loads(
            download(settings.GRAVEWRIGHT_MARKETPLACE_URL, 2 * 1024 * 1024)
        )
    except ValueError:
        raise ModuleFailure("invalid_data") from None
    if not isinstance(rows, list) or len(rows) > 5000:
        raise ModuleFailure("invalid_data")
    seen = set()
    for record in rows:
        engine.verify(record, require_compatible=False)
        identity = (record["id"], record["version"])
        if identity in seen:
            raise ModuleFailure("invalid_data")
        seen.add(identity)
    for record in rows:
        if record.get("status") == "revoked":
            engine.revoke(record)
    return rows


@require_GET
@owner
def marketplace_status(request):
    return JsonResponse(
        {
            "catalogConfigured": bool(settings.GRAVEWRIGHT_MARKETPLACE_URL),
            "trustedKeysConfigured": bool(host().keys),
            "sdk": "1.0.0",
        }
    )


@require_GET
@owner
def marketplace(request):
    return JsonResponse(
        [
            r
            for r in catalog(host())
            if compatible(r["sdk"]) and r.get("status") != "revoked"
        ],
        safe=False,
    )


@require_POST
@owner
def install(request):
    data = read_json(request)
    if set(data) != {"id", "version"} or any(
        not isinstance(v, str) for v in data.values()
    ):
        raise ModuleFailure("invalid_data")
    engine = host()
    record = next(
        (
            r
            for r in catalog(engine)
            if r["id"] == data["id"] and r["version"] == data["version"]
        ),
        None,
    )
    if record is None:
        raise ModuleFailure("not_found")
    manifest = engine.install(record, download(record["download"], MAX_ARCHIVE))
    audit(request, "module.install", module=manifest["id"], version=manifest["version"])
    return JsonResponse(manifest)


@require_GET
@authenticated
def installed(request):
    return JsonResponse(
        [
            {**row.manifest, "revoked": row.revoked}
            for row in Package.objects.order_by("module_id", "version")
        ],
        safe=False,
    )


@require_http_methods(["GET", "POST"])
@authenticated
def state(request, table_id):
    get_campaign(request.user, table_id, manage=request.method == "POST")
    engine = host()
    if request.method == "POST":
        data = read_json(request)
        if set(data) != {"modules", "replacements", "expectedRevision"}:
            raise ModuleFailure("invalid_data")
        value = engine.configure(
            table_id, data["modules"], data["replacements"], data["expectedRevision"]
        )
        audit(
            request, "modules.configure", table=str(table_id), modules=data["modules"]
        )
        # The runtime also reconciles after reconnect; state never depends on delivery.
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        async_to_sync(get_channel_layer().group_send)(
            f"table.{table_id.hex}", {"type": "room.modules", "state": value}
        )
    else:
        value = engine.state(table_id)
    value["role"] = Membership.objects.get(campaign_id=table_id, user=request.user).role
    return JsonResponse(value)


@require_POST
@authenticated
def acknowledge(request, table_id):
    get_campaign(request.user, table_id)
    if (
        read_json(request).get("moduleSetRevision")
        != host().state(table_id)["moduleSetRevision"]
    ):
        raise ModuleFailure("stale_context")
    return JsonResponse({"ok": True})


def identity(request, table_id, module_id, data, *, check=True):
    """Bind calls to authenticated membership, activation revision and mount lease.

    The optional scene must be visible to the same user. ``check=False`` is used
    only while opening a lease; normal operations also require a live matching row.
    """
    get_campaign(request.user, table_id)
    for key in ("mountId", "moduleSetRevision"):
        if not isinstance(data.get(key), str) or not 1 <= len(data[key]) <= (
            128 if key == "mountId" else 32
        ):
            raise ModuleFailure("invalid_data")
    engine = host()
    engine.check(table_id, module_id, data["moduleSetRevision"])
    scene = data.get("sceneId")
    if scene is not None:
        from gravewright.journals.services import member
        from gravewright.maps.services import scene as get_scene

        try:
            scene = get_scene(scene, member(table_id, request.user.pk)).pk
        except Exception:
            raise ModuleFailure("not_found") from None
    query = ContextLease.objects.filter(
        campaign_id=table_id,
        user=request.user,
        module_id=module_id,
        mount=data["mountId"],
    )
    if check:
        lease = query.first()
        if (
            not lease
            or lease.closed
            or lease.expires_at <= timezone.now()
            or lease.revision != data["moduleSetRevision"]
            or lease.scene_id != scene
        ):
            raise ModuleFailure("stale_context")
        query.update(expires_at=timezone.now() + timedelta(minutes=30))
    return engine, query, scene


@require_POST
@authenticated
@transaction.atomic
def context(request, table_id, module_id):
    """Open/renew a 30-minute mount lease or permanently close that mount ID."""
    data = read_json(request)
    if set(data) - {"action", "mountId", "moduleSetRevision", "sceneId"} or data.get(
        "action"
    ) not in ("open", "close"):
        raise ModuleFailure("invalid_data")
    if data["action"] == "close":
        get_campaign(request.user, table_id)
        ContextLease.objects.filter(
            campaign_id=table_id,
            user=request.user,
            module_id=module_id,
            mount=data.get("mountId"),
        ).update(closed=True)
    else:
        _, query, scene = identity(request, table_id, module_id, data, check=False)
        lease = query.first()
        if lease and (
            lease.closed
            or lease.revision != data["moduleSetRevision"]
            or lease.scene_id != scene
        ):
            raise ModuleFailure("stale_context")
        ContextLease.objects.filter(expires_at__lt=timezone.now()).delete()
        if ContextLease.objects.count() >= 10000:
            raise ModuleFailure("unavailable")
        ContextLease.objects.update_or_create(
            campaign_id=table_id,
            user=request.user,
            module_id=module_id,
            mount=data["mountId"],
            defaults={
                "revision": data["moduleSetRevision"],
                "scene_id": scene,
                "expires_at": timezone.now() + timedelta(minutes=30),
            },
        )
    return JsonResponse({"ok": True})


@require_POST
@authenticated
@transaction.atomic
def storage(request, table_id, module_id):
    data = read_json(request)
    if (
        set(data)
        - {
            "scope",
            "action",
            "key",
            "value",
            "expectedRevision",
            "moduleSetRevision",
            "mountId",
            "sceneId",
        }
        or data.get("scope") not in ("user", "table")
        or data.get("action") not in ("get", "list", "set", "delete")
    ):
        raise ModuleFailure("invalid_data")
    get_campaign(
        request.user,
        table_id,
        manage=data["scope"] == "table" and data["action"] in ("set", "delete"),
    )
    engine, _, _ = identity(request, table_id, module_id, data)
    return JsonResponse(
        {
            "value": engine.storage(
                table_id,
                module_id,
                str(request.user.pk) if data["scope"] == "user" else "",
                data["moduleSetRevision"],
                data["action"],
                data.get("key", ""),
                data.get("value"),
                data.get("expectedRevision"),
            )
        }
    )


@require_GET
@authenticated
def asset(request, module_id, version, digest, asset):
    """Serve authenticated package bytes after checking their signed archive copy."""
    row = Package.objects.filter(
        module_id=module_id, version=version, digest=digest, revoked=False
    ).first()
    if not row:
        raise ModuleFailure("not_found")
    name = str(safe_path(asset))
    engine = host()
    engine.verify_installed(row, name)
    path = engine.directory / "packages" / module_id / version / digest / name
    return FileResponse(
        path.open("rb"),
        content_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        headers={
            "Cache-Control": "private, no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@require_POST
@authenticated
@transaction.atomic
def call(request, table_id, module_id):
    """Validate and dispatch an original SDK operation with JSON or binary transport."""
    if request.content_type == "multipart/form-data":
        try:
            data = json.loads(request.POST["metadata"])
            upload = request.FILES["file"]
            data["payload"]["file"] = {
                "name": upload.name,
                "contentType": upload.content_type,
                "size": upload.size,
            }
        except KeyError, ValueError, TypeError:
            raise ModuleFailure("invalid_data") from None
    else:
        data, upload = read_json(request), None
    if not isinstance(data, dict) or set(data) - {
        "name",
        "payload",
        "moduleSetRevision",
        "mountId",
        "sceneId",
    }:
        raise ModuleFailure("invalid_data")
    engine, _, scene = identity(request, table_id, module_id, data)
    contract = engine.contracts.registry["operations"].get(data.get("name"))
    if not contract or contract["scope"] == "local":
        raise ModuleFailure("unavailable")
    engine.contracts.validate(contract["input"], data.get("payload"))
    if contract["scope"] == "scene" and scene is None:
        raise ModuleFailure("stale_context")
    from .operations import invoke

    result = invoke(request, table_id, scene, data["name"], data["payload"], upload)
    if contract.get("transport") == "binary":
        return result
    engine.contracts.validate(contract["output"], result)
    return JsonResponse({"value": result})
