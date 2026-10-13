"""Build the VTT source ZIP from public Git files, without local installations.

Run ``python scripts/build_release.py`` after staging the release's new files.
Use ``--include-untracked`` only for a reviewable working-tree snapshot before
staging. Neither mode reads ignored runtime files or bundles installed systems.
The ZIP contains working-tree bytes, including pending edits to selected files.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import tomllib
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gravewright.administration.release_metadata import normalize_version, update_version_is_valid
from scripts.project_files import source_files


MAX_FILES = 100_000
MAX_EXPANDED_BYTES = 2 * 1024**3
MAX_ARCHIVE_BYTES = 1024**3


def metadata(root):
    project = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))['project']
    package_version = project['version']
    version = normalize_version(package_version)
    if not update_version_is_valid(version):
        raise ValueError('pyproject.toml has an invalid public release version')
    lock = tomllib.loads((root / 'uv.lock').read_text(encoding='utf-8'))
    packages = [item for item in lock['package'] if item['name'] == project['name']]
    if len(packages) != 1 or packages[0]['version'] != package_version:
        raise ValueError('uv.lock must match the pyproject.toml project version')
    folder = root / 'gravewright/maps/frontend'
    frontend = json.loads((folder / 'package.json').read_text(encoding='utf-8'))
    frontend_lock = json.loads((folder / 'package-lock.json').read_text(encoding='utf-8'))
    if not (frontend['version'] == frontend_lock['version']
            == frontend_lock['packages']['']['version'] == version):
        raise ValueError('Frontend package.json and package-lock.json must match the public version')
    notes = f'docs/releases/{version}.md'
    if not (root / notes).is_file() or not (root / notes).read_text(encoding='utf-8').strip():
        raise ValueError(f'Missing release notes: {notes}')
    return version, notes


def git_files(root, *, untracked=False):
    args = ['git', 'ls-files', '--others', '--exclude-standard', '-z'] if untracked else [
        'git', 'ls-files', '--cached', '-z',
    ]
    result = subprocess.run(args, cwd=root, check=True, stdout=subprocess.PIPE)
    return {name for name in result.stdout.decode('utf-8').split('\0') if name}


def extension_readme(name):
    parts = PurePosixPath(name).parts
    return (len(parts) == 3 and parts[:2] in [('extensions', 'api'), ('extensions', 'django')]
            and parts[2].startswith('README') and parts[2].endswith('.md'))


def public_path(name):
    """Apply release exclusions even if a local file was force-added to Git."""
    path = PurePosixPath(name)
    parts = path.parts
    if not parts or path.is_absolute() or any(part in ('', '.', '..') for part in parts):
        return False
    if '\\' in name or ':' in name or name.startswith(('dist/', 'build/')):
        return False
    if parts[0] == 'extensions':
        return extension_readme(name)
    if parts[0] == 'data':
        return name == 'data/.gitkeep'
    if path.name in ('Gravewright Runner.bat', 'Gravewright Runner.lnk',
                     'Gravewright Runner.sh', 'Gravewright Runner.command',
                     'Gravewright Runner.desktop'):
        return False
    if path.name.startswith('.Gravewright-') and path.suffix in ('.bat', '.lnk', '.sh', '.command', '.desktop'):
        return False
    if path.name.startswith('.env') and path.name != '.env.example':
        return False
    return True


def checked_file(root, name):
    path = root / name
    for candidate in (path, *path.parents):
        if candidate == root:
            break
        if candidate.is_symlink() or candidate.is_junction():
            raise ValueError(f'Release files cannot be links or junctions: {name}')
    if not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError(f'Release file is missing or outside the project: {name}')
    return path


def selection(root, output, *, include_untracked=False):
    tracked = git_files(root)
    extra = git_files(root, untracked=True) if include_untracked else set()
    # Do not traverse installed extensions, archives or private runtime storage.
    available = set(source_files(root, protected=(root / 'extensions', root / 'dist', root / 'build', output)))
    available |= {name for name in tracked | extra if extension_readme(name) or name == 'data/.gitkeep'}
    names = sorted(name for name in (tracked | extra) & available if public_path(name))
    seen = set()
    total = 0
    for name in names:
        key = name.casefold()
        if key in seen:
            raise ValueError(f'Duplicate release path on Windows: {name}')
        seen.add(key)
        total += checked_file(root, name).stat().st_size
    if not names or len(names) > MAX_FILES or total > MAX_EXPANDED_BYTES:
        raise ValueError('Release exceeds the updater expanded-size/file-count limits')
    return names, sorted(set(names) & extra), total


def required_files(notes):
    return {
        'pyproject.toml', 'uv.lock', 'main.py', 'manage.py', '.env.example',
        'Install Windows.bat', 'Install Linux.sh', 'Install macOS.command',
        'scripts/posix/install.sh', 'scripts/posix/create_runner.py', 'scripts/posix/runner.sh',
        'scripts/posix/mac_tools.sh', 'scripts/posix/mac_build.py',
        'scripts/windows/create_runner.py', 'scripts/windows/runner.bat',
        'scripts/windows/launch_runner.py', 'scripts/prepare_frontend.py',
        'gravewright/maps/scripts/build.cjs',
        'config/managed_asgi.py', 'scripts/managed_server.py',
        'scripts/build_release.py', 'scripts/update_supervisor.py',
        'gravewright/maps/frontend/package.json', 'gravewright/maps/frontend/package-lock.json',
        'gravewright/maps/static/gravewright_maps/vendor/board.js',
        'gravewright/administration/release_presentation.py',
        'gravewright/table/static/gravewright_table/modal.js',
        'gravewright/web/icons/Bell-regular.svg',
        'gravewright/web/jinja2/gravewright_web/inside/updates.html',
        'gravewright/web/jinja2/gravewright_web/inside/update-notification.html',
        'gravewright/web/static/gravewright_web/inside/release-notes.js',
        'gravewright/web/static/gravewright_web/inside/update-notification.js',
        'gravewright/web/static/gravewright_web/inside/update-notification.css',
        'gravewright/modules/static/gravewright_modules/i18n.js',
        'gravewright/modules/locale_overrides/es.json', 'LICENSE', 'LICENSE-EXCEPTION', notes,
    }


def archive_timestamp():
    """Use current time by default; SOURCE_DATE_EPOCH enables reproducible builds."""
    epoch = os.environ.get('SOURCE_DATE_EPOCH')
    moment = datetime.fromtimestamp(int(epoch), timezone.utc) if epoch else datetime.now(timezone.utc)
    if not 1980 <= moment.year <= 2107:
        raise ValueError('ZIP timestamp must be between 1980 and 2107')
    return moment.timetuple()[:6]


def atomic_text(path, value):
    descriptor, name = tempfile.mkstemp(prefix='.release-', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(value)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def build(root=ROOT, *, output_dir=None, include_untracked=False, check=False):
    root = Path(root).resolve()
    output = Path(output_dir).resolve() if output_dir else root / 'dist'
    if output == root:
        raise ValueError('Output directory must differ from the source root')
    version, notes = metadata(root)
    names, extra, expanded = selection(root, output, include_untracked=include_untracked)
    missing = required_files(notes) - set(names)
    if missing:
        raise ValueError('Required public files are not selected; stage new files or use '
                         '--include-untracked for a snapshot: ' + ', '.join(sorted(missing)))
    report = {
        'version': version, 'files': len(names), 'expanded_bytes': expanded,
        'selection': 'tracked and untracked public files' if include_untracked else 'Git-tracked public files',
        'untracked_files': extra, 'source': 'working tree; not published',
    }
    if check:
        return {**report, 'integrity': 'selection verified; archive not written'}
    output.mkdir(parents=True, exist_ok=True)
    target = output / f'Gravewright-{version}-django.zip'
    descriptor, name = tempfile.mkstemp(prefix='.release-', suffix='.zip', dir=output)
    os.close(descriptor)
    temporary = Path(name)
    try:
        stamp = archive_timestamp()
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name in names:
                info = zipfile.ZipInfo(name, stamp)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                # Finder and Linux launchers must remain runnable after ZIP extraction.
                mode = 0o100755 if PurePosixPath(name).suffix in ('.sh', '.command') else 0o100644
                info.external_attr = mode << 16
                archive.writestr(info, checked_file(root, name).read_bytes(), compresslevel=9)
        if temporary.stat().st_size > MAX_ARCHIVE_BYTES:
            raise ValueError('Release exceeds the updater compressed-size limit')
        with zipfile.ZipFile(temporary) as archive:
            if archive.namelist() != names or archive.testzip() is not None:
                raise ValueError('Release ZIP failed its integrity check')
            packaged = tomllib.loads(archive.read('pyproject.toml').decode('utf-8'))
            if normalize_version(packaged['project']['version']) != version:
                raise ValueError('Project version changed during the build')
        with temporary.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        temporary.replace(target)
        atomic_text(target.with_suffix('.zip.sha256'), f'{digest}  {target.name}\n')
        return {**report, 'archive': str(target), 'bytes': target.stat().st_size,
                'sha256': digest, 'integrity': 'verified'}
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-untracked', action='store_true',
                        help='include nonignored public new files for a precommit snapshot')
    parser.add_argument('--output-dir', type=Path, help='artifact directory (default: dist)')
    parser.add_argument('--check', action='store_true', help='validate selection and metadata without writing an archive')
    args = parser.parse_args()
    try:
        result = build(output_dir=args.output_dir, include_untracked=args.include_untracked, check=args.check)
    except (KeyError, TypeError, ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Release build failed: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
