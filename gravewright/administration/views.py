import hashlib
import io
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from functools import wraps

from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, JsonResponse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from gravewright.accounts.services import AuthError
from gravewright.accounts.views import read_json
from gravewright.campaigns.services import get_campaign
from gravewright.campaigns.views import authenticated

from . import archives, automatic_updates
from .models import AuditEvent, HostSettings, Snapshot
from .updates import CoreUpdateService


def owner(view):
    @wraps(view)
    @authenticated
    def wrapped(request, *args, **kwargs):
        if request.user.role != "owner":
            raise AuthError("owner_required", 403)
        return view(request, *args, **kwargs)

    return wrapped


def audit(request, action, **detail):
    if not settings.ADMINISTRATIVE_AUDIT_ENABLED:
        return
    AuditEvent.objects.filter(created_at__lt=timezone.now() - timedelta(days=settings.ADMINISTRATIVE_AUDIT_RETENTION_DAYS)).delete()
    AuditEvent.objects.create(user=request.user, action=action, detail=detail)


@require_GET
@owner
def status(request):
    return JsonResponse(
        {
            "updates": {**CoreUpdateService().status(), "automatic": automatic_updates.status()},
            "features": {"clone": settings.CAMPAIGN_CLONE_ENABLED, "import": True},
        }
    )


@require_GET
@owner
def diagnostics(request):
    from gravewright.accounts.models import User
    from gravewright.campaigns.models import Campaign

    return JsonResponse(
        {
            "metrics": {
                "database": {
                    "campaigns": Campaign.objects.count(),
                    "users": User.objects.count(),
                    "backups": Snapshot.objects.count(),
                }
            },
            "recent_events": [
                {"ts": e.created_at.timestamp(), "event": e.action, "fields": e.detail}
                for e in AuditEvent.objects.all()[:100]
            ],
        },
        headers={"Cache-Control": "no-store"},
    )


@require_POST
@owner
def updates(request, action):
    if action == "apply":
        data = read_json(request)
        if set(data) != {"version"} or not isinstance(data["version"], str):
            raise AuthError("invalid_input")
        result = automatic_updates.request_update(data["version"])
        audit(request, "updates.apply", version=data["version"])
        return JsonResponse(result, status=202)
    if action == "channel":
        data = read_json(request)
        if set(data) != {"channel"} or data["channel"] not in (
            "stable",
            "testing",
            "dev",
        ):
            raise AuthError("invalid_channel")
        HostSettings.objects.update_or_create(
            pk=1, defaults={"channel": data["channel"], "update_status": {}}
        )
        audit(request, "updates.channel", channel=data["channel"])
        return JsonResponse(CoreUpdateService().status())
    if action != "check":
        raise AuthError("not_found", 404)
    result = CoreUpdateService().check()
    audit(request, "updates.check", status=result["status"])
    return JsonResponse(result)


@require_POST
@owner
def clone(request, campaign_id, action):
    if not settings.CAMPAIGN_CLONE_ENABLED:
        raise AuthError("feature_disabled", 403)
    campaign = get_campaign(request.user, campaign_id, manage=True)
    data = read_json(request)
    selected = archives.options(data.get("options"))
    rows = archives.records(campaign, selected)
    summary = {
        key: sum(r["model"] in labels for r in rows)
        if key != "settings"
        else selected[key]
        for key, labels in archives.GROUPS.items()
    }
    if action == "preview":
        return JsonResponse({"campaignId": str(campaign.pk), "summary": summary})
    if action != "create":
        raise AuthError("invalid_action")
    result = archives.import_campaign(
        archives.export_campaign(campaign, selected, include_files=False),
        request.user,
        data.get("title", ""),
    )
    audit(request, "campaign.clone", source=str(campaign.pk), campaign=str(result.pk))
    return JsonResponse({"campaignId": str(result.pk), "summary": summary})


@require_POST
@owner
def import_campaign(request):
    upload = request.FILES.get("archive")
    if upload is None:
        raise AuthError("archive_required")
    result = archives.import_campaign(
        upload.read(archives.MAX_ARCHIVE + 1),
        request.user,
        request.POST.get("title", ""),
    )
    audit(request, "campaign.import", campaign=str(result.pk))
    return JsonResponse({"campaignId": str(result.pk)})


@require_GET
@authenticated
def export_campaign(request, campaign_id):
    if not settings.CAMPAIGN_EXPORT_ENABLED:
        raise AuthError("feature_disabled", 403)
    campaign = get_campaign(request.user, campaign_id, manage=True)
    raw = archives.export_campaign(campaign)
    audit(request, "campaign.export", campaign=str(campaign.pk))
    return FileResponse(
        io.BytesIO(raw),
        as_attachment=True,
        filename=f"gravewright-{campaign.pk}.zip",
        content_type="application/zip",
    )


