"""Owner-authorized server extension activation via the managed host."""
import os
from pathlib import Path
import shutil

from config.marketplace_apps import selections
from .packages import ModuleFailure, host


def queue_activation(row, enabled):
    from scripts.update_supervisor import write
    state = os.environ.get('GRAVEWRIGHT_MANAGED_STATE')
    if not state or os.environ.get('GRAVEWRIGHT_MANAGED_PROTOCOL') != '2':
        raise ModuleFailure('managed_start_required')
    if enabled:
        if row.revoked:
            raise ModuleFailure('permission_denied')
        host().verify_installed(row)
    elif selections(host().directory).get(row.module_id, {}).get('version') != row.version:
        raise ModuleFailure('conflict', 'This Django version is not active')
    folder = Path(state)
    try:
        (folder / 'job.lock').mkdir()
    except FileExistsError:
        raise ModuleFailure('update_in_progress') from None
    try:
        write(folder / 'progress.json', {'stage': 'queued', 'kind': 'django'})
        write(folder / 'job.json', {'kind': 'django', 'id': row.module_id, 'version': row.version, 'enabled': enabled})
    except BaseException:
        shutil.rmtree(folder / 'job.lock')
        raise
    return {'stage': 'queued', 'restartRequired': True}


def plan(module_id, version, enabled):
    from .models import Package
    engine = host()
    current = selections(engine.directory)
    if enabled:
        row = Package.objects.get(module_id=module_id, version=version, revoked=False)
        engine.verify_installed(row)
        if 'django' not in row.manifest:
            raise ModuleFailure('invalid_data')
        current[module_id] = {'id': module_id, 'version': version, 'digest': row.digest, 'django': row.manifest['django']}
    elif current.get(module_id, {}).get('version') == version:
        del current[module_id]
    for entry in list(current.values()):
        row = Package.objects.get(module_id=entry['id'], version=entry['version'])
        if row.revoked:
            del current[entry['id']]
            continue
        engine.verify_installed(row)
    return current
