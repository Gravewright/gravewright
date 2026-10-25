"""Campaign broadcast and explicit player scene destinations."""
from django.db.models import Value
from django.db.models.functions import Coalesce

from gravewright.campaigns.models import Membership
from .models import Broadcast, Scene, SceneAssignment, SceneNavigation


def destination(who):
    if who.role == 'player':
        assigned = SceneAssignment.objects.filter(
            membership=who, scene__campaign_id=who.campaign_id,
        ).select_related('scene').first()
        if assigned:
            return assigned.scene
    broadcast = Broadcast.objects.filter(campaign_id=who.campaign_id).select_related('scene').first()
    return broadcast.scene if broadcast else None


def broadcast(who, row):
    """A table-wide activation reunites players, clearing individual destinations."""
    Broadcast.objects.update_or_create(campaign_id=who.campaign_id, defaults={'scene': row})
    SceneAssignment.objects.filter(membership__campaign_id=who.campaign_id).delete()
    SceneNavigation.objects.filter(membership=who).update(scene=None)


def assign(who, row, player_ids):
    from .services import MapError
    from gravewright.journals.services import identifier
    from gravewright.table.ownership import resource_allows

    if not isinstance(player_ids, list) or not 1 <= len(player_ids) <= 1000:
        raise MapError('Select one or more players.')
    ids = [identifier(value) for value in player_ids]
    members = list(Membership.objects.filter(campaign_id=who.campaign_id, role='player', user_id__in=ids))
    if len(set(ids)) != len(ids) or len(members) != len(ids):
        raise MapError('Select players from this campaign.')
    if any(not resource_allows(member, 'scenes', row, default='read') for member in members):
        raise MapError('A selected player cannot access this scene.', 'forbidden')
    for member in members:
        SceneAssignment.objects.update_or_create(membership=member, defaults={'scene': row})


def players(campaign_id):
    from gravewright.table.ownership import resource_allows

    members = Membership.objects.filter(campaign_id=campaign_id, role='player').select_related('user').annotate(
        identification_color=Coalesce('user__preferences__ping_color', Value('#f2c679')),
    ).order_by('user__name', 'user_id')
    assignments = dict(SceneAssignment.objects.filter(membership__campaign_id=campaign_id).values_list('membership_id', 'scene_id'))
    active = Broadcast.objects.filter(campaign_id=campaign_id).values_list('scene_id', flat=True).first()
    scenes = {row.pk: row for row in Scene.objects.filter(
        campaign_id=campaign_id, visibility='players',
    ).only('id', 'campaign_id')}
    result = []
    for member in members:
        row = scenes.get(assignments.get(member.pk, active))
        visible = row is not None and resource_allows(member, 'scenes', row, default='read')
        result.append({'id': str(member.user_id), 'name': member.user.name or 'Player',
                       'color': member.identification_color, 'sceneId': str(row.pk) if visible else None})
    return result


def color_changed(user_id):
    """Refresh campaign directories after a player changes identification color."""
    from django.db import transaction
    from gravewright.realtime.dispatch import send
    for campaign_id in Membership.objects.filter(user_id=user_id, role='player').values_list('campaign_id', flat=True):
        transaction.on_commit(lambda campaign_id=campaign_id: send(campaign_id, {'type': 'room.maps'}), robust=True)
