"""Clock-based playback projection shared by reads and transport commands."""
from copy import deepcopy


def project(entry, duration, now):
    result = deepcopy(entry)
    position = result.get('position', 0)
    if result['status'] == 'playing':
        position += max(0, now - result['startedAt'])
    if duration > 0:
        if result.get('loop'):
            position %= duration
        elif position >= duration:
            position = duration
            result['status'] = 'stopped'
    result['position'] = position
    result['startedAt'] = now
    return result
