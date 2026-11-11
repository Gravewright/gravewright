"""Post-commit invalidations shared by HTTP, sockets and Python extensions."""
import logging
from copy import deepcopy
from uuid import UUID
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, connection, transaction
from django.db.models import F

logger = logging.getLogger(__name__)


def send(campaign_id, event):
    """Send an internal Channels event; callers choose the safe transaction boundary."""
    async_to_sync(get_channel_layer().group_send)(f'table.{UUID(str(campaign_id)).hex}', event)


def message(campaign_id, message_id):
    """Schedule delivery from the final committed message, including attached metadata."""
    # Read after commit: callers may attach card metadata in the same transaction.
    def publish():
        from gravewright.chat.models import Message
        from gravewright.chat.services import public_message
        row = Message.objects.filter(pk=message_id, campaign_id=campaign_id).first()
        if row:
            entry = public_message(row)
            send(campaign_id, {'type':'room.message','message':entry,'audience':entry['audience']})
    transaction.on_commit(publish, robust=True)


# Projections a socket can refresh after a commit, in delivery order: the board
# first, then directories and the scene list, then dependent resources (audio and
# combat last). `chat.history` is reloaded with the scene list it depends on.
PROJECTIONS = (
    'maps.layers', 'tokens', 'actors', 'journals', 'maps', 'chat.history',
    'resources:items', 'resources:cards', 'resources:compendiums', 'resources:clocks',
    'resources:clues', 'resources:mindmaps', 'resources:audio', 'resources:combat',
)
SHARED_RESOURCES = ('items', 'combat', 'cards', 'audio', 'compendiums')
PLAYBACK = frozenset({'play', 'pause', 'stop', 'seek', 'volume'})


def refreshes(campaign_id, resource, action, result):
    """Projections that may change when ``resource``/``action`` commits.

    The table is declarative and lives in the core: system packages extend data
    through these generic resources, never through system-specific branches.
    """
    names = set()
    if resource in ('actors', 'tokens'):
        # Presence handlers may change artwork and lights in the same operation.
        names = {'maps.layers', 'tokens', 'resources:audio'}
        if resource != 'tokens' or action not in ('move', 'teleport'):
            # Moves keep actor sheets and combat projections unchanged.
            names |= {'actors', 'resources:combat'}
    elif resource == 'maps':
        if action == 'objects':
            names = {'maps.layers', 'resources:audio'}
        else:
            names = {'maps', 'chat.history'}
            if action == 'update':
                names |= {'maps.layers', 'resources:audio'}
    elif resource == 'journals':
        names = {'journals'}
        # Journal/page grants, titles and board membership also change map locations.
        from gravewright.maps.models import SceneObject
        if result.get('map_locations_changed') or SceneObject.objects.filter(
                scene__campaign_id=campaign_id, kind='journalPins').exists():
            names |= {'maps.layers', 'resources:audio'}
    elif resource in ('clocks', 'clues', 'mindmaps'):
        names = {f'resources:{resource}'}
    elif resource == 'compendiums' and action == 'import':
        # An import can merge a whole content archive: refresh everything it may touch.
        names = {f'resources:{name}' for name in SHARED_RESOURCES}
        names |= {'maps.layers', 'actors', 'tokens', 'journals'}
        if result.get('kind') == 'scene':
            names |= {'maps', 'chat.history'}
    elif resource in SHARED_RESOURCES:
        # Measured with test_dispatch_dependencies: each resource changes its own
        # projection; cards on the scene, combat and the soundscape also appear in
        # the map layers. Playback alone changes only the audio projection.
        names = {f'resources:{resource}'}
        if resource in ('combat', 'cards') or (resource == 'audio' and action not in PLAYBACK):
            names.add('maps.layers')
    return [name for name in PROJECTIONS if name in names]


def revision(campaign_id):
    """The campaign's latest committed envelope number (0 before the first one)."""
    from .models import CampaignRevision
    return CampaignRevision.objects.filter(campaign_id=campaign_id).values_list('value', flat=True).first() or 0


def next_revision(campaign_id):
    """Advance the envelope counter inside the committing transaction.

    One statement while the write lock is held (UPDATE ... RETURNING); None when the
    campaign does not exist, so a notification never breaks the committing work.
    """
    from gravewright.campaigns.models import Campaign
    from .models import CampaignRevision
    rows = CampaignRevision.objects.filter(campaign_id=campaign_id)
    if connection.vendor in ('sqlite', 'postgresql'):
        key = CampaignRevision._meta.pk.target_field.get_db_prep_value(UUID(str(campaign_id)), connection)
        table = connection.ops.quote_name(CampaignRevision._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(f'UPDATE {table} SET value = value + 1 WHERE campaign_id = %s RETURNING value', [key])
            row = cursor.fetchone()
        if row:
            return row[0]
    elif rows.update(value=F('value') + 1):
        return revision(campaign_id)
    if not Campaign.objects.filter(pk=campaign_id).exists():
        return None
    try:
        with transaction.atomic():
            CampaignRevision.objects.create(campaign_id=campaign_id, value=1)
        return 1
    except IntegrityError:
        rows.update(value=F('value') + 1)
        return revision(campaign_id)


def changed(campaign_id, user_id, resource, action, request_id, result=None):
    """Schedule one refresh envelope and trusted extension callbacks after commit.

    Each commit becomes a single ``room.changes`` event listing the projections to
    refresh, so a socket delivers each projection once. Handouts and chat messages
    keep their own events.
    """
    from gravewright.table.events import Change, resource_changed
    change = Change(UUID(str(campaign_id)), UUID(str(user_id)), resource, action, UUID(str(request_id)))
    result = deepcopy(result or {})
    events = []
    if resource == 'journals':
        if result.get('presentation'):
            events.append({'type':'room.handout','payload':result['presentation'],'request_id':str(request_id)})
        if result.get('message_id'):
            message(campaign_id, result['message_id'])
    refresh = refreshes(campaign_id, resource, action, result)
    if refresh:
        # The counter commits or rolls back with the change it numbers.
        envelope = {'type': 'room.changes', 'resource': resource, 'action': action, 'refresh': refresh}
        number = next_revision(campaign_id)
        if number is not None:
            envelope['revision'] = number
        if resource == 'tokens' and result.get('teleports'):
            envelope.update(mapId=result['mapId'], teleports=result['teleports'])
        events.append(envelope)
    for event in events:
        transaction.on_commit(lambda value=event: send(campaign_id, value), robust=True)

    def notify_extensions():
        for receiver, response in resource_changed.send_robust(sender=resource, change=change):
            if isinstance(response, Exception):
                logger.error('Extension change handler failed: %r', receiver, exc_info=(type(response),response,response.__traceback__))
    transaction.on_commit(notify_extensions, robust=True)
