"""Authorized library projections and receipt-backed file organization."""
from copy import deepcopy
import json
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F, Q
from gravewright.campaigns.models import Campaign
from gravewright.journals.services import identifier
from . import services
from .models import AssetFolder, MapAsset, Receipt, SceneObject, SceneState
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


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
    from .audience import destination
    row = destination(member)
    active = row.pk if row and row.visibility == 'players' else None
    if active is not None:
        services.scene(active, member)
    return active


def state(campaign_id, user_id):
    """Return the same recipient-filtered assets and folders as the native library."""
    member = services.member(campaign_id, user_id)
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
    return {
        "assets": result,
        "folders": [{"id": str(f.pk), "name": f.name} for f in folders],
    }


@transaction.atomic
def command(campaign_id, user_id, action, payload, request_id):
    """Organize campaign assets with GM checks, retries and post-commit delivery."""
    campaign_id = identifier(campaign_id)
    if Campaign.objects.select_for_update().filter(pk=campaign_id).first() is None:
        raise services.MapError("Asset or folder not found.", "not_found")
    current = services.member(campaign_id, user_id)
    services.manage(current)
    rid = identifier(request_id)
    previous = Receipt.objects.filter(campaign_id=campaign_id, user_id=user_id, request_id=rid).first()
    if previous:
        return previous.result
    try:
        valid = isinstance(payload, dict) and len(json.dumps(payload, allow_nan=False)) <= 500_000
    except (TypeError, ValueError, RecursionError):
        valid = False
    if not valid:
        raise services.MapError("Invalid command.")
    p = deepcopy(payload)
    for alias, canonical in (("folderId", "folder_id"), ("assetId", "asset_id")):
        if alias in p:
            if canonical in p and p[canonical] != p[alias]:
                raise services.MapError("Conflicting asset identifiers.")
            p[canonical] = p[alias]
    result = {"ok": True}
    try:
        if action == "folder-create":
            created = AssetFolder.objects.create(
                campaign_id=campaign_id, name=services.title(p.get("name"), 80)
            )
            result["id"] = str(created.pk)
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
                    audio_command(current, "track-delete", {"id": str(asset.pk), "version": asset.version})
                else:
                    from gravewright.actors.models import Asset as ActorAsset
                    is_actor_asset = isinstance(asset, ActorAsset)
                    if is_actor_asset:
                        from gravewright.campaigns.systems import remove_asset_references
                        remove_asset_references(current.campaign.system, campaign_id, asset)
                    storage,path=asset.file.storage,asset.file.name
                    asset.delete()
                    transaction.on_commit(lambda s=storage,n=path:s.delete(n))
                    if is_actor_asset:
                        from gravewright.realtime.dispatch import changed
                        changed(campaign_id, user_id, "actors", "asset.delete", rid, result)
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
    except ObjectDoesNotExist:
        raise services.MapError("Asset or folder not found.", "not_found") from None
    Receipt.objects.create(campaign_id=campaign_id, user_id=user_id, request_id=rid, result=result)
    from .views import notify
    from gravewright.table.media import announce
    transaction.on_commit(lambda: notify(campaign_id), robust=True)
    transaction.on_commit(lambda: announce(campaign_id), robust=True)
    from gravewright.realtime.dispatch import changed
    changed(campaign_id, user_id, "library", action, rid, result)
    return result
