"""Shared area markers, with scene revisions and creator ownership."""
from django.conf import settings
from gravewright.journals.services import identifier
from .models import SceneObject
from .objects import number, choice
from .services import MapError, color


def replace(scene, who, env, payload):
    if type(payload.get('expected_version')) is not int or payload['expected_version'] != env.version:
        raise MapError('Scene markers changed. Refresh before editing.', 'conflict')
    rows = payload.get('rows')
    if not isinstance(rows, list) or len(rows) > settings.BOARD_MARKERS_MAX_PER_SCENE:
        raise MapError('This scene has too many markers.')
    current = {str(row.pk): row for row in SceneObject.objects.filter(scene=scene, kind='markers')}
    incoming = {}
    for row in rows:
        if not isinstance(row, dict):
            raise MapError('Invalid area marker.')
        key = str(identifier(row.get('id')))
        if key in incoming:
            raise MapError('Duplicate area marker.')
        origin = row.get('origin')
        if not isinstance(origin, dict):
            raise MapError('Invalid marker origin.')
        previous = current.get(key)
        data = dict(kind=choice(row.get('kind'), {'line','circle','rect','cone','wide-cone'}),
                    origin={'x':number(origin.get('x'),-100000,100000),'y':number(origin.get('y'),-100000,100000)},
                    length=number(row.get('length'),0,100000),width=number(row.get('width',0),0,100000),
                    direction=number(row.get('direction',0))%360,angle=number(row.get('angle',90),5,170),
                    color=color(row.get('color')),
                    owner=previous.data['owner'] if previous else str(who.user_id))
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
