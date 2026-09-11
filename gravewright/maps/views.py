from io import BytesIO
import json
import math
import uuid
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from PIL import Image, ImageOps, UnidentifiedImageError
from gravewright.campaigns.models import Campaign
from gravewright.journals.services import JournalError, member
from . import services
from .models import Scene, Tile, Broadcast


def notify(campaign_id):
    async_to_sync(get_channel_layer().group_send)(
        f"table.{campaign_id.hex}", {"type": "room.maps"}
    )


@require_POST
def upload(request, campaign_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=403)
    stored = []
    try:
        who = member(campaign_id, request.user.pk)
        services.manage(who)
        name = services.title(request.POST.get("name"))
        raw_settings = json.loads(request.POST.get("settings", "{}"))
        options = services.settings(raw_settings)
        visibility = raw_settings.get("visibility", "players")
        if visibility not in ("players", "gm"):
            raise services.MapError("Invalid visibility.")
        target = services.folder(raw_settings.get("groupId"), who)
        incoming = request.FILES.get("map")
        if incoming is None or incoming.size > settings.MAP_UPLOAD_MAX_BYTES:
            raise services.MapError("Choose a map image within the configured upload limit.")
        try:
            with Image.open(incoming) as source:
                if source.format not in ("PNG", "JPEG", "WEBP", "TIFF"):
                    raise ValueError("format")
                if source.width * source.height > getattr(
                    settings, "GRAVEWRIGHT_MAP_MAX_PIXELS", 64_000_000
                ):
                    raise services.MapError(
                        "This map exceeds the server image pixel limit."
                    )
                if source.width > settings.MAP_IMAGE_MAX_WIDTH or source.height > settings.MAP_IMAGE_MAX_HEIGHT:
                    raise services.MapError("Map dimensions exceed the configured limit.")
                levels = max(0, math.ceil(math.log2(max(source.size) / 512)))
                if sum(math.ceil(source.width / (512 * 2**lod)) * math.ceil(source.height / (512 * 2**lod)) for lod in range(levels + 1)) > settings.MAP_MAX_TILE_COUNT:
                    raise services.MapError("Map tile count exceeds the configured limit.")
                source.load()
                raster = ImageOps.exif_transpose(source).convert("RGBA")
        except (
            UnidentifiedImageError,
            ValueError,
            OSError,
            Image.DecompressionBombError,
        ):
            raise services.MapError(
                "Choose a valid PNG, JPEG, WebP or TIFF image."
            ) from None
        width, height = raster.size
        max_lod = max(0, math.ceil(math.log2(max(width, height) / 512)))
        tiles = []
        try:
            for lod in range(max_lod + 1):
                if lod:
                    level = raster.resize(
                        (math.ceil(width / 2**lod), math.ceil(height / 2**lod)),
                        Image.Resampling.LANCZOS,
                    )
                else:
                    level = raster
                try:
                    for y in range(math.ceil(level.height / 512)):
                        for x in range(math.ceil(level.width / 512)):
                            with level.crop(
                                (
                                    x * 512,
                                    y * 512,
                                    min((x + 1) * 512, level.width),
                                    min((y + 1) * 512, level.height),
                                )
                            ) as chunk:
                                content = BytesIO()
                                chunk.save(content, format="WEBP", lossless=True)
                            path = default_storage.save(
                                "maps/tiles/" + uuid.uuid4().hex + ".webp",
                                ContentFile(content.getvalue()),
                            )
                            stored.append(path)
                            tiles.append(Tile(lod=lod, x=x, y=y, file=path, byte_size=len(content.getvalue())))
                finally:
                    if lod:
                        level.close()
        finally:
            raster.close()
        with transaction.atomic():
            Campaign.objects.select_for_update().get(pk=campaign_id)
            who = member(campaign_id, request.user.pk)
            services.manage(who)
            target = services.folder(raw_settings.get("groupId"), who)
            row = Scene.objects.create(
                campaign_id=campaign_id,
                name=name,
                folder=target,
                visibility=visibility,
                width=width,
                height=height,
                max_lod=max_lod,
                settings=options,
            )
            for tile in tiles:
                tile.scene = row
            Tile.objects.bulk_create(tiles)
            if request.POST.get("activate") == "true":
                Broadcast.objects.update_or_create(
                    campaign_id=campaign_id, defaults={"scene": row}
                )
        stored.clear()
        notify(campaign_id)
        return JsonResponse(services.view(row), status=201)
    except (services.MapError, JournalError, ValueError) as error:
        return JsonResponse({"error": str(error)}, status=400)
    finally:
        for path in stored:
            default_storage.delete(path)


def authorized(request, map_id):
    if not request.user.is_authenticated:
        raise Http404
    row = Scene.objects.filter(pk=map_id).first()
    if row is None:
        raise Http404
    try:
        return services.scene(map_id, member(row.campaign_id, request.user.pk))
    except services.MapError, JournalError:
        raise Http404 from None


@require_GET
def manifest(request, map_id):
    response = JsonResponse(services.manifest(authorized(request, map_id)))
    response["Cache-Control"] = "private, no-store"
    return response


@require_GET
def tile(request, map_id, lod, x, y):
    row = authorized(request, map_id)
    item = Tile.objects.filter(scene=row, lod=lod, x=x, y=y).first()
    if item is None:
        raise Http404
    try:
        response = FileResponse(item.file.open("rb"), content_type="image/webp")
    except FileNotFoundError:
        raise Http404 from None
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_GET
def state(request, campaign_id):
    if not request.user.is_authenticated:
        raise Http404
    try:
        return JsonResponse(services.state(campaign_id, request.user.pk))
    except services.MapError, JournalError:
        raise Http404 from None


@require_GET
def layers(request, map_id):
    from .objects import layer_state

    row = authorized(request, map_id)
    response = JsonResponse(layer_state(row, member(row.campaign_id, request.user.pk)))
    response["Cache-Control"] = "private, no-store"
    return response
