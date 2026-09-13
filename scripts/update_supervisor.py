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
        total = 0
        seen = set()
        for item in z.infolist():
            path = Path(item.filename)
            mode = item.external_attr >> 16
            if (path.is_absolute() or '..' in path.parts or '\\' in item.filename
                    or ':' in item.filename or any(p in {'.git', '.venv', '.env'} for p in path.parts)
                    or ('data' in path.parts and path.name != '.gitkeep' and not item.is_dir())
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

    def resolve_active(self, path):
        path = Path(path).resolve()
        if path != self.origin and not path.is_relative_to(self.state / 'releases'):
            raise ValueError('Invalid active release path')
        return path

    def notify(self, stage, **values):
        write(self.state / 'progress.json', {'stage': stage, 'at': time.time(), **values})

    def python(self, project):
        return str(environment_python(project)) if project != self.origin else sys.executable

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
            write(self.state / 'active.json', {'path': str(self.active)})
            (self.state / 'transaction.json').unlink()
            (self.state / 'job.json').unlink(missing_ok=True)
            shutil.rmtree(self.state / 'job.lock', ignore_errors=True)
            self.notify('rolled_back')

    def apply(self, job):
        previous = self.active
        ident = uuid.uuid4().hex
        staging = self.state / 'releases' / ident
        backup = self.state / 'backups' / ident
        staging.mkdir(parents=True)
        transaction_started = False
        try:
            self.notify('download', received=0, total=job['artifact']['size'])
            download(job['artifact'], staging / 'release.zip', self.notify)
            self.notify('verify')
            candidate = extract(staging / 'release.zip', staging / 'source')
            from gravewright.administration.release_metadata import normalize_version
            version = tomllib.loads((candidate / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
            if normalize_version(version) != job['version']:
                raise ValueError('Release version mismatch')
            self.notify('dependencies')
            uv = os.environ.get('GW_UV') or shutil.which('uv')
            if not uv:
                raise RuntimeError('uv is required')
            self.command(candidate, uv, 'sync', '--locked', '--project', str(candidate), '--python', sys.executable)
            self.command(candidate, self.python(candidate), 'manage.py', 'check')
            (self.state / 'maintenance').touch()
            self.stop()
            self.notify('backup')
            self.backup(backup)
            write(self.state / 'transaction.json', {'previous': str(previous), 'backup': ident, 'restore': True})
            transaction_started = True
            self.notify('migrate')
            self.command(candidate, self.python(candidate), 'manage.py', 'migrate', '--noinput')
            self.command(candidate, self.python(candidate), 'manage.py', 'collectstatic', '--noinput')
            self.notify('restart')
            self.start(candidate)
            self.ready()
            write(self.state / 'active.json', {'path': str(candidate)})
            self.active = candidate
            (self.state / 'transaction.json').unlink()
            transaction_started = False
            self.notify('complete', version=job['version'], backup=str(backup))
        except Exception as error:
            if (self.state / 'maintenance').exists():
                self.stop()
                if transaction_started:
                    self.recover()
                self.active = previous
                self.start(previous)
                self.ready()
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
