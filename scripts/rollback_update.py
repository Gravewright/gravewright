"""Restore a retained .old installation and matching data with the server stopped."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.process_control import instance_lock
from scripts.project_files import checked_path, replace_files, source_files
from scripts.update_supervisor import Supervisor, read, write


def rollback(old):
    old = Path(old).resolve()
    metadata = old / '.gravewright-rollback'
    installation = read(metadata / 'installation.json')
    journal = read(metadata / 'project.json')
    if not installation or not journal or not read(metadata / 'complete.json'):
        raise ValueError('This is not a complete Gravewright .old backup')
    origin, state = Path(installation['origin']).resolve(), Path(installation['state']).resolve()
    if old == origin or old.is_relative_to(origin) or origin.is_relative_to(old):
        raise ValueError('The rollback copy must be separate from the installation')
    with instance_lock(state / 'supervisor.lock'):
        supervisor = Supervisor(origin, state, installation['database'], installation['media'], '127.0.0.1', 3000)
        supervisor.extra_paths = {key: Path(value) for key, value in installation['extra_paths'].items()}
        supervisor.protected += list(supervisor.extra_paths.values())
        supervisor.protected += [Path(path).resolve() for path in installation.get('protected', [])]
        if read(state / 'transaction.json'):
            raise ValueError('Recover the interrupted update before restoring a retained backup')
        # Validate the entire source before touching the current installation.
        for name in journal['project_files']:
            if not checked_path(old, name).is_file():
                raise ValueError('The .old project copy is incomplete')
        supervisor.restore(metadata)
        replace_files(old, origin, journal['project_files'], source_files(origin, supervisor.protected))
        write(state / 'active.json', {'path': journal['previous'], 'python': journal['previous_python']})
        (state / 'maintenance').unlink(missing_ok=True)
        (state / 'job.json').unlink(missing_ok=True)
        supervisor.notify('rolled_back')
    return origin


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('old', type=Path, help='Path to the retained project.old folder.')
    args = parser.parse_args()
    print(f'Restored: {rollback(args.old)}')
