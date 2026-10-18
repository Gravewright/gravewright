"""Post-commit invalidations shared by HTTP, sockets and Python extensions."""
import logging
from copy import deepcopy
from uuid import UUID
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

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


def changed(campaign_id, user_id, resource, action, request_id, result=None):
    """Schedule resource refreshes and trusted extension callbacks after commit."""
    from gravewright.table.events import Change, resource_changed
    change = Change(UUID(str(campaign_id)), UUID(str(user_id)), resource, action, UUID(str(request_id)))
    result = deepcopy(result or {})
    events = []
    if resource in ('actors', 'tokens'):
        # Presence handlers may change artwork and lights in the same operation.
        # The following token refresh also delivers the final spatial audio.
        events = [{'type': 'room.map_layers', 'refresh_audio': False}]
        if resource != 'tokens' or action not in ('move', 'teleport'):
            events.append({'type': 'room.actors'})
        events.append({'type': 'room.tokens'})
        if resource == 'tokens' and action in ('move', 'teleport'):
            events[-1]['refresh_combat'] = False
        if resource == 'tokens' and result.get('teleports'):
            events[-1].update(mapId=result['mapId'], teleports=result['teleports'])
        if resource == 'actors' or action in ('condition-add', 'condition-remove', 'remove', 'hidden', 'configure'):
            events.append({'type': 'room.resources', 'module': 'combat'})
    elif resource == 'maps':
        events = [{'type':'room.map_layers' if action == 'objects' else 'room.maps'}]
        if action == 'update':
            events.append({'type': 'room.map_layers'})
    elif resource == 'journals':
        if result.get('presentation'):
            events.append({'type':'room.handout','payload':result['presentation'],'request_id':str(request_id)})
        if result.get('message_id'):
            message(campaign_id, result['message_id'])
        events.append({'type':'room.journals'})
        # Journal/page grants, titles and board membership also change map locations.
        from gravewright.maps.models import SceneObject
        if result.get('map_locations_changed') or SceneObject.objects.filter(scene__campaign_id=campaign_id, kind='journalPins').exists():
            events.append({'type': 'room.map_layers'})
    elif resource in ('items','combat','cards','audio','compendiums'):
        events = [{'type':'room.resources','module':name} for name in ('items','combat','cards','audio','compendiums')]
        if resource == 'compendiums' and result.get('kind') == 'scene':
            events.append({'type':'room.maps'})
        events.extend({'type':name} for name in ('room.map_layers','room.actors','room.tokens','room.journals'))
    for event in events:
        transaction.on_commit(lambda value=event: send(campaign_id, value), robust=True)

    def notify_extensions():
        for receiver, response in resource_changed.send_robust(sender=resource, change=change):
            if isinstance(response, Exception):
                logger.error('Extension change handler failed: %r', receiver, exc_info=(type(response),response,response.__traceback__))
    transaction.on_commit(notify_extensions, robust=True)
