"""Domain API shared by native browser code and mounted extensions.

Only the explicit registry is callable. Identity is always derived from the
session; a module additionally passes the existing activation/lease checks.
"""
import json
from pathlib import Path
from uuid import UUID

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from api import actors, tokens, maps, journals, resources, chat, dice, table
from api.errors import AuthError, JournalError, MapError, RollError
from gravewright.accounts.views import read_json
from gravewright.campaigns.views import authenticated
from .packages import ModuleFailure

CONTRACT = json.loads((Path(__file__).parent / 'contracts/frontend.json').read_text())
DOMAINS = {'actors': actors, 'tokens': tokens, 'maps': maps, 'journals': journals}
RESOURCE_DOMAINS = {'items', 'combat', 'cards', 'audio', 'compendiums'}


def invoke(campaign_id, user_id, domain, method, payload, request_id=None, scene_id=None):
    """Map an explicitly registered browser method onto its native public service.

    Read methods return the user's projection; writes retain native receipts,
    version checks and post-commit notifications. A mounted scene overrides no
    payload silently: attempts to target another scene fail as stale contexts.
    """
    if not isinstance(domain, str) or not isinstance(method, str) or not isinstance(payload, dict):
        raise ModuleFailure('invalid_data')
    p = dict(payload)
    # A mounted scene is authoritative; a payload cannot silently retarget it.
    if scene_id is not None:
        for key in ('sceneId', 'mapId'):
            if p.get(key) is not None and str(p[key]) != str(scene_id):
                raise ModuleFailure('stale_context')
        p['sceneId'] = p['mapId'] = str(scene_id)
    scene = p.get('sceneId') or p.get('mapId')
    try:
        if domain in CONTRACT['domains']:
            if method == 'state':
                if domain in RESOURCE_DOMAINS:
                    return resources.state(campaign_id, user_id, domain, scene, p.get('previewTokenId'))
                if domain == 'tokens':
                    return tokens.state(campaign_id, user_id, scene)
                return DOMAINS[domain].state(campaign_id, user_id)
            if domain == 'actors' and method == 'sheet':
                return actors.sheet(campaign_id, user_id, p.get('id'), p.get('tokenId'))
            if domain == 'maps' and method == 'layers':
                return maps.layer_state(campaign_id, user_id, scene)
            action = CONTRACT['domains'][domain].get(method)
            if action is None:
                raise ModuleFailure('unavailable')
            rid = UUID(str(request_id))
            if domain in RESOURCE_DOMAINS:
                return resources.command(campaign_id, user_id, domain, action, p, rid)
            return DOMAINS[domain].command(campaign_id, user_id, action, p, rid)
        if domain == 'chat':
            if method == 'history':
                return chat.history(campaign_id, user_id, scene)
            if method == 'send':
                return chat.send(campaign_id, user_id, p.get('text'), UUID(str(request_id)), scene)
            if method == 'remove':
                if not p.get('id'):
                    raise ModuleFailure('invalid_data')
                return chat.remove(campaign_id, user_id, p['id'])
            if method == 'clear':
                return chat.remove(campaign_id, user_id)
        if domain == 'dice' and method == 'roll':
            return dice.roll(campaign_id, user_id, p.get('expression'), UUID(str(request_id)),
                             repeat=p.get('repeat', 1), label=p.get('label', ''),
                             visibility=p.get('visibility', 'public'), map_id=scene)
        if domain == 'table':
            if method == 'search':
                return table.search(campaign_id, user_id, p.get('query', ''))
            if method == 'lobby':
                return table.lobby(campaign_id, user_id)
            if method == 'updateLobby':
                return table.update_lobby(campaign_id, user_id, p)
        raise ModuleFailure('unavailable')
    except ModuleFailure:
        raise
    except (JournalError, MapError, AuthError, RollError) as error:
        code = getattr(error, 'code', 'invalid_data')
        code = {'forbidden': 'permission_denied', 'not_a_member': 'permission_denied',
                'gm_required': 'permission_denied', 'owner_required': 'permission_denied',
                'blocked': 'permission_denied', 'invalid_input': 'invalid_data'}.get(code, code)
        if code not in ('not_found', 'permission_denied', 'conflict', 'invalid_data'):
            code = 'invalid_data'
        raise ModuleFailure(code, str(error)) from None
    except (ValueError, TypeError, KeyError):
        raise ModuleFailure('invalid_data') from None


@require_POST
@authenticated
@transaction.atomic
def call(request, table_id, module_id=None):
    """Share domain dispatch between host pages and lease-bound browser modules."""
    data = read_json(request)
    allowed = {'domain', 'method', 'payload', 'requestId'}
    if module_id is not None:
        allowed |= {'mountId', 'moduleSetRevision', 'sceneId'}
    if not isinstance(data, dict) or set(data) - allowed:
        raise ModuleFailure('invalid_data')
    # This check also covers operations like dice evaluation that do not read a resource.
    from gravewright.journals.services import member
    try:
        member(table_id, request.user.pk)
    except JournalError:
        raise ModuleFailure('permission_denied') from None
    scene = None
    if module_id is not None:
        from .views import identity
        _, _, scene = identity(request, table_id, module_id, data)
    value = invoke(table_id, request.user.pk, data.get('domain'), data.get('method'),
                   data.get('payload', {}), data.get('requestId'), scene)
    return JsonResponse({'value': value})
