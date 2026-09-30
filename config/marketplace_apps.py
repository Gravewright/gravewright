"""Load the supervisor's verified, persistent Django package selection."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import zipfile


def registry_path(directory):
    return Path(os.environ.get('GRAVEWRIGHT_DJANGO_REGISTRY', Path(directory) / 'server-apps.json'))


def selections(directory):
    path = registry_path(directory)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def load_apps(directory):
    directory = Path(directory).resolve()
    apps = []
    for row in selections(directory).values():
        root = (directory / 'packages' / row['id'] / row['version'] / row['digest']).resolve()
        if not root.is_relative_to(directory / 'packages'):
            raise ValueError('Invalid Django package location')
        archive = (directory / 'archives' / (row['digest'] + '.zip')).resolve()
        if not archive.is_relative_to(directory / 'archives'):
            raise ValueError('Invalid Django archive location')
        raw = archive.read_bytes()
        if hashlib.sha256(raw).hexdigest() != row['digest']:
            raise ValueError('Django package archive changed')
        with zipfile.ZipFile(io.BytesIO(raw)) as package:
            names = {e.filename for e in package.infolist() if not e.is_dir()}
            if names != {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}:
                raise ValueError('Django package files changed')
            for name in names:
                path = root / name
                if (not path.resolve().is_relative_to(root) or any(p.is_symlink() for p in (path, *path.parents))
                        or path.read_bytes() != package.read(name)):
                    raise ValueError('Django package files changed')
            manifest = json.loads(package.read('manifest.json'))
            if manifest['django'] != row['django']:
                raise ValueError('Django package configuration changed')
        # Immutable packages must not acquire __pycache__ files during imports.
        sys.dont_write_bytecode = True
        sys.path.append(str(root))
        apps.extend(row['django']['apps'])
    if len(apps) != len(set(apps)):
        raise ValueError('Duplicate marketplace Django apps')
    return apps
