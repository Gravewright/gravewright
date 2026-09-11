"""Shared validation at the boundaries of table modules."""
import json
from copy import deepcopy
from django.db import transaction
from gravewright.campaigns.models import Campaign, Membership
from gravewright.journals.services import identifier, member
from gravewright.maps.models import Receipt
from gravewright.maps.services import MapError, title, color, manage
from gravewright.maps.objects import number, boolean, choice


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
    if not isinstance(value, dict) or len(value) > 1000:
        raise MapError('Invalid permissions.')
    valid = {str(i) for i in Membership.objects.filter(campaign_id=who.campaign_id).values_list('user_id', flat=True)}
    if any(k not in valid or v not in ('none','read','owner') for k,v in value.items()):
        raise MapError('Invalid permissions.')
    return dict(value)


def module(name):
    """Resolve a supported built-in table resource, not an installed extension package."""
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
    Campaign.objects.select_for_update().get(pk=campaign_id)
    who = member(campaign_id, user_id)
    from gravewright.journals.services import writable
    writable(who)
    if not isinstance(action, str) or not isinstance(data, dict):
        raise MapError('Invalid command.')
    rid = identifier(request_id)
    previous = Receipt.objects.filter(campaign_id=campaign_id,user_id=user_id,request_id=rid).first()
    if previous:
        return previous.result
    result = module(name).command(who, action, data) or {}
    Receipt.objects.create(campaign_id=campaign_id,user_id=user_id,request_id=rid,result=result)
    from gravewright.realtime.dispatch import changed
    changed(campaign_id,user_id,name,action,rid,result)
    return result