def snapshot_data(row):
    return {
        "id": str(row.pk),
        "name": row.name,
        "description": row.description,
        "createdAt": row.created_at.isoformat(),
        "sha256": row.digest,
    }


@require_http_methods(["GET", "POST"])
@authenticated
def snapshots(request, campaign_id):
    if not settings.CAMPAIGN_SNAPSHOTS_ENABLED:
        raise AuthError("feature_disabled", 403)
    campaign = get_campaign(request.user, campaign_id, manage=True)
    if request.method == "GET":
        return JsonResponse(
            {
                "snapshots": [
                    snapshot_data(row)
                    for row in Snapshot.objects.filter(campaign=campaign).order_by(
                        "-created_at"
                    )
                ]
            }
        )
    data = read_json(request)
    name = data.get("name", "")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        raise AuthError("invalid_name")
    raw = archives.export_campaign(campaign, snapshot=True)
    row = Snapshot(
        campaign=campaign,
        name=name.strip(),
        description=str(data.get("description", ""))[:1000],
        digest=hashlib.sha256(raw).hexdigest(),
    )
    row.archive.save(f"{row.pk}.zip", ContentFile(raw), save=False)
    try:
        row.save()
    except Exception:
        row.archive.delete(save=False)
        raise
    with transaction.atomic():
        from gravewright.campaigns.models import Campaign
        Campaign.objects.select_for_update().get(pk=campaign.pk)
        expired = list(Snapshot.objects.filter(campaign=campaign).order_by('-created_at', '-pk')[settings.CAMPAIGN_SNAPSHOT_RETENTION:])
        for old in expired:
            storage, path = old.archive.storage, old.archive.name
            old.delete()
            transaction.on_commit(lambda storage=storage, path=path: storage.delete(path))
    audit(request, "snapshot.create", campaign=str(campaign.pk), snapshot=str(row.pk))
    return JsonResponse(snapshot_data(row), status=201)


@require_POST
@authenticated
@transaction.atomic
def snapshot_action(request, campaign_id, snapshot_id, action):
    if not settings.CAMPAIGN_SNAPSHOTS_ENABLED:
        raise AuthError("feature_disabled", 403)
    campaign = get_campaign(request.user, campaign_id, manage=True)
    from gravewright.campaigns.models import Campaign
    Campaign.objects.select_for_update().get(pk=campaign.pk)
    row = Snapshot.objects.filter(campaign=campaign, pk=snapshot_id).first()
    if row is None:
        raise AuthError("not_found", 404)
    data = read_json(request)
    if action not in ("preview", "restore", "delete"):
        raise AuthError("invalid_action")
    if action != "preview" and data.get("confirm") != action.upper():
        raise AuthError("confirmation_required")
    if action == "delete":
        path = row.archive.name
        row.delete()
        transaction.on_commit(lambda: row.archive.storage.delete(path))
    else:
        with row.archive.open("rb") as source:
            raw = source.read(archives.MAX_ARCHIVE + 1)
        if hashlib.sha256(raw).hexdigest() != row.digest:
            raise AuthError("invalid_archive")
        payload, _ = archives.read_archive(raw)
        if action == "preview":
            return JsonResponse(
                {
                    "snapshot": snapshot_data(row),
                    "preview": {
                        "records": len(payload["records"]),
                        "files": len(payload["files"]),
                    },
                }
            )
        from django.utils import timezone

        from gravewright.realtime.models import PresenceConnection

        if PresenceConnection.objects.filter(
            membership__campaign=campaign, expires_at__gt=timezone.now()
        ).exists():
            raise AuthError("campaign_in_use", 409)
        archives.import_campaign(raw, request.user, target=campaign)
    audit(
        request,
        f"snapshot.{action}",
        campaign=str(campaign.pk),
        snapshot=str(snapshot_id),
    )
    return JsonResponse({"ok": True})


@require_GET
@owner
def preferences(request):
    from .preferences import read
    return JsonResponse(read(),headers={'Cache-Control':'no-store'})


@require_POST
@owner
def update_preferences(request,section):
    from .preferences import update
    result=update(request.user,section,read_json(request))
    audit(request,'settings.'+section)
    return JsonResponse(result,headers={'Cache-Control':'no-store'})


@require_GET
def public_privacy(request):
    from .preferences import public_privacy as read
    return JsonResponse(read(),headers={'Cache-Control':'no-store'})
