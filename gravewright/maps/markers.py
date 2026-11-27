"""Shared area markers, with scene revisions and creator ownership."""
import hashlib
import json

from django.conf import settings
from gravewright.journals.services import identifier
from .models import SceneObject
from .objects import number, choice
from .services import MapError, color


def clean(row, who, previous=None):
    """Validate authored geometry; ownership always comes from the server."""
    if not isinstance(row, dict) or not isinstance(row.get('origin'), dict):
        raise MapError('Invalid area marker.')
    origin = row['origin']
    data = dict(kind=choice(row.get('kind'), {'line', 'circle', 'rect', 'cone', 'wide-cone'}),
                origin={k: number(origin.get(k), -100000, 100000) for k in ('x', 'y')},
                length=number(row.get('length'), 0, 100000), width=number(row.get('width', 0), 0, 100000),
                direction=number(row.get('direction', 0)) % 360, angle=number(row.get('angle', 90), 5, 170),
                color=color(row.get('color')), owner=previous['owner'] if previous else str(who.user_id))
    # Omitted optional fields retain their legacy representation and values.
    for key in ('audience', 'title', 'titleEnabled', 'points'):
        if key in row or previous and key in previous:
            data[key] = row.get(key, previous.get(key) if previous else None)
    audience = data.get('audience', 'campaign')
    choice(audience, {'campaign', 'gm'})
    if audience == 'gm' and who.role != 'gm':
        raise MapError('Only a GM can create private measurements.', 'forbidden')
    if 'title' in data and (not isinstance(data['title'], str) or len(data['title']) > 120
                            or any(c in data['title'] for c in '\r\n\t')):
        raise MapError('Invalid measurement title.')
    if 'titleEnabled' in data and type(data['titleEnabled']) is not bool:
        raise MapError('Invalid measurement title visibility.')
    if 'points' in data:
        points = data['points']
        if data['kind'] != 'line' or not isinstance(points, list) or not 2 <= len(points) <= 256:
            raise MapError('Invalid measurement path.')
        if any(not isinstance(p, dict) for p in points):
            raise MapError('Invalid measurement path.')
        data['points'] = [{k: number(p.get(k), -100000, 100000) for k in ('x', 'y')} for p in points]
    return data


def visible(rows, who):
    return [{**row, 'canEdit': who.role == 'gm' or who.role == 'player' and row.get('owner') == str(who.user_id)}
            for row in rows if who.role == 'gm' or row.get('audience', 'campaign') == 'campaign']


def receipt(payload):
    try:
        encoded = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    except (ValueError, TypeError):
        raise MapError('Invalid measurement changes.') from None
    return {'measurementPatch': hashlib.sha256(encoded).hexdigest()}


def replay(scene, who):
    from .objects import entry
    from .models import SceneState
    env = SceneState.objects.get(scene=scene)
    return {'version': env.version, 'markers': visible([entry(row) for row in SceneObject.objects.filter(scene=scene, kind='markers')], who)}


def patch(scene, who, env, payload):
    """Edit only named measurements, with independent compare-and-swap revisions."""
    from .objects import entry
    upserts, removed = payload.get('upserts', []), payload.get('removed', [])
    limit = settings.BOARD_MARKERS_MAX_PER_SCENE
    if not isinstance(upserts, list) or not isinstance(removed, list) or not 1 <= len(upserts) + len(removed) <= limit:
        raise MapError('Invalid measurement changes.')
    current = {str(row.pk): row for row in SceneObject.objects.filter(scene=scene, kind='markers')}
    seen, updates, deletions = set(), [], []
    for deleting, rows in ((False, upserts), (True, removed)):
        for value in rows:
            if not isinstance(value, dict):
                raise MapError('Invalid measurement changes.')
            key = str(identifier(value.get('id')))
            if key in seen:
                raise MapError('Duplicate measurement identifier.')
            seen.add(key)
            previous = current.get(key)
            if previous and (who.role != 'gm' and (previous.data.get('audience') == 'gm'
                                                   or previous.data['owner'] != str(who.user_id))):
                raise MapError('You do not control this marker.', 'forbidden')
            expected = value.get('expected_version')
            if previous:
                if type(expected) is not int or expected != previous.version:
                    raise MapError('The measurement changed. Refresh before editing.', 'conflict')
            elif deleting or expected is not None or SceneObject.objects.filter(pk=key).exists():
                raise MapError('The measurement changed. Refresh before editing.', 'conflict')
            if deleting:
                deletions.append(previous)
            else:
                updates.append((key, previous, clean(value, who, previous.data if previous else None)))
    if len(current) - len(deletions) + sum(previous is None for _, previous, _ in updates) > limit:
        raise MapError('This scene has too many markers.')
    for row in deletions:
        row.delete()
    for key, previous, data in updates:
        if previous is None:
            SceneObject.objects.create(pk=key, scene=scene, kind='markers', data=data)
        else:
            previous.data = data
            previous.version += 1
            previous.save(update_fields=['data', 'version'])
    env.version += 1
    env.save(update_fields=['version'])
    return {'version': env.version, 'markers': visible([entry(row) for row in SceneObject.objects.filter(scene=scene, kind='markers')], who)}


def replace(scene, who, env, payload):
    if type(payload.get('expected_version')) is not int or payload['expected_version'] != env.version:
        raise MapError('Scene markers changed. Refresh before editing.', 'conflict')
    rows = payload.get('rows')
    if not isinstance(rows, list) or len(rows) > settings.BOARD_MARKERS_MAX_PER_SCENE:
        raise MapError('This scene has too many markers.')
    all_rows = list(SceneObject.objects.filter(scene=scene, kind='markers'))
    current = {str(row.pk): row for row in all_rows
               if who.role == 'gm' or row.data.get('audience', 'campaign') == 'campaign'}
    if len(rows) + len(all_rows) - len(current) > settings.BOARD_MARKERS_MAX_PER_SCENE:
        raise MapError('This scene has too many markers.')
    incoming = {}
    for row in rows:
        if not isinstance(row, dict):
            raise MapError('Invalid area marker.')
        key = str(identifier(row.get('id')))
        if key in incoming:
            raise MapError('Duplicate area marker.')
        previous = current.get(key)
        data = clean(row, who, previous.data if previous else None)
        if previous and who.role!='gm' and previous.data['owner']!=str(who.user_id) and data!=previous.data:
            raise MapError('You do not control this marker.', 'forbidden')
        if not previous and SceneObject.objects.filter(pk=key).exists():
            raise MapError('Invalid marker identifier.')
        incoming[key] = data
    for key, row in current.items():
        if key not in incoming:
            if who.role!='gm' and row.data['owner']!=str(who.user_id):
                raise MapError('You do not control this marker.', 'forbidden')
            row.delete()
    for key, data in incoming.items():
        row = current.get(key)
        if row is None:
            SceneObject.objects.create(pk=key,scene=scene,kind='markers',data=data)
        elif row.data!=data:
            row.data=data;row.version+=1;row.save()
    env.version+=1;env.save()
    return {}
