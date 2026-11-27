"""Atomic, system-independent initiative from package-prepared expressions.

Packages prepare rules and resolve their own sheet fields. The host owns live
permissions, source revisions, randomness, encounter ordering and chat delivery.
"""
from copy import deepcopy
import hashlib
import json
import math
from uuid import uuid5

from django.db import transaction

from gravewright.actors.models import Actor
from gravewright.campaigns.models import Campaign, Membership
from gravewright.chat.models import Message, Recipient
from gravewright.chat.services import consume_limit
from gravewright.dice.engine import evaluate_batch
from gravewright.dice.grammar.errors import RollError
from gravewright.journals.services import identifier, member
from gravewright.maps.services import MapError, scene
from gravewright.tokens.models import Token
from gravewright.tokens.services import presentation
from .models import Encounter, InitiativeBatchReceipt
from .services import initiative_score, identity, state

ACTION = 'roll-initiative-batch'
MAX_INPUT_BYTES = 128 * 1024
MAX_RESULT_BYTES = 1024 * 1024


def _integer(value):
    if type(value) is not int or value < 0:
        raise MapError('Revisions must be non-negative integers.')
    return value


def _serialized(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (TypeError, ValueError):
        raise MapError('Invalid initiative batch document.') from None


def _prepare(payload):
    allowed = {'sceneId', 'mapId', 'version', 'entries', 'selectFirst', 'label'}
    if not isinstance(payload, dict) or set(payload) - allowed:
        raise MapError('Invalid initiative batch fields.')
    if len(_serialized(payload)) > MAX_INPUT_BYTES:
        raise MapError('Initiative batch exceeds 128 KiB.')
    scene_id = str(identifier(payload.get('sceneId')))
    if payload.get('mapId') is not None and str(identifier(payload['mapId'])) != scene_id:
        raise MapError('Initiative batch scene does not match its context.')
    entries = payload.get('entries')
    if not isinstance(entries, list) or not 1 <= len(entries) <= 64:
        raise MapError('Choose between 1 and 64 combatants.')
    select_first, label = payload.get('selectFirst', False), payload.get('label', 'Initiative')
    if type(select_first) is not bool or not isinstance(label, str) or len(label) > 48:
        raise MapError('Invalid initiative batch options.')
    prepared, seen = [], set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) - {'tokenId', 'actorId', 'expression', 'visibility', 'source'}:
            raise MapError('Invalid initiative batch entry.')
        if ('tokenId' in entry) == ('actorId' in entry):
            raise MapError('Each entry must identify exactly one token or actor.')
        kind = 'tokenId' if 'tokenId' in entry else 'actorId'
        target = str(identifier(entry[kind]))
        if target in seen:
            raise MapError('Initiative batch contains a duplicate combatant.')
        seen.add(target)
        expression, visibility = entry.get('expression'), entry.get('visibility', 'public')
        if not isinstance(expression, str) or not expression.strip() or len(expression) > 512:
            raise MapError('Expressions must contain 1 to 512 characters.')
        if visibility not in ('public', 'gm'):
            raise MapError('Invalid initiative audience.')
        source = entry.get('source')
        source_keys = {'actorVersion', 'sheetVersion'} | ({'tokenVersion'} if kind == 'tokenId' else set())
        if not isinstance(source, dict) or set(source) != source_keys:
            raise MapError('Supply the actor, sheet and applicable token revisions.')
        source = {key: _integer(value) for key, value in source.items()}
        prepared.append({kind: target, 'expression': expression, 'visibility': visibility, 'source': source})
    return {'sceneId': scene_id, 'version': _integer(payload.get('version')), 'entries': prepared,
            'selectFirst': select_first, 'label': label}


def _sources(who, target, row, entries):
    """Validate the whole frozen plan before any random draw or mutation."""
    combatants = {identity(entry): entry for entry in row.combatants}
    token_ids = [entry['tokenId'] for entry in entries if 'tokenId' in entry]
    actor_ids = [entry['actorId'] for entry in entries if 'actorId' in entry]
    tokens = {str(token.pk): token for token in Token.objects.filter(pk__in=token_ids, scene=target)
              .select_related('actor')}
    actors = {str(actor.pk): actor for actor in Actor.objects.filter(pk__in=actor_ids, campaign_id=who.campaign_id)}
    resolved = []
    for entry in entries:
        key, token = identity(entry), tokens.get(entry.get('tokenId'))
        participant = combatants.get(key)
        if not participant or ('tokenId' in participant) != ('tokenId' in entry):
            raise MapError('Combatant is not present in this encounter.', 'conflict')
        actor = token.actor if token else actors.get(entry.get('actorId'))
        if actor is None or actor.campaign_id != who.campaign_id:
            raise MapError('Combatant source is no longer available.', 'conflict')
        source = entry['source']
        sheet_version = token.sheet_version if token and not token.linked else actor.sheet_version
        if source['actorVersion'] != actor.version or source['sheetVersion'] != sheet_version \
                or token and source['tokenVersion'] != token.version:
            raise MapError('An initiative source changed. Refresh before rolling.', 'conflict')
        # A direct actor has no public token presence. Restricted ownership must
        # not become a public name/formula merely by joining this batch. Public
        # chat is durable and also visible to future members, so require a read
        # default and no explicit denial rather than checking only today's users.
        restricted_actor = not token and (actor.permissions.get('default') not in ('read', 'owner')
            or any(level not in ('read', 'owner') for level in actor.permissions.values()))
        hidden = participant.get('hidden') or token and token.hidden or restricted_actor
        visibility = 'gm' if hidden else entry['visibility']
        name = (presentation(token).get('token', {}).get('name') if token else None) or actor.name
        resolved.append((entry, participant, visibility, str(name)[:80]))
    return resolved


