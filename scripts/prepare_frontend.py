"""Prepare the locked frontend dependencies and assets for Gravewright Runner.

The Windows batch launcher supplies a working Node/npm pair. ``--plan`` reports
which npm commands the launcher needs to run; ``--record`` validates their build
manifest and saves a reusable state. Neither mode installs or builds anything.
The default mode also runs npm, for scripted development and regression tests.
"""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = Path('gravewright/maps/frontend')
CACHE_VERSION = 1


def file_hash(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read_state(path):
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def source_hashes(root, extra=()):
    """Cover source additions/removals as well as edits, excluding npm output."""
    paths = [root / 'gravewright/maps/scripts/build.cjs']
    for name in extra:
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise ValueError('The frontend build reported an invalid input path.')
        paths.append(path)
    for directory in (FRONTEND, Path('gravewright/pdf_system/frontend')):
        for parent, directories, files in os.walk(root / directory):
            directories[:] = [name for name in directories if name not in ('node_modules', '.git')]
            paths.extend(Path(parent) / name for name in files)
    return {path.relative_to(root).as_posix(): file_hash(path) if path.is_file() else None
            for path in sorted(set(paths))}


def output_hashes(root, names):
    """Only accept project files from the build's own output manifest."""
    if not isinstance(names, (list, dict)) or not names:
        raise ValueError('The frontend build did not report any outputs.')
    result = {}
    for name in names:
        path = (root / name).resolve()
        if not path.is_relative_to(root) or 'static' not in path.relative_to(root).parts:
            raise ValueError('The frontend build reported an invalid output path.')
        result[name] = file_hash(path)
    return result


def dependencies_present(frontend, lock):
    """Check installed package versions; platform-specific optional packages vary."""
    for name, package in lock['packages'].items():
        if not name:
            continue
        installed = read_state(frontend / name / 'package.json')
        if not installed and package.get('optional'):
            continue
        if not installed or installed.get('version') != package.get('version'):
            return False
    return True


@contextmanager
def preparation_lock(directory):
    """Prevent two launches from replacing node_modules or assets concurrently."""
    with (directory / 'prepare.lock').open('a+b') as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b'\0')
            handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise RuntimeError('Another Runner is preparing this checkout. Wait for it to finish.') from error
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def record_build(root, state_dir, dependencies):
    """Commit a successful external build only after all reported files exist."""
    built = json.loads((state_dir / 'build-outputs.json').read_text(encoding='utf-8'))
    if not isinstance(built, dict) or not isinstance(built.get('inputs'), list):
        raise ValueError('The frontend build did not report a valid input manifest.')
    if any(not isinstance(name, str) for name in built['inputs']):
        raise ValueError('The frontend build reported an invalid input path.')
    outputs = output_hashes(root, built['outputs'])
    # esbuild also reports imports outside the frontend directories (for
    # example the PDF sheet schema). Those must invalidate future builds.
    sources = source_hashes(root, built['inputs'])
    if any(value is None for value in sources.values()):
        raise ValueError('A frontend input disappeared before the build could be recorded.')
    temporary = state_dir / 'state.json.tmp'
    temporary.write_text(json.dumps({'dependencies': dependencies, 'sources': sources,
                                     'buildInputs': built['inputs'],
                                     'outputs': outputs}, indent=2) + '\n', encoding='utf-8')
    temporary.replace(state_dir / 'state.json')
    print('Frontend assets are ready.', flush=True)


