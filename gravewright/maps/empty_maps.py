"""Create solid-color native scenes through the normal map lifecycle."""

import uuid

from django.core.files.storage import default_storage
from django.db import transaction

from gravewright.campaigns.models import Campaign
from gravewright.journals.services import identifier, member
from . import services, tiling
from .models import Receipt, Scene, SceneNavigation, Tile


def create(campaign_id, user_id, payload):
    if not isinstance(payload, dict):
        raise services.MapError("Invalid empty map settings.")
    who = member(campaign_id, user_id)
    services.manage(who)
    rid = identifier(payload.get("requestId"))
    receipts = Receipt.objects.filter(campaign_id=campaign_id, user_id=user_id, request_id=rid)
    receipt = receipts.first()
    if receipt:
        return receipt.result
    name = services.title(payload.get("name", "Empty map"))
    grid = payload.get("gridVisible")
    if type(grid) is not bool:
        raise services.MapError("Invalid grid visibility.")
    activate = payload.get("activate", True)
    if type(activate) is not bool:
        raise services.MapError("Invalid scene activation.")
    services.folder(payload.get("groupId"), who)
    stored, tiles = [], []
    try:
        def save_tile(lod, x, y, content):
            candidate = "maps/tiles/" + uuid.uuid4().hex + ".webp"
            existed = default_storage.exists(candidate)
            try:
                path = default_storage.save(candidate, content)
            except Exception:
                # A storage backend can write the file before reporting failure.
                if not existed and default_storage.exists(candidate):
                    default_storage.delete(candidate)
                raise
            stored.append(path)
            tiles.append(Tile(lod=lod, x=x, y=y, file=path, byte_size=content.size))

        width, height, max_lod = tiling.generate_solid_pyramid(
            payload.get("width"), payload.get("height"), payload.get("color"), save_tile,
        )
        with transaction.atomic():
            Campaign.objects.select_for_update().get(pk=campaign_id)
            who = member(campaign_id, user_id)
            services.manage(who)
            receipt = receipts.first()
            if receipt:
                return receipt.result
            target = services.folder(payload.get("groupId"), who)
            row = Scene.objects.create(
                campaign_id=campaign_id, folder=target, name=name, width=width, height=height,
                max_lod=max_lod, settings={**services.DEFAULTS, "gridVisible": grid},
            )
            for tile in tiles:
                tile.scene = row
            Tile.objects.bulk_create(tiles)
            if activate:
                from .audience import broadcast
                broadcast(who, row)
            SceneNavigation.objects.update_or_create(
                membership=who, defaults={"scene": None if activate else row},
            )
            result = services.view(row)
            Receipt.objects.create(campaign_id=campaign_id, user_id=user_id, request_id=rid, result=result)
            from gravewright.realtime.dispatch import changed
            changed(campaign_id, user_id, "maps", "create-empty", rid, result)
        stored.clear()
        return result
    finally:
        for path in stored:
            default_storage.delete(path)