def _response(who, target, outcome, *, replayed):
    # A retry acknowledges the original outcomes while showing the live scene.
    return {**state(who, str(target.pk)), 'batch': {**deepcopy(outcome), 'replayed': replayed}}


@transaction.atomic
def execute(campaign_id, user_id, payload, request_id):
    Campaign.objects.select_for_update().get(pk=campaign_id)
    who = member(campaign_id, user_id)
    who = Membership.objects.select_for_update().select_related('user', 'campaign').get(pk=who.pk)
    if who.role != 'gm':
        raise MapError('Only the GM can roll encounter initiative.', 'forbidden')
    data, rid = _prepare(payload), identifier(request_id)
    target = scene(data['sceneId'], who)
    digest = hashlib.sha256(_serialized(data)).hexdigest()
    previous = InitiativeBatchReceipt.objects.filter(campaign_id=campaign_id, user_id=user_id, request_id=rid).first()
    if previous:
        if previous.scene_id != target.pk or previous.payload_hash != digest:
            raise MapError('This initiative request ID belongs to a different payload.')
        return _response(who, target, previous.result, replayed=True)
    row = Encounter.objects.filter(scene=target).first()
    if row is None or row.version != data['version']:
        raise MapError('This encounter changed. Refresh before rolling.', 'conflict')
    resolved = _sources(who, target, row, data['entries'])
    groups = {visibility: [] for visibility in ('public', 'gm')
              if any(item[2] == visibility for item in resolved)}
    message_requests = {visibility: uuid5(rid, 'combat-initiative:' + visibility) for visibility in groups}
    if Message.objects.filter(campaign_id=campaign_id, author_id=user_id,
                              request_id__in=message_requests.values()).exists():
        raise MapError('An initiative message request ID has already been used.')
    # Reserve only actual grouped messages. The encompassing transaction rolls
    # back the allowance together with all outcomes if any later step fails.
    for _ in groups:
        consume_limit(who)
    try:
        results = evaluate_batch([entry['expression'] for entry in data['entries']])
    except RollError as error:
        raise MapError(str(error)) from None
    if len(_serialized(results)) > MAX_RESULT_BYTES:
        raise MapError('Initiative results exceed 1 MiB.')
    outcomes = []
    for (entry, participant, visibility, name), result in zip(resolved, results, strict=True):
        value = result['value']['value']
        if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 1e6:
            raise MapError('Initiative must be a finite number between -1000000 and 1000000.')
        participant['initiative'] = value
        groups[visibility].append({'label': name, 'expression': entry['expression'], 'result': result})
        kind = 'tokenId' if 'tokenId' in entry else 'actorId'
        outcomes.append(({kind: entry[kind], 'initiative': value}, visibility))
    current_id = identity(row.combatants[row.turn]) if row.combatants and row.turn < len(row.combatants) else None
    row.combatants.sort(key=initiative_score, reverse=True)
    row.turn = (0 if data['selectFirst'] else next((i for i, entry in enumerate(row.combatants)
                if identity(entry) == current_id), 0)) if row.active else 0
    row.version += 1
    row.save(update_fields=['combatants', 'turn', 'version'])
    messages = {}
    for visibility, rolls in groups.items():
        message = Message.objects.create(campaign_id=campaign_id, author_id=user_id,
            author_name=who.user.name, scene=target, text=data['label'], visibility=visibility,
            request_id=message_requests[visibility], roll={'expression': '', 'label': data['label'],
                'secret': visibility == 'gm', 'result': rolls[0]['result'], 'batch': rolls})
        if visibility == 'gm':
            audience = set(Membership.objects.filter(campaign_id=campaign_id, role='gm', user__is_active=True)
                           .values_list('user_id', flat=True)) | {who.user_id}
            Recipient.objects.bulk_create([Recipient(message=message, user_id=pk) for pk in audience])
        messages[visibility] = message
    outcome = {'requestId': str(rid), 'version': row.version,
        'results': [{**value, 'messageId': str(messages[visibility].pk)} for value, visibility in outcomes],
        'messageIds': [str(message.pk) for message in messages.values()]}
    InitiativeBatchReceipt.objects.create(campaign_id=campaign_id, user_id=user_id, request_id=rid,
        scene_id=target.pk, payload_hash=digest, result=outcome)
    from gravewright.realtime.dispatch import changed, message as publish
    for message in messages.values():
        publish(campaign_id, message.pk)
    changed(campaign_id, user_id, 'combat', ACTION, rid)
    return _response(who, target, outcome, replayed=False)
