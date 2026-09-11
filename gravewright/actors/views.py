import uuid
from io import BytesIO
from pathlib import Path

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from PIL import Image, ImageOps, UnidentifiedImageError

from gravewright.journals.services import JournalError
from gravewright.maps.services import MapError

from . import services
from .models import Asset


def publish(campaign):
    layer = get_channel_layer()
    for kind in ("room.actors", "room.tokens", "room.map_layers"):
        async_to_sync(layer.group_send)(f"table.{campaign.hex}", {"type": kind})


@require_GET
def state(request, campaign_id):
    if not request.user.is_authenticated:
        raise Http404
    try:
        return JsonResponse(services.state(campaign_id, request.user.pk))
    except JournalError, MapError:
        raise Http404 from None


@require_GET
def sheet(request, campaign_id, actor_id):
    if not request.user.is_authenticated:
        raise Http404
    try:
        return JsonResponse(
            services.sheet(
                campaign_id, request.user.pk, actor_id, request.GET.get("tokenId")
            )
        )
    except JournalError, MapError:
        raise Http404 from None


@require_POST
def upload(request, campaign_id):
    if not request.user.is_authenticated:
        raise Http404
    asset = None
    try:
        who = services.member(campaign_id, request.user.pk)
        kind = request.POST.get("kind", "pdf")
        actor = None
        if kind == "pdf":
            services.manage(who)
        elif kind in ("portrait", "token"):
            actor = services.get(request.POST.get("actorId"), who, True)
        else:
            raise MapError("Invalid image kind.")
        file = request.FILES.get("file")
        if not file or file.size > 10_000_000:
            raise MapError("The file must be no larger than 10 MB.")
        raw = file.read()
        if kind == "pdf":
            if not raw.startswith(b"%PDF-"):
                raise MapError("Choose a PDF document.")
            ext = ".pdf"
        else:
            with Image.open(BytesIO(raw)) as image:
                if (
                    image.format not in {"PNG", "JPEG", "WEBP"}
                    or image.width * image.height > 25_000_000
                ):
                    raise MapError("Choose a PNG, JPEG or WebP image.")
                image.load()
                out = BytesIO()
                ImageOps.exif_transpose(image).convert("RGBA").save(out, format="PNG")
                raw = out.getvalue()
                ext = ".png"
        with transaction.atomic():
            from gravewright.campaigns.models import Campaign

            Campaign.objects.select_for_update().get(pk=campaign_id)
            who = services.member(campaign_id, request.user.pk)
            if actor:
                actor = services.get(actor.pk, who, True)
            else:
                services.manage(who)
            folder=None
            if kind=="pdf" and request.POST.get("folder_id"):
                from gravewright.maps.models import AssetFolder
                from gravewright.journals.services import identifier
                folder=AssetFolder.objects.filter(pk=identifier(request.POST["folder_id"]),campaign_id=campaign_id).first()
                if not folder:raise MapError("Folder not found.")
            asset = Asset(
                campaign_id=campaign_id,
                folder=folder,
                actor=actor,
                kind=kind,
                name=Path(file.name).name[:240],
            )
            asset.file.save(uuid.uuid4().hex + ext, ContentFile(raw), save=False)
            asset.save()
            transaction.on_commit(lambda: publish(campaign_id))
        return JsonResponse(
            {
                "id": str(asset.pk),
                "name": asset.name,
                "url": f"/game/actors/asset/{asset.pk}",
            }
        )
    except (
        JournalError,
        MapError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
    ) as e:
        if asset and asset.file and not Asset.objects.filter(pk=asset.pk).exists():
            asset.file.delete(save=False)
        return JsonResponse({"message": str(e)}, status=400)


@require_GET
def asset(request, asset_id):
    if not request.user.is_authenticated:
        raise Http404
    try:
        item = Asset.objects.select_related("actor").get(pk=asset_id)
        who = services.member(item.campaign_id, request.user.pk)
        if item.actor and not services.access(item.actor, who):
            from gravewright.maps.models import Broadcast

            scene_id = (
                Broadcast.objects.filter(
                    campaign_id=item.campaign_id, scene__visibility="players"
                )
                .values_list("scene_id", flat=True)
                .first()
            )
            # Rendering a visible token authorizes its image, not the actor's sheet.
            if (
                item.kind not in ("token", "portrait")
                or not item.actor.tokens.filter(
                    scene_id=scene_id, hidden=False
                ).exists()
            ):
                raise Http404
        response = FileResponse(
            item.file.open("rb"),
            content_type="application/pdf" if item.kind == "pdf" else "image/png",
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
    except Asset.DoesNotExist, JournalError, FileNotFoundError:
        raise Http404 from None
