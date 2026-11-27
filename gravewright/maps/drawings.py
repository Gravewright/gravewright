"""Shared scene drawings with server-owned authorship, privacy and per-drawing revisions.

Drawings stay in the scene document (``SceneState.drawings``). Each row records the
participant who created it and its own revision, so participants can draw at the
same time without replacing each other's work. Players draw on the table layer and
edit only their own drawings; GMs edit every drawing and keep GM-layer drawings
private.
"""
import hashlib
import json

from gravewright.journals.services import identifier
from .extra_objects import drawing
from .services import MapError

MAX_DRAWINGS = 500
MAX_POINTS = 50000
SERVER_FIELDS = ('owner', 'version')


def document(env):
    doc = env.drawings if env and isinstance(env.drawings, dict) else {}
    rows = doc.get('rows') if isinstance(doc.get('rows'), list) else []
    version = doc.get('version') if type(doc.get('version')) is int else 0
    return version, rows


def revision(row):
    value = row.get('version')
    return value if type(value) is int and value > 0 else 1


def editable(row, who):
    if who.role == 'gm':
        return True
    return (who.role == 'player' and row.get('audience') == 'campaign'
            and row.get('owner') is not None and row.get('owner') == str(who.user_id))


def visible(rows, who):
    """Recipient projection: GM-layer rows stay with GMs; ``canEdit`` mirrors the server rule."""
    return [{**row, 'version': revision(row), 'canEdit': editable(row, who)}
            for row in rows if who.role == 'gm' or row.get('audience') == 'campaign']


def authored(row):
    return {key: value for key, value in row.items() if key not in SERVER_FIELDS}


def stamped(data, who, previous, changed=True):
    """Authorship and revisions come from the server, never from the payload."""
    if previous is None:
        return {**data, 'owner': str(who.user_id), 'version': 1}
    if previous.get('owner') is not None:
        data['owner'] = previous['owner']
    data['version'] = revision(previous) + (1 if changed else 0)
    return data


def check_limits(rows):
    if len(rows) > MAX_DRAWINGS:
        raise MapError('Use up to 500 drawings.')
    if sum(len(row['points']) for row in rows) > MAX_POINTS:
        raise MapError('Drawing point limit reached.')


def replace(env, who, payload):
    """Legacy GM document replacement, preserving each row's author and revision."""
    version, current = document(env)
    if payload.get('expected_version') != version:
        raise MapError('Drawings changed. Refresh and try again.', 'conflict')
    rows = payload.get('rows')
    if not isinstance(rows, list) or len(rows) > MAX_DRAWINGS:
        raise MapError('Use up to 500 drawings.')
    cleaned = [drawing(row) for row in rows]
    if len({row['id'] for row in cleaned}) != len(cleaned):
        raise MapError('Duplicate drawing identifier.')
    previous = {str(row.get('id')): row for row in current}
    result = []
    for data in cleaned:
        before = previous.get(data['id'])
        result.append(stamped(data, who, before, before is None or authored(before) != data))
    check_limits(result)
    env.drawings = {'version': version + 1, 'rows': result}
    return {'version': version + 1, 'rows': visible(result, who)}


def patch(env, who, payload):
    """Create, edit or remove named drawings, each with its own compare-and-swap revision."""
    upserts, removed = payload.get('upserts', []), payload.get('removed', [])
    if (not isinstance(upserts, list) or not isinstance(removed, list)
            or not 1 <= len(upserts) + len(removed) <= MAX_DRAWINGS):
        raise MapError('Invalid drawing changes.')
    version, current = document(env)
    index = {str(row.get('id')): row for row in current}
    seen, changes, added = set(), {}, []
    for deleting, values in ((False, upserts), (True, removed)):
        for value in values:
            if not isinstance(value, dict):
                raise MapError('Invalid drawing changes.')
            key = str(identifier(value.get('id')))
            if key in seen:
                raise MapError('Duplicate drawing identifier.')
            seen.add(key)
            previous = index.get(key)
            if previous is not None and not editable(previous, who):
                raise MapError('You do not control this drawing.', 'forbidden')
            expected = value.get('expected_version')
            if previous is not None:
                if type(expected) is not int or expected != revision(previous):
                    raise MapError('The drawing changed. Refresh before editing.', 'conflict')
            elif deleting or expected is not None:
                raise MapError('The drawing changed. Refresh before editing.', 'conflict')
            if deleting:
                changes[key] = None
                continue
            data = drawing(value)
            if data['audience'] == 'gm' and who.role != 'gm':
                raise MapError('Only a GM can create private drawings.', 'forbidden')
            changes[key] = stamped(data, who, previous)
            if previous is None:
                added.append(key)
    result = [changes.get(str(row.get('id')), row) for row in current]
    result = [row for row in result if row is not None] + [changes[key] for key in added]
    check_limits(result)
    env.drawings = {'version': version + 1, 'rows': result}
    return {'version': version + 1, 'rows': visible(result, who)}


def receipt(payload):
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    except (ValueError, TypeError):
        raise MapError('Invalid drawing changes.') from None
    return {'drawingPatch': hashlib.sha256(encoded).hexdigest()}


def replay(scene, who):
    """A retried patch returns the current projection, filtered for the caller's current role."""
    from .models import SceneState
    version, rows = document(SceneState.objects.filter(scene=scene).first())
    return {'version': version, 'rows': visible(rows, who)}
