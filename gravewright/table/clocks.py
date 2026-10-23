"""Campaign progress clocks with current membership, scene and revision checks.

Raw membership-based helpers are called only inside table.domain. Public entry
points retain that domain's transaction, receipt and post-commit notifications.
"""

from uuid import UUID

from django.db.models import Q

from gravewright.maps.services import MapError, color, scene, title

from .models import ProgressClock

MAX_CLOCKS = 128
DEFAULT_FIELDS = {'name': '', 'description': '', 'segments': 4, 'value': 0, 'color': '#c9a44c',
                  'visibility': 'gm', 'playersCanEdit': False, 'pinned': False}
CONFIG_FIELDS = frozenset(DEFAULT_FIELDS)
CONTEXT_FIELDS = {'sceneId', 'mapId'}
SCOPE_FIELDS = {'scopeSceneId'}
_INVALID = 'Invalid progress clock.'
_NOT_FOUND = 'Progress clock not found or access denied.'


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


def validate_clock_fields(fields):
    """Validate a complete portable field record; no membership or DB access.

    Archives must separately validate the clock's campaign and scene references.
    Field names follow the public camelCase configuration contract.
    """
    _keys(fields, CONFIG_FIELDS, CONFIG_FIELDS)
    segments = _integer(fields['segments'], 2, 24)
    if fields['visibility'] not in ('gm', 'players'):
        raise MapError(_INVALID)
    if type(fields['playersCanEdit']) is not bool or type(fields['pinned']) is not bool:
        raise MapError(_INVALID)
    if not isinstance(fields['description'], str) or len(fields['description']) > 4000:
        raise MapError(_INVALID)
    return {
        'name': title(fields['name']), 'description': fields['description'], 'segments': segments,
        'value': _integer(fields['value'], 0, segments), 'color': color(fields['color']),
        'visibility': fields['visibility'], 'playersCanEdit': fields['playersCanEdit'],
        'pinned': fields['pinned'],
    }


def _fields(row):
    return {key: getattr(row, {'playersCanEdit': 'players_can_edit'}.get(key, key)) for key in CONFIG_FIELDS}


def _gm(who):
    if who.role != 'gm':
        raise MapError('Only the GM can configure progress clocks.', 'forbidden')


def _can_edit(row, who):
    return who.role == 'gm' or (who.role == 'player' and row.visibility == 'players' and row.players_can_edit)


def project(row, who):
    return {
        'id': str(row.pk), **_fields(row), 'version': row.version,
        'sceneId': str(row.scene_id) if row.scene_id else None,
        'canEdit': _can_edit(row, who), 'canConfigure': who.role == 'gm',
    }


def state(who, scene_id=None):
    target = scene(scene_id, who) if scene_id is not None else None
    rows = ProgressClock.objects.filter(campaign_id=who.campaign_id).filter(
        Q(scene__isnull=True) | Q(scene=target))
    if who.role != 'gm':
        rows = rows.filter(visibility='players')
    return {'clocks': [project(row, who) for row in rows], 'is_gm': who.role == 'gm',
            'sceneId': str(target.pk) if target else None}


def _get(value, who):
    row = ProgressClock.objects.filter(pk=_identifier(value), campaign_id=who.campaign_id).first()
    if row is None or who.role != 'gm' and row.visibility != 'players':
        raise MapError(_NOT_FOUND, 'not_found')
    if row.scene_id:
        scene(row.scene_id, who)
    return row


def _context_scene(payload, who):
    """Resolve SDK scene aliases; supplied aliases must identify the same scope."""
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
        setattr(row, {'playersCanEdit': 'players_can_edit'}.get(key, key), value)


def _result(row, who):
    return {'id': str(row.pk), 'version': row.version, 'clock': project(row, who)}


def command(who, action, payload):
    """Apply one already serialized domain command, without bypassing its receipt."""
    if who.role == 'streamer':
        raise MapError('Streamers have read-only access.', 'forbidden')
    if not isinstance(action, str) or action not in ('create', 'update', 'advance', 'reset', 'delete'):
        raise MapError('Invalid progress clock action.')
    allowed = {
        'create': CONFIG_FIELDS | CONTEXT_FIELDS | SCOPE_FIELDS,
        'update': CONFIG_FIELDS | CONTEXT_FIELDS | SCOPE_FIELDS | {'id', 'version'},
        'advance': CONTEXT_FIELDS | {'id', 'version', 'delta'},
        'reset': CONTEXT_FIELDS | {'id', 'version'},
        'delete': CONTEXT_FIELDS | {'id', 'version'},
    }[action]
    required = ('name',) if action == 'create' else ('id', 'version', 'delta') if action == 'advance' else ('id', 'version')
    _keys(payload, allowed, required)
    if action != 'advance':
        _gm(who)
    if action == 'create':
        fields = validate_clock_fields({**DEFAULT_FIELDS, **{key: payload[key] for key in CONFIG_FIELDS if key in payload}})
        _context_scene(payload, who)
        scope_id = payload.get('scopeSceneId')
        target = scene(_identifier(scope_id), who) if scope_id is not None else None
        if ProgressClock.objects.filter(campaign_id=who.campaign_id).count() >= MAX_CLOCKS:
            raise MapError('A campaign can contain at most 128 progress clocks.')
        row = ProgressClock(campaign_id=who.campaign_id, scene=target)
        _assign(row, fields)
        row.save()
        return _result(row, who)

    row = _get(payload['id'], who)
    _context(row, payload, who)
    if action == 'advance' and not _can_edit(row, who):
        raise MapError('Only editable public clocks can be advanced by players.', 'forbidden')
    from .domain import version
    version(row, payload)
    if action == 'delete':
        clock_id = str(row.pk)
        row.delete()
        return {'id': clock_id}
    if action == 'update':
        fields = {**_fields(row), **{key: payload[key] for key in CONFIG_FIELDS if key in payload}}
        if 'segments' in payload and 'value' not in payload:
            fields['value'] = min(row.value, _integer(payload['segments'], 2, 24))
        fields = validate_clock_fields(fields)
        target = row.scene
        if 'scopeSceneId' in payload:
            target = scene(_identifier(payload['scopeSceneId']), who) if payload['scopeSceneId'] is not None else None
        _assign(row, fields)
        row.scene = target
    elif action == 'advance':
        row.value = max(0, min(row.segments, row.value + _integer(payload['delta'], -24, 24)))
    elif action == 'reset':
        row.value = 0
    row.version += 1
    row.save()
    return _result(row, who)


def validate_replay(who, action, payload, result):
    """Recheck live visibility before replaying a stored command projection.

    A former GM cannot retrieve a private GM receipt after becoming a player.
    Player retries also stop working when a clock becomes private or read-only.
    Revisions intentionally stay unchecked: a legitimate retry returns its receipt.
    """
    if who.role == 'gm':
        return
    prior = result.get('clock', {})
    if who.role != 'player' or action != 'advance' or prior.get('canConfigure'):
        raise MapError('Only editable public clocks can be advanced by players.', 'forbidden')
    row = _get(prior.get('id'), who)
    _context(row, payload, who)
    if not _can_edit(row, who):
        raise MapError('Only editable public clocks can be advanced by players.', 'forbidden')


def public_state(campaign_id, user_id, scene_id=None):
    from .domain import state as read
    return read(campaign_id, user_id, 'clocks', scene_id)


def public_command(campaign_id, user_id, action, data, request_id):
    from .domain import command as execute
    return execute(campaign_id, user_id, 'clocks', action, data, request_id)
