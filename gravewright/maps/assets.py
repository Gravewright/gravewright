import json
from io import BytesIO
from pathlib import Path

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.files.base import ContentFile
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F, Q
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from PIL import Image, ImageOps, UnidentifiedImageError

from gravewright.campaigns.models import Campaign
from gravewright.journals.services import JournalError, identifier

from . import services, library_services
from .library_services import visible_door_art, active_scene
from .models import AssetFolder, Broadcast, MapAsset, SceneObject, SceneState


def who(request, campaign_id, write=False):
    if not request.user.is_authenticated:
        raise Http404
    member = services.member(campaign_id, request.user.pk)
    if write:
        services.manage(member)
    return member


@require_GET
def state(request, campaign_id):
    try:
        who(request, campaign_id)
        response = JsonResponse(library_services.state(campaign_id, request.user.pk))
        response["Cache-Control"] = "private, no-store"
        return response
    except (services.MapError, JournalError):
        raise Http404 from None


@require_POST
def upload(request, campaign_id):
    if request.POST.get("purpose") in ("ambient", "effect"):
        from gravewright.table.media import upload as upload_media
        return upload_media(request, campaign_id, "audio")
    if request.POST.get("purpose") == "pdf-sheet":
        from gravewright.actors.views import upload as upload_pdf
        return upload_pdf(request, campaign_id)
    stored = None
    try:
        who(request, campaign_id, True)
        file = request.FILES.get("file")
        if not file or file.size > 25 * 1024 * 1024:
            raise services.MapError("Choose an image up to 25 MB.")
        with Image.open(file) as image:
            if (
                image.format not in {"PNG", "JPEG", "WEBP", "TIFF"}
                or image.width * image.height > 40_000_000
            ):
                raise services.MapError("Invalid image.")
            image = ImageOps.exif_transpose(image)
            image.load()
            width, height = image.size
            buf = BytesIO()
            image.convert("RGBA").save(buf, "PNG")
        with transaction.atomic():
            get_object_or_404(Campaign.objects.select_for_update(), pk=campaign_id)
            who(request, campaign_id, True)
            folder = None
            if request.POST.get("folder_id"):
                folder = AssetFolder.objects.get(
                    pk=identifier(request.POST["folder_id"]), campaign_id=campaign_id
                )
            asset = MapAsset(
                campaign_id=campaign_id,
                folder=folder,
                name=Path(file.name).name[:240],
                width=width,
                height=height,
            )
            asset.file.save("image.png", ContentFile(buf.getvalue()), save=False)
            stored = asset.file
            asset.save()
        stored = None
        return JsonResponse({"id": str(asset.pk)}, status=201)
    except (
        services.MapError,
        JournalError,
        AssetFolder.DoesNotExist,
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
    ) as error:
        return JsonResponse({"error": str(error)}, status=400)
    finally:
        if stored:
            stored.delete(save=False)


@require_POST
def command(request, campaign_id, action):
    try:
        who(request, campaign_id, True)
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise services.MapError("Invalid command.")
        import uuid
        result = library_services.command(campaign_id, request.user.pk, action, payload,
                                          payload.get("requestId") or uuid.uuid4())
        return JsonResponse(result)
    except (ValueError, services.MapError, JournalError, ObjectDoesNotExist) as error:
        return JsonResponse({"error": str(error)}, status=400)


@require_GET
def file(request, asset_id):
    try:
        asset = MapAsset.objects.get(pk=asset_id)
        member = who(request, asset.campaign_id)
        if member.role != "gm":
            active = active_scene(member)
            if asset.generated_for_id is not None and str(asset.generated_for_id) != str(active):
                raise Http404
            if not (
                SceneObject.objects.filter(
                    Q(data__asset_id=str(asset.pk)) | Q(data__surface__maskId=str(asset.pk))
                    | Q(data__surface__materialId=str(asset.pk)), scene_id=active, kind="images"
                )
                .exclude(data__layer__in=["gm", "gm-image-layer"])
                .exists()
                or str(asset.pk) in visible_door_art(active, asset.pk)
            ):
                raise Http404
        response = FileResponse(asset.file.open("rb"), content_type="image/png")
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
    except MapAsset.DoesNotExist, services.MapError, JournalError, FileNotFoundError:
        raise Http404 from None
