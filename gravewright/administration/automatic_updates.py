"""Owner-authorized handoff to the source-installation supervisor."""
import os
from pathlib import Path
import shutil
import subprocess
from django.conf import settings
from gravewright.accounts.services import AuthError
from .updates import CoreUpdateService


def status():
    from scripts.update_supervisor import read
    state = os.environ.get('GRAVEWRIGHT_MANAGED_STATE')
    if not state:
        return {'supported': False, 'reason': 'managed_start_required', 'stage': 'idle'}
    progress = read(Path(state) / 'progress.json', {'stage': 'idle'})
    return {**progress, 'supported': True, 'busy': (Path(state) / 'job.lock').exists()}


def request_update(version):
    from scripts.update_supervisor import write
    state = os.environ.get('GRAVEWRIGHT_MANAGED_STATE')
    if not state:
        raise AuthError('managed_start_required', 409)
    root = settings.BASE_DIR
    if (root / '.git').exists():
        result = subprocess.run(['git', 'status', '--porcelain'], cwd=root, capture_output=True, text=True, timeout=10, check=True)
        if result.stdout.strip():
            raise AuthError('local_changes_present', 409)
    folder = Path(state)
    try:
        (folder / 'job.lock').mkdir()
    except FileExistsError:
        raise AuthError('update_in_progress', 409) from None
    try:
        result = CoreUpdateService().check()
        if result['status'] != 'available' or result['availableVersion'] != version:
            raise AuthError('release_changed', 409)
        write(folder / 'progress.json', {'stage': 'queued', 'version': version})
        write(folder / 'job.json', {'version': version, 'artifact': result['artifact']})
    except BaseException:
        shutil.rmtree(folder / 'job.lock')
        raise
    return status()
