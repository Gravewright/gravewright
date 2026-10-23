"""Shared validation at the boundaries of table modules."""
import json
from copy import deepcopy
from django.db import transaction
from gravewright.campaigns.models import Campaign, Membership
from gravewright.journals.services import identifier, member
from gravewright.maps.models import Receipt
from gravewright.maps.services import MapError, title, color, manage
from gravewright.maps.objects import number, boolean, choice
from .models import ClockReceipt, ClueReceipt


def version(row, payload):
    if type(payload.get('version')) is not int or row.version != payload['version']:
        raise MapError('This resource changed. Refresh before editing.', 'conflict')


def document(value, limit=256*1024):
    try:
        valid = isinstance(value, dict) and len(json.dumps(value, allow_nan=False).encode('utf-8')) <= limit
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise MapError('Invalid document.')
    return deepcopy(value)


def permissions(value, who):
    from .ownership import validate
    return validate(value, who, error_class=MapError)


def module(name):
    """Resolve a supported built-in table resource, not an installed extension package."""
    if name == 'clocks':
        from . import clocks
        return clocks
    if name == 'clues':
        from . import clues
        return clues
    if name not in ('items','combat','cards','audio','compendiums'):
        raise MapError('Unknown table module.')
    return __import__('gravewright.'+name+'.services', fromlist=['services'])


def state(campaign_id, user_id, name, scene_id=None, preview_token_id=None):
    """Resolve live membership before asking the named resource for a projection."""
    who = member(campaign_id, user_id)
    if name == "audio":
        return module(name).state(who, scene_id, preview_token_id)
    return module(name).state(who, scene_id)


@transaction.atomic
def command(campaign_id, user_id, name, action, data, request_id):
    """Serialize a resource command and record its retry result before notification."""
    if name == 'compendiums' and action == 'read':
        # Reads must recheck live grants, including when a caller reuses a
        # request ID. They neither create write receipts nor invalidate state.
        who = member(campaign_id, user_id)
        if not isinstance(data, dict):
            raise MapError('Invalid command.')
        identifier(request_id)
        return module(name).command(who, action, data) or {}
    Campaign.objects.select_for_update().get(pk=campaign_id)
    who = member(campaign_id, user_id)
    from gravewright.journals.services import writable
    writable(who)
    if not isinstance(action, str) or not isinstance(data, dict):
        raise MapError('Invalid command.')
    rid = identifier(request_id)
    # These projections include GM-only data. Each private domain has its own
    # cache, outside legacy cross-resource map/actor/native command receipts.
    receipt_model = {'clocks': ClockReceipt, 'clues': ClueReceipt}.get(name, Receipt)
    previous = receipt_model.objects.filter(campaign_id=campaign_id,user_id=user_id,request_id=rid).first()
    if previous:
        if name in ('clocks', 'clues'):
            module(name).validate_replay(who, action, data, previous.result)
        return previous.result
    result = module(name).command(who, action, data) or {}
    receipt_model.objects.create(campaign_id=campaign_id,user_id=user_id,request_id=rid,result=result)
    from gravewright.realtime.dispatch import changed
    changed(campaign_id,user_id,name,action,rid,result)
    return result
