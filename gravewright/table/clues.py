"""Scoped clue discoveries with GM-only commands and public projection filtering."""

from uuid import UUID

from django.db.models import F, Q

from gravewright.maps.services import MapError, color, scene, title

from .models import ProgressClue

MAX_CLUES = 128
DEFAULT_FIELDS = {'name': '', 'content': '', 'gmNotes': '', 'segments': 4, 'value': 0,
                  'color': '#c9a44c', 'visibility': 'players', 'pinned': False}
CONFIG_FIELDS = frozenset(DEFAULT_FIELDS)
CONTEXT_FIELDS = {'sceneId', 'mapId'}
SCOPE_FIELDS = {'scopeSceneId'}
_INVALID = 'Invalid progress clue.'
_NOT_FOUND = 'Progress clue not found or access denied.'


def _keys(payload, allowed, required=()):
    if not isinstance(payload, dict) or set(payload) - set(allowed) or set(required) - set(payload):
        raise MapError(_INVALID)


def _integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise MapError(_INVALID)
    return value


def _identifier(value):
    if not isinstance(value, (str, UUID)):
        raise MapError(_NOT_FOUND, 'not_found')
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise MapError(_NOT_FOUND, 'not_found') from None


def validate_clue_fields(fields):
    """Validate portable configuration; callers validate campaign/scene references."""
    _keys(fields, CONFIG_FIELDS, CONFIG_FIELDS)
    segments = _integer(fields['segments'], 1, 24)
    if fields['visibility'] not in ('gm', 'players') or type(fields['pinned']) is not bool:
        raise MapError(_INVALID)
    for key in ('content', 'gmNotes'):
        if not isinstance(fields[key], str) or len(fields[key]) > 4000:
            raise MapError(_INVALID)
    return {
        'name': title(fields['name']), 'content': fields['content'], 'gmNotes': fields['gmNotes'],
        'segments': segments, 'value': _integer(fields['value'], 0, segments),
        'color': color(fields['color']), 'visibility': fields['visibility'], 'pinned': fields['pinned'],
    }


def _fields(row):
    return {key: getattr(row, 'gm_notes' if key == 'gmNotes' else key) for key in CONFIG_FIELDS}


def _gm(who):
    if who.role != 'gm':
        raise MapError('Only the GM can configure progress clues.', 'forbidden')


def project(row, who):
    # An explicit whitelist keeps private notes absent from public DTOs, including
    # completed discoveries. New model fields cannot silently become public.
    result = {
        'id': str(row.pk), 'name': row.name, 'content': row.content,
        'segments': row.segments, 'value': row.value, 'color': row.color,
        'visibility': row.visibility, 'pinned': row.pinned, 'version': row.version,
        'sceneId': str(row.scene_id) if row.scene_id else None,
        'discovered': row.value == row.segments,
        'canEdit': who.role == 'gm', 'canConfigure': who.role == 'gm',
    }
    if who.role == 'gm':
        result['gmNotes'] = row.gm_notes
    return result


def state(who, scene_id=None):
    target = scene(scene_id, who) if scene_id is not None else None
    rows = ProgressClue.objects.filter(campaign_id=who.campaign_id).filter(
        Q(scene__isnull=True) | Q(scene=target))
    if who.role != 'gm':
        rows = rows.filter(visibility='players', value=F('segments'))
    return {'clues': [project(row, who) for row in rows], 'is_gm': who.role == 'gm',
            'sceneId': str(target.pk) if target else None}


def _get(value, who):
    row = ProgressClue.objects.filter(pk=_identifier(value), campaign_id=who.campaign_id).first()
    if row is None:
        raise MapError(_NOT_FOUND, 'not_found')
    if row.scene_id:
        scene(row.scene_id, who)
    return row


def _context_scene(payload, who):
    ids = [_identifier(payload[key]) if payload[key] is not None else None
           for key in ('sceneId', 'mapId') if key in payload]
    if len(ids) == 2 and ids[0] != ids[1]:
        raise MapError(_INVALID)
    return scene(ids[0], who) if ids and ids[0] is not None else None


def _context(row, payload, who):
    if CONTEXT_FIELDS.intersection(payload):
        target = _context_scene(payload, who)
        if row.scene_id and (target is None or row.scene_id != target.pk):
            raise MapError(_NOT_FOUND, 'not_found')


def _assign(row, fields):
    for key, value in fields.items():
        setattr(row, 'gm_notes' if key == 'gmNotes' else key, value)


def _result(row, who):
    return {'id': str(row.pk), 'version': row.version, 'clue': project(row, who)}


def command(who, action, payload):
    """Apply one command inside table.domain's transaction and isolated receipt."""
    _gm(who)
    if not isinstance(action, str) or action not in ('create', 'update', 'advance', 'reset', 'delete', 'reveal', 'hide'):
        raise MapError('Invalid progress clue action.')
    allowed = {
        'create': CONFIG_FIELDS | CONTEXT_FIELDS | SCOPE_FIELDS,
        'update': CONFIG_FIELDS | CONTEXT_FIELDS | SCOPE_FIELDS | {'id', 'version'},
        'advance': CONTEXT_FIELDS | {'id', 'version', 'delta'},
        **{key: CONTEXT_FIELDS | {'id', 'version'} for key in ('reset', 'delete', 'reveal', 'hide')},
    }[action]
    required = ('name',) if action == 'create' else ('id', 'version', 'delta') if action == 'advance' else ('id', 'version')
    _keys(payload, allowed, required)
    if action == 'create':
        fields = validate_clue_fields({**DEFAULT_FIELDS, **{key: payload[key] for key in CONFIG_FIELDS if key in payload}})
        _context_scene(payload, who)
        scope_id = payload.get('scopeSceneId')
        target = scene(_identifier(scope_id), who) if scope_id is not None else None
        if ProgressClue.objects.filter(campaign_id=who.campaign_id).count() >= MAX_CLUES:
            raise MapError('A campaign can contain at most 128 progress clues.')
        row = ProgressClue(campaign_id=who.campaign_id, scene=target)
        _assign(row, fields)
        row.save()
        return _result(row, who)

    row = _get(payload['id'], who)
    _context(row, payload, who)
    from .domain import version
    version(row, payload)
    if action == 'delete':
        clue_id = str(row.pk)
        row.delete()
        return {'id': clue_id}
    if action == 'update':
        fields = {**_fields(row), **{key: payload[key] for key in CONFIG_FIELDS if key in payload}}
        if 'segments' in payload and 'value' not in payload:
            fields['value'] = min(row.value, _integer(payload['segments'], 1, 24))
        fields = validate_clue_fields(fields)
        target = row.scene
        if 'scopeSceneId' in payload:
            target = scene(_identifier(payload['scopeSceneId']), who) if payload['scopeSceneId'] is not None else None
        _assign(row, fields)
        row.scene = target
    elif action == 'advance':
        row.value = max(0, min(row.segments, row.value + _integer(payload['delta'], -24, 24)))
    elif action == 'reset':
        row.value = 0
    elif action == 'reveal':
        row.value, row.visibility = row.segments, 'players'
    elif action == 'hide':
        row.visibility = 'gm'
    row.version += 1
    row.save()
    return _result(row, who)


def validate_replay(who, action, payload, result):
    """A former GM must never replay a receipt containing private notes."""
    _gm(who)


def public_state(campaign_id, user_id, scene_id=None):
    from .domain import state as read
    return read(campaign_id, user_id, 'clues', scene_id)


def public_command(campaign_id, user_id, action, data, request_id):
    from .domain import command as execute
    return execute(campaign_id, user_id, 'clues', action, data, request_id)
