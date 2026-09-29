"""Immutable startup recovery, kept outside the replaceable project directory."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import uuid


@contextmanager
def data_lock(directory):
    with (directory / 'runner.lock').open('a+b') as handle:
        if handle.seek(0, 2) == 0:
            handle.write(b'\0'); handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def recover_source(project, data):
    """Repair interrupted source replacement before importing any project code.

    The restored supervisor completes database/media recovery from the same
    journal. Leave that journal intact until the regular recovery commits.
    """
    transaction = data / 'updates/transaction.json'
    if not transaction.exists():
        return sys.executable
    with data_lock(data):
        if not transaction.exists():
            return sys.executable
        journal = json.loads(transaction.read_text(encoding='utf-8'))
        if 'project_files' not in journal:
            return sys.executable
        backup = (data / 'updates/backups' / journal['backup'] / 'project').resolve()
        if not backup.is_relative_to((data / 'updates/backups').resolve()):
            raise ValueError('Invalid recovery backup path')

        def path(root, name):
            value = (root / name).resolve()
            if value == root or not value.is_relative_to(root):
                raise ValueError('Invalid recovery project path')
            return value

        previous = journal['project_files']
        for name in previous:
            if not path(backup, name).is_file():
                raise ValueError('Incomplete project recovery copy')
        for name in sorted(set(journal['incoming_files']) - set(previous), reverse=True):
            destination = path(project, name)
            destination.unlink(missing_ok=True)
            parent = destination.parent
            while parent != project:
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent
        for name in previous:
            destination = path(project, name)
            if destination.is_dir():
                destination.rmdir()
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name('.recover-' + uuid.uuid4().hex)
            try:
                shutil.copy2(path(backup, name), temporary)
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
            cache = destination.parent / '__pycache__'
            if name.endswith('.py') and cache.exists():
                if not cache.resolve().is_relative_to(project):
                    raise ValueError('Invalid recovery cache path')
                shutil.rmtree(cache)
        return journal['previous_python']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--data-dir', type=Path, required=True)
    args, remaining = parser.parse_known_args()
    try:
        project, data = args.project.resolve(), args.data_dir.resolve()
        python = recover_source(project, data)
        command = [python, '-X', 'utf8', str(project / 'scripts/gravewright_runner.py'),
                   '--data-dir', str(data), *remaining]
        if os.name == 'nt':
            # subprocess quotes Windows paths correctly; execv does not. The
            # child shares the console and handles Ctrl+C/Break itself.
            with subprocess.Popen(command) as child:
                signal.signal(signal.SIGINT, lambda *_: None)
                signal.signal(signal.SIGBREAK, lambda *_: None)
                raise SystemExit(child.wait())
        os.execv(python, command)
    except (OSError, ValueError) as error:
        print(f'Runner recovery/startup failed: {error}', file=sys.stderr)
        raise SystemExit(1)
