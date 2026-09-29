"""Cross-platform source-release supervisor. Application processes never replace themselves."""
import hashlib
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import signal
import sqlite3
import stat
import subprocess
import sys
import time
import tomllib
import uuid
from urllib.request import Request, urlopen, build_opener, ProxyHandler
import zipfile
from scripts.process_control import environment_python, instance_lock, spawn, stop
from scripts.project_files import source_files, copy_files, replace_files, remove_work_tree


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    temporary.write_text(json.dumps(data), encoding='utf-8')
    temporary.replace(path)


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return default


def extract(archive, destination):
    """Only ordinary source files, one project root, bounded expanded size."""
    destination = Path(destination)
    with zipfile.ZipFile(archive) as z:
        roots = [Path(item.filename).parent for item in z.infolist()
                 if Path(item.filename).name == 'pyproject.toml' and len(Path(item.filename).parts) <= 2]
        if len(roots) != 1:
            raise ValueError('Expected one project root')
        prefix = roots[0].parts
        total = 0
        seen = set()
        for item in z.infolist():
            path = Path(item.filename)
            mode = item.external_attr >> 16
            if (path.is_absolute() or '..' in path.parts or '\\' in item.filename
                    or ':' in item.filename or any(p in {'.git', '.venv', '.env'} for p in path.parts)
                    or (path.parts[:len(prefix)] == prefix
                        and path.parts[len(prefix):len(prefix) + 1] == ('data',)
                        and path.name != '.gitkeep' and not item.is_dir())
                    or (stat.S_IFMT(mode) and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)))):
                raise ValueError('Unsafe archive member')
            normalized = str(path).casefold()
            if normalized in seen:
                raise ValueError('Duplicate archive member')
            seen.add(normalized)
            total += item.file_size
            if total > 2 * 1024**3 or len(seen) > 100000:
                raise ValueError('Expanded release exceeds limit')
        z.extractall(destination)
    projects = list(destination.glob('pyproject.toml')) + list(destination.glob('*/pyproject.toml'))
    if len(projects) != 1:
        raise ValueError('Expected one project root')
    project = projects[0].parent
    for name in ('manage.py', 'uv.lock', 'config/managed_asgi.py', 'scripts/managed_server.py'):
        if not (project / name).is_file():
            raise ValueError('Release does not support managed updates')
    return project


def download(artifact, target, notify):
    received = 0
    digest = hashlib.sha256()
    with urlopen(Request(artifact['url'], headers={'User-Agent': 'Gravewright'}), timeout=30) as response, open(target, 'wb') as out:
        if not response.url.startswith('https://'):
            raise ValueError('HTTPS required')
        while chunk := response.read(256 * 1024):
            received += len(chunk)
            if received > artifact['size']:
                raise ValueError('Release exceeds declared size')
            out.write(chunk)
            digest.update(chunk)
            notify('download', received=received, total=artifact['size'])
    if received != artifact['size'] or digest.hexdigest() != artifact['sha256']:
        raise ValueError('Release checksum mismatch')


