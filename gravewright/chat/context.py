"""Resolve an explicitly selected scene or the public broadcast, never a foreign block."""

from gravewright.accounts.services import AuthError
from gravewright.maps.models import Broadcast, Scene


def scene_for(who, map_id=None, block_id=None):
    from gravewright.journals.services import JournalError, identifier
    from gravewright.maps import services as maps

    try:
        if block_id:
            block_id = identifier(block_id)
            row = Scene.objects.filter(
                campaign_id=who.campaign_id, block_id=block_id
            ).first()
            if row is None:
                raise AuthError("invalid_scene")
            if map_id and str(row.pk) != str(map_id):
                raise AuthError("invalid_scene")
            map_id = row.pk
        if not map_id:
            map_id = (
                Broadcast.objects.filter(
                    campaign_id=who.campaign_id, scene__visibility="players"
                )
                .values_list("scene_id", flat=True)
                .first()
            )
        return maps.scene(map_id, who) if map_id else None
    except maps.MapError, JournalError, ValueError:
        raise AuthError("invalid_scene") from None


def readable(campaign_id, user_id, map_id):
    if not map_id:
        return True
    from gravewright.journals.services import JournalError
    from gravewright.maps import services as maps

    try:
        maps.scene(map_id, maps.member(campaign_id, user_id))
        return True
    except maps.MapError, JournalError, ValueError:
        return False
