"""Combat clocks for conditions attached to participating scene tokens."""
from gravewright.maps.services import MapError
from gravewright.tokens.models import Token


def duration(value):
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) - {'type', 'value', 'expires'}:
        raise MapError('Invalid condition duration.')
    unit, count, phase = value.get('type'), value.get('value'), value.get('expires', 'end')
    if unit not in ('turns', 'rounds') or type(count) is not int or not 1 <= count <= 10000 or phase not in ('start', 'end'):
        raise MapError('Invalid condition duration.')
    return {'type': unit, 'value': count, 'remaining': count, 'expires': phase}


def advance(encounter, phase, entry, *, round_boundary=False):
    """Advance only forward, inside the command's transaction and retry receipt."""
    ids = [item['tokenId'] for item in encounter.combatants if item.get('tokenId')]
    if not round_boundary:
        ids = [entry['tokenId']] if entry.get('tokenId') in ids else []
    for token in Token.objects.filter(scene=encounter.scene, pk__in=ids).only('id','conditions','version'):
        kept, changed = [], False
        for condition in token.conditions:
            clock = condition.get('duration')
            tick = isinstance(clock, dict) and clock.get('expires', 'end') == phase and (
                clock.get('type') == 'rounds' and round_boundary or
                clock.get('type') == 'turns' and str(token.pk) == entry.get('tokenId'))
            remaining = clock.get('remaining', clock.get('value')) if isinstance(clock, dict) else None
            if tick and type(remaining) is int and remaining > 0:
                changed = True
                clock['remaining'] = remaining - 1
                if clock['remaining'] == 0:
                    continue
            kept.append(condition)
        if changed:
            token.conditions = kept
            token.version += 1
            token.save(update_fields=['conditions', 'version'])