class Supervisor:
    def __init__(self, origin, state, database, media, host, port, on_ready=None):
        self.origin, self.state = Path(origin).resolve(), Path(state).resolve()
        self.database, self.media = Path(database).resolve(), Path(media).resolve()
        self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
        runner_data = os.environ.get('GRAVEWRIGHT_RUNNER_DATA')
        content = Path(runner_data) / 'compendiums' if runner_data else Path(os.environ.get('GRAVEWRIGHT_CONTENT_ROOT', self.origin / 'data/vtt/compendiums'))
        self.extra_paths = {} if content.resolve().is_relative_to(self.media) else {'compendiums': content.resolve()}
        if runner_data:
            self.extra_paths['staticfiles'] = Path(runner_data).resolve() / 'staticfiles'
        modules = Path(os.environ.get('GRAVEWRIGHT_MODULES_ROOT', self.media / 'modules'))
        modules = (modules if modules.is_absolute() else self.origin / modules).resolve()
        if not modules.is_relative_to(self.media):
            self.extra_paths['modules'] = modules
        for path in [self.media, *self.extra_paths.values()]:
            if self.state.is_relative_to(path) or path == self.origin or self.origin.is_relative_to(path):
                raise ValueError('Persistent storage must not contain the application or updater')
        self.host, self.port = host, port
        self.child = None
        self.on_ready = on_ready
        self.profile = os.environ.get('DJANGO_SETTINGS_MODULE', 'config.settings')
        self.token = uuid.uuid4().hex
        self.env = {**os.environ, 'PYTHONUTF8': '1', 'GRAVEWRIGHT_MANAGED_STATE': str(self.state),
                    'GRAVEWRIGHT_MANAGED_TOKEN': self.token,
                    'GRAVEWRIGHT_DATABASE': str(self.database), 'GRAVEWRIGHT_MEDIA_ROOT': str(self.media),
                    'GRAVEWRIGHT_HOST': host, 'GRAVEWRIGHT_PORT': str(port),
                    'GRAVEWRIGHT_CONTENT_ROOT': str(content.resolve())}
        self.active = self.resolve_active(read(self.state / 'active.json', {'path': str(self.origin)})['path'])
        self.runtime_python = read(self.state / 'active.json', {}).get('python', sys.executable)
        self.protected = [self.state, self.database, self.media, *self.extra_paths.values()]
        self.protected += [Path(str(self.database) + suffix) for suffix in ('-wal', '-shm', '-journal')]
        if runner_data:
            self.protected.append(Path(runner_data).resolve())
        for key, default in (('GRAVEWRIGHT_MODULES_ROOT', 'data/media/modules'),
                             ('GRAVEWRIGHT_API_MODULES_ROOT', 'extensions/api'),
                             ('GRAVEWRIGHT_DJANGO_MODULES_ROOT', 'extensions/django')):
            value = os.environ.get(key, default)
            if value:
                path = Path(value)
                self.protected.append((path if path.is_absolute() else self.origin / path).resolve())

    def resolve_active(self, path):
        path = Path(path).resolve()
        if path != self.origin and not path.is_relative_to(self.state / 'releases'):
            raise ValueError('Invalid active release path')
        return path

    def notify(self, stage, **values):
        write(self.state / 'progress.json', {'stage': stage, 'at': time.time(), **values})

    def python(self, project):
        return str(environment_python(project)) if project != self.origin else self.runtime_python

    def environment(self, project):
        return {**self.env, 'PYTHONPATH': str(project), 'DJANGO_SETTINGS_MODULE': self.profile,
                'UV_PROJECT_ENVIRONMENT': str(project / '.venv')}

    def command(self, project, *args, timeout=600):
        with open(self.state / 'update.log', 'ab') as log:
            process = spawn(args, cwd=project, env=self.environment(project), stdout=log, stderr=log)
            try:
                code = process.wait(timeout=timeout)
                if code:
                    raise subprocess.CalledProcessError(code, args)
            finally:
                stop(process)

    def start(self, project):
        self.child = spawn([self.python(project), str(project / 'scripts/managed_server.py')],
                           cwd=project, env=self.environment(project))

    def stop(self):
        stop(self.child)
        self.child = None

    def ready(self, timeout=60):
        host = '127.0.0.1' if self.host in {'0.0.0.0', '::'} else self.host
        if ':' in host:
            host = '[' + host + ']'
        opener = build_opener(ProxyHandler({}))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.child.poll() is not None:
                raise RuntimeError('Server exited during startup')
            try:
                request = Request(f'http://{host}:{self.port}/__gravewright_update_health', headers={'X-Gravewright-Update': self.token})
                with opener.open(request, timeout=1) as response:
                    if json.load(response).get('token') == self.token:
                        return
            except (OSError, ValueError):
                pass
            time.sleep(.2)
        raise RuntimeError('New server failed readiness check')

    def backup(self, folder):
        folder.mkdir(parents=True)
        with closing(sqlite3.connect(self.database)) as source, closing(sqlite3.connect(folder / 'database.sqlite3')) as target:
            source.backup(target)
        if self.media.exists():
            shutil.copytree(self.media, folder / 'media')
        extras = {}
        for name, path in self.extra_paths.items():
            extras[name] = path.exists()
            if path.exists():
                shutil.copytree(path, folder / name)
        write(folder / 'complete.json', {'media_existed': self.media.exists(), 'extras': extras})

    def restore(self, folder):
        complete = read(folder / 'complete.json')
        if complete is None:
            raise RuntimeError('Incomplete backup; automatic restoration refused')
        for suffix in ('-wal', '-shm'):
            Path(str(self.database) + suffix).unlink(missing_ok=True)
        shutil.copy2(folder / 'database.sqlite3', self.database)
        if self.media.exists():
            shutil.rmtree(self.media)
        if complete['media_existed']:
            shutil.copytree(folder / 'media', self.media)
        for name, existed in complete.get('extras', {}).items():
            path = self.extra_paths[name]
            if path.exists():
                shutil.rmtree(path)
            if existed:
                shutil.copytree(folder / name, path)

    def recover(self):
        journal = read(self.state / 'transaction.json')
        if journal:
            self.notify('rollback')
            self.active = self.resolve_active(journal['previous'])
            folder = self.state / 'backups' / journal['backup']
            if journal['restore']:
                self.restore(folder)
            if journal.get('project_files') is not None:
                replace_files(folder / 'project', self.origin, journal['project_files'], journal['incoming_files'])
                self.runtime_python = journal['previous_python']
            if journal.get('old_copy'):
                old = Path(journal['old_copy']).resolve()
                if old.parent != self.origin.parent or old == self.origin or not old.name.endswith('.old'):
                    raise ValueError('Invalid retained backup path')
                remove_work_tree(old, self.origin.parent)
            write(self.state / 'active.json', {'path': str(self.active), 'python': self.runtime_python})
            (self.state / 'transaction.json').unlink()
            (self.state / 'job.json').unlink(missing_ok=True)
            shutil.rmtree(self.state / 'job.lock', ignore_errors=True)
            self.notify('rolled_back')

    def apply(self, job):
        previous = self.active
        previous_python = self.python(previous)
        ident = uuid.uuid4().hex
        staging = self.state / 'releases' / ident
        backup = self.state / 'backups' / ident
        staging.mkdir(parents=True)
        transaction_started = False
        old_copy = None
        created_old = False
        try:
            self.notify('download', received=0, total=job['artifact']['size'])
            download(job['artifact'], staging / 'release.zip', self.notify)
            self.notify('verify')
            candidate = extract(staging / 'release.zip', staging / 'source')
            from gravewright.administration.release_metadata import normalize_version
            version = tomllib.loads((candidate / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
            if normalize_version(version) != job['version']:
                raise ValueError('Release version mismatch')
            incoming = source_files(candidate)
            existing = source_files(self.origin, self.protected)
            # A release may not replace a locally configured storage directory.
            allowed = set(source_files(candidate, [candidate / p.relative_to(self.origin)
                          for p in self.protected if p.is_relative_to(self.origin)]))
            incoming = sorted(allowed)
            if self.profile == 'config.runner':
                for name in ('Install Windows.bat', 'scripts/windows/create_runner.py',
                             'scripts/windows/runner.bat', 'scripts/windows/launch_runner.py'):
                    if name not in incoming:
                        raise ValueError('Release is missing the Windows installer or runner generator')
                # Generated launchers and shortcuts are local outputs, not release inputs.
                if 'Gravewright Runner.bat' not in incoming:
                    incoming.append('Gravewright Runner.bat')
            self.notify('dependencies')
            uv = os.environ.get('GW_UV') or shutil.which('uv')
            if not uv:
                raise RuntimeError('uv is required')
            self.env['GW_UV'] = uv
            self.command(candidate, uv, 'sync', '--locked', '--no-dev', '--project', str(candidate), '--python', previous_python)
            if self.profile == 'config.runner':
                self.command(candidate, self.python(candidate), 'scripts/windows/create_runner.py',
                             '--data-dir', self.env['GRAVEWRIGHT_RUNNER_DATA'], '--runtime-project', str(self.origin))
            self.command(candidate, self.python(candidate), 'manage.py', 'check')
            (self.state / 'maintenance').touch()
            self.stop()
            self.notify('backup')
            self.backup(backup)
            copy_files(self.origin, backup / 'project', existing)
            journal = {'previous': str(previous), 'previous_python': previous_python,
                       'backup': ident, 'restore': True, 'project_files': existing, 'incoming_files': incoming}
            write(backup / 'project.json', journal)
            write(self.state / 'transaction.json', journal)
            transaction_started = True
            self.notify('migrate')
            self.command(candidate, self.python(candidate), 'manage.py', 'migrate', '--noinput')
            self.command(candidate, self.python(candidate), 'manage.py', 'collectstatic', '--noinput')
            self.notify('replace')
            replace_files(candidate, self.origin, incoming, existing)
            self.runtime_python = self.python(candidate)
            self.notify('restart')
            self.start(self.origin)
            self.ready()
            if job.get('keep_old', True):
                old_copy = self.origin.with_name(self.origin.name + '.old')
                if old_copy.exists():
                    old_copy = self.origin.with_name(self.origin.name + '.' + ident + '.old')
                # Do not replace an earlier user-selected rollback copy.
                old_copy.mkdir(mode=0o700)
                created_old = True
                journal['old_copy'] = str(old_copy)
                write(self.state / 'transaction.json', journal)
                copy_files(backup / 'project', old_copy, existing)
                shutil.copytree(backup, old_copy / '.gravewright-rollback',
                                ignore=shutil.ignore_patterns('project'))
                write(old_copy / '.gravewright-rollback' / 'installation.json', {
                    'origin': str(self.origin), 'state': str(self.state), 'database': str(self.database),
                    'media': str(self.media), 'extra_paths': {k: str(v) for k, v in self.extra_paths.items()},
                    'protected': [str(path) for path in self.protected],
                })
            write(self.state / 'active.json', {'path': str(self.origin), 'python': self.runtime_python})
            self.active = self.origin
            (self.state / 'job.json').unlink(missing_ok=True)
            (self.state / 'transaction.json').unlink()
            transaction_started = False
            self.notify('complete', version=job['version'], backup=str(old_copy) if old_copy else None)
            try:
                remove_work_tree(backup, self.state / 'backups')
            except OSError:
                # A retained temporary copy must not undo a committed update.
                pass
        except Exception as error:
            if (self.state / 'maintenance').exists():
                self.stop()
                if transaction_started:
                    self.recover()
                self.active = previous
                self.start(previous)
                self.ready()
            if created_old:
                remove_work_tree(old_copy, self.origin.parent)
            self.notify('rolled_back' if transaction_started else 'failed', error=type(error).__name__)
            with open(self.state / 'update.log', 'a') as log:
                log.write(f'Update failed: {type(error).__name__}: {error}\n')
        finally:
            # Keep maintenance if recovery itself failed; the journal is retried at next start.
            if not (self.state / 'transaction.json').exists():
                (self.state / 'maintenance').unlink(missing_ok=True)
                (self.state / 'job.json').unlink(missing_ok=True)
                shutil.rmtree(self.state / 'job.lock', ignore_errors=True)

    def run(self):
        with instance_lock(self.state / 'supervisor.lock'):
            self.recover()
            (self.state / 'maintenance').touch()
            try:
                self.start(self.active)
                self.ready()
                (self.state / 'maintenance').unlink(missing_ok=True)
                if self.on_ready:
                    self.on_ready()
                while self.child.poll() is None:
                    job = read(self.state / 'job.json')
                    if job:
                        self.apply(job)
                    time.sleep(.5)
            finally:
                self.stop()
