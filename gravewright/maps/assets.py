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

from . import services
from .models import AssetFolder, Broadcast, MapAsset, SceneObject, SceneState


def who(request, campaign_id, write=False):
    if not request.user.is_authenticated:
        raise Http404
    member = services.member(campaign_id, request.user.pk)
    if write:
        services.manage(member)
    return member


def visible_door_art(scene_id, asset_id=None):
    """Expose only door images already visible in the audience's active scene."""
    from .blueprint_runtime import appearance

    doors = SceneObject.objects.filter(scene_id=scene_id, kind="walls", data__kind="door").filter(
        Q(data__presentation__in=["normal", "window", "bars"]) | Q(data__discovered=True)
    )
    if asset_id is not None:
        asset_id = str(asset_id)
        doors = doors.filter(
            Q(data__asset_id=asset_id)
            | Q(data__blueprint__states__closed__assetId=asset_id)
            | Q(data__blueprint__states__open__assetId=asset_id)
            | Q(data__blueprint__states__locked__assetId=asset_id)
            | Q(data__sprite__assetId=asset_id)
        )
    result = set()
    for data in doors.values_list("data", flat=True):
        art = appearance(data)
        if art["visible"] and art["assetId"]:
            result.add(art["assetId"])
    return result


def active_scene(member):
    active = Broadcast.objects.filter(
        campaign_id=member.campaign_id, scene__visibility="players"
    ).values_list("scene_id", flat=True).first()
    if active is not None:
        services.scene(active, member)
    return active