def prepare(root, node, npm_cli, state_dir, *, mode=None):
    """Prepare directly, or return a batch plan: 0 ready, 10 install, 11 build.

    A caller using separate plan/npm/record processes must serialize that whole
    sequence itself. The file lock here protects each individual helper call.
    """
    if mode not in (None, 'plan', 'record'):
        raise ValueError('Unknown frontend preparation mode.')
    root, node, npm_cli = root.resolve(), node.resolve(), npm_cli.resolve()
    frontend = root / FRONTEND
    state_dir.mkdir(parents=True, exist_ok=True)
    # Change only child processes. npm run must find the selected Node, even
    # when another version appears first on the user's PATH.
    environment = os.environ.copy()
    environment['PATH'] = str(node.parent) + os.pathsep + environment.get('PATH', '')
    # Windows environment names are case-insensitive, but this copied Python
    # dict is not. Avoid emitting conflicting uppercase/lowercase npm settings.
    controlled = {'npm_config_update_notifier', 'npm_config_global', 'npm_config_script_shell'}
    environment = {key: value for key, value in environment.items() if key.lower() not in controlled}
    environment['npm_config_update_notifier'] = 'false'
    environment['npm_config_global'] = 'false'
    # npm scripts default to CMD on Windows; inherited custom shells can break
    # that contract. The project build command itself contains no user paths.
    if os.name == 'nt':
        environment['npm_config_script_shell'] = str(Path(os.environ['SystemRoot']) / 'System32/cmd.exe')

    def run(arguments, *, capture=False, check=True):
        return subprocess.run([str(node), *map(str, arguments)], cwd=frontend,
                              env=environment, check=check, capture_output=capture,
                              text=True, encoding='utf-8', errors='replace')

    with preparation_lock(state_dir):
        state_file = state_dir / 'state.json'
        state = read_state(state_file)
        lock = json.loads((frontend / 'package-lock.json').read_text(encoding='utf-8'))
        dependencies = {
            'cacheVersion': CACHE_VERSION,
            'node': run(['--version'], capture=True).stdout.strip(),
            'npm': run([npm_cli, '--version'], capture=True).stdout.strip(),
            'package': file_hash(frontend / 'package.json'),
            'lock': file_hash(frontend / 'package-lock.json'),
        }
        # A valid existing developer install can also be reused on the first
        # Runner launch. Verify esbuild's native executable, not just metadata.
        healthy = dependencies_present(frontend, lock)
        if healthy:
            healthy = run(['-e', "require('esbuild').transformSync('const value = 1'); require.resolve('pixi.js');"],
                          capture=True, check=False).returncode == 0
        if mode == 'record':
            if not healthy:
                raise RuntimeError('Frontend dependencies are incomplete. Run npm ci before recording a build.')
            record_build(root, state_dir, dependencies)
            return 0
        installed = not healthy or bool(state and state.get('dependencies') != dependencies)
        sources = source_hashes(root, state.get('buildInputs', []))
        outputs = state.get('outputs', {})
        try:
            assets_current = output_hashes(root, outputs) == outputs
        except (OSError, ValueError, TypeError):
            assets_current = False
        if not installed and state.get('sources') == sources and assets_current:
            print('Frontend dependencies are already current.', flush=True)
            print('Frontend assets are already current.', flush=True)
            return 0

        manifest = state_dir / 'build-outputs.json'
        if mode == 'plan':
            # A failed/interrupted external build must never reuse an earlier
            # successful manifest when the batch file later calls --record.
            manifest.unlink(missing_ok=True)
            if installed:
                print('Frontend preparation requires npm ci and npm run build.', flush=True)
                return 10
            print('Frontend dependencies are already current; npm run build is required.', flush=True)
            return 11

        if installed:
            print('Installing locked frontend dependencies with npm ci...', flush=True)
            run([npm_cli, 'ci', '--include=dev', '--include=optional', '--no-audit', '--no-fund'])
        else:
            print('Frontend dependencies are already current.', flush=True)

        print('Building frontend assets with npm run build...', flush=True)
        manifest.unlink(missing_ok=True)
        environment['GRAVEWRIGHT_BUILD_MANIFEST'] = str(manifest.resolve())
        run([npm_cli, 'run', 'build'])
        # Only mark a completed build as reusable; interrupted writes or a
        # failed npm command leave the previous state for a retry next launch.
        record_build(root, state_dir, dependencies)
        return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--node', type=Path, required=True)
    parser.add_argument('--npm-cli', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--plan', action='store_true', help='Return 0 when ready, 10 for npm ci/build, or 11 for build only.')
    modes.add_argument('--record', action='store_true', help='Validate and record a successful externally executed build.')
    args = parser.parse_args()
    try:
        return prepare(ROOT, args.node, args.npm_cli, args.state_dir,
                       mode='plan' if args.plan else 'record' if args.record else None)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f'Frontend preparation failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
