"""Validate ephemeral scene pointer positions and attach server-owned identity."""
import math

from gravewright.accounts.models import UserPreference
from . import services


def project(who, payload):
    return place(identity(who, payload.get('mapId')), payload.get('position'))


def identity(who, map_id):
    """The server-owned part of a pointer on a scene this member may see."""
    if who.role not in ('gm', 'player'):
        raise services.MapError('Streamers have read-only access.', 'forbidden')
    row = services.scene(map_id, who)
    return {'mapId': str(row.pk), 'userId': str(who.user_id), 'name': who.user.name,
            'color': UserPreference.objects.filter(user_id=who.user_id).values_list('ping_color', flat=True).first() or '#f2c679',
            'width': row.width, 'height': row.height}


def place(identity, point):
    """A pointer packet at ``point`` within the identity's scene. No database access."""
    if not isinstance(point, dict) or any(
        type(point.get(key)) not in (int, float) or not math.isfinite(point[key])
        or not 0 <= point[key] <= maximum for key, maximum in (('x', identity['width']), ('y', identity['height']))
    ):
        raise services.MapError('Pointer outside the map.')
    return {'mapId': identity['mapId'], 'userId': identity['userId'], 'name': identity['name'],
            'color': identity['color'], 'position': {'x': point['x'], 'y': point['y']}}