@require_GET
def state(request, campaign_id):
    try:
        member = who(request, campaign_id)
        assets = MapAsset.objects.filter(campaign_id=campaign_id, generated_for__isnull=True)
        if member.role != "gm":
            active = active_scene(member)
            ids = [
                r["asset_id"]
                for r in SceneObject.objects.filter(
                    scene_id=active, kind="images"
                ).values_list("data", flat=True)
                if r.get("layer") not in {"gm", "gm-image-layer"}
            ]
            ids.extend(visible_door_art(active))
            assets = assets.filter(pk__in=ids)
        result = []
        for a in assets:
            result.append(
                {
                    "id": str(a.pk),
                    "filename": a.name,
                    "name": a.name,
                    "kind": "image",
                    "src": f"/game/map-assets/{a.pk}",
                    "url": f"/game/map-assets/{a.pk}",
                    "content_type": "image/png",
                    "width": a.width,
                    "height": a.height,
                    "byte_size": a.file.size,
                    "folder_id": str(a.folder_id) if a.folder_id else None,
                }
            )
        if member.role == "gm":
            from gravewright.audio.models import Track
            for track in Track.objects.filter(campaign_id=campaign_id):
                result.append({"id": str(track.pk), "name": track.name, "filename": track.name,
                    "kind": "audio", "purpose": "effect" if track.kind == "effect" else "ambient",
                    "src": f"/game/audio/{track.pk}", "url": f"/game/audio/{track.pk}",
                    "content_type": track.content_type, "byte_size": track.file.size,
                    "folder_id": str(track.folder_id) if track.folder_id else None})
        if member.role == "gm":
            from gravewright.actors.models import Asset
            for asset in Asset.objects.filter(campaign_id=campaign_id,kind="pdf"):
                result.append({"id":str(asset.pk),"name":asset.name,"filename":asset.name,"kind":"pdf","purpose":"pdf-sheet","src":f"/game/actors/asset/{asset.pk}","url":f"/game/actors/asset/{asset.pk}","content_type":"application/pdf","byte_size":asset.file.size,"folder_id":str(asset.folder_id) if asset.folder_id else None})
        folders = AssetFolder.objects.filter(campaign_id=campaign_id)
        if member.role != "gm":
            folders = folders.filter(
                pk__in=[a["folder_id"] for a in result if a["folder_id"]]
            )
        response = JsonResponse(
            {
                "assets": result,
                "folders": [{"id": str(f.pk), "name": f.name} for f in folders],
            }
        )
        response["Cache-Control"] = "private, no-store"
        return response
    except services.MapError, JournalError:
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
        with transaction.atomic():
            get_object_or_404(Campaign.objects.select_for_update(), pk=campaign_id)
            who(request, campaign_id, True)
            p = json.loads(request.body)
            if not isinstance(p, dict):
                raise services.MapError("Invalid command.")
            if action == "folder-create":
                AssetFolder.objects.create(
                    campaign_id=campaign_id, name=services.title(p.get("name"), 80)
                )
            elif action in ("folder-delete", "folder-rename"):
                folder = AssetFolder.objects.get(
                    campaign_id=campaign_id, pk=identifier(p.get("folder_id"))
                )
                if action == "folder-delete":
                    folder.delete()
                else:
                    folder.name = services.title(p.get("name"), 80)
                    folder.save()
            elif action in ("delete", "move"):
                from gravewright.audio.models import Track
                asset_id = identifier(p.get("asset_id"))
                asset = MapAsset.objects.filter(campaign_id=campaign_id, pk=asset_id).first()
                if asset is not None and asset.generated_for_id is not None:
                    raise services.MapError("Generated map surfaces are managed by their scene.")
                if asset is None:
                    asset = Track.objects.filter(campaign_id=campaign_id, pk=asset_id).first()
                if asset is None:
                    from gravewright.actors.models import Asset
                    asset = Asset.objects.get(campaign_id=campaign_id,pk=asset_id,kind="pdf")
                if action == "delete":
                    scenes = []
                    if isinstance(asset, MapAsset):
                        # State images leave native blueprints first, so a lever showing
                        # one reverts to its own image instead of being deleted below.
                        from .blueprint_runtime import detach_scene_art
                        scenes.extend(detach_scene_art(campaign_id, asset.pk))
                    # All placements disappear with the image, including inactive scenes.
                    placements = SceneObject.objects.filter(
                        scene__campaign_id=campaign_id,
                        kind="spatialSounds" if isinstance(asset, Track) else "images",
                    )
                    if isinstance(asset, Track):
                        placements = placements.filter(data__trackId=str(asset.pk))
                    else:
                        placements = placements.filter(Q(data__asset_id=str(asset.pk))
                            | Q(data__lever__baseAssetId=str(asset.pk)) | Q(data__torch__baseAssetId=str(asset.pk))
                            | Q(data__sprite__assetId=str(asset.pk)) | Q(data__spriteBase__assetId=str(asset.pk)))
                        from .torches import delete_group
                        for placement in placements:
                            delete_group(placement)
                    scenes.extend(placements.values_list("scene_id", flat=True))
                    placements.delete()
                    if isinstance(asset, MapAsset):
                        from .builder_services import detach_project_art
                        detach_project_art(campaign_id, asset.pk)
                        # Removing art must never remove the door's collision or
                        # expose a passage that is still closed in the table.
                        for door in SceneObject.objects.filter(
                            scene__campaign_id=campaign_id, kind="walls",
                            data__asset_id=str(asset.pk),
                        ):
                            door.data.pop("asset_id", None)
                            if "blueprint" not in door.data:
                                door.data.pop("thickness", None)
                            door.version += 1
                            door.save(update_fields=["data", "version"])
                            scenes.append(door.scene_id)
                    SceneState.objects.filter(scene_id__in=scenes).update(
                        version=F("version") + 1
                    )
                    if isinstance(asset, Track):
                        from gravewright.audio.services import command as audio_command
                        audio_command(who(request, campaign_id, True), "track-delete", {"id": str(asset.pk), "version": asset.version})
                    else:
                        storage,path=asset.file.storage,asset.file.name
                        asset.delete()
                        transaction.on_commit(lambda s=storage,n=path:s.delete(n))
                    transaction.on_commit(
                        lambda: async_to_sync(get_channel_layer().group_send)(
                            f"table.{campaign_id.hex}", {"type": "room.map_layers"}
                        )
                    )
                else:
                    asset.folder = (
                        AssetFolder.objects.get(
                            campaign_id=campaign_id, pk=identifier(p["folder_id"])
                        )
                        if p.get("folder_id")
                        else None
                    )
                    asset.save()
            else:
                raise services.MapError("Unknown asset command.")
        from .views import notify

        notify(campaign_id)
        from gravewright.table.media import announce
        announce(campaign_id)
        return JsonResponse({"ok": True})
    except (
        ValueError,
        services.MapError,
        JournalError,
        AssetFolder.DoesNotExist,
        ObjectDoesNotExist,
    ) as error:
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
