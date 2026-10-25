"""Validate ephemeral scene pointer positions and attach server-owned identity."""
import math

from gravewright.accounts.models import UserPreference
from . import services


def project(who, payload):
    if who.role not in ('gm', 'player'):
        raise services.MapError('Streamers have read-only access.', 'forbidden')
    row = services.scene(payload.get('mapId'), who)
    point = payload.get('position')
    if not isinstance(point, dict) or any(
        type(point.get(key)) not in (int, float) or not math.isfinite(point[key])
        or not 0 <= point[key] <= maximum for key, maximum in (('x', row.width), ('y', row.height))
    ):
        raise services.MapError('Pointer outside the map.')
    return {'mapId': str(row.pk), 'userId': str(who.user_id), 'name': who.user.name,
            'color': UserPreference.objects.filter(user_id=who.user_id).values_list('ping_color', flat=True).first() or '#f2c679',
            'position': {'x': point['x'], 'y': point['y']}}
