"""Prepare private user data and supervise the local Gravewright server and updates.

Native installers prepare the app; the generated Gravewright Runner launcher
only starts it. This helper is also portable for checks with --data-dir.
Configuration lives in the source checkout's .env; runtime data stays separate.
"""

import argparse
import base64
from contextlib import contextmanager
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import secrets
import socket
import sys
import threading
import time
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
import webbrowser


ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger('gravewright.runner')
DEFAULT_MARKETPLACE_URL = (
    'https://raw.githubusercontent.com/Gravewright/marketplace/main/'
    'gravewright.marketplace.json'
)
DEFAULT_MARKETPLACE_KEYS_URL = (
    'https://raw.githubusercontent.com/Gravewright/marketplace/'
    '56aefb9db91666f7573bfdcdc2f6e9a6f2100527/trusted-keys.json'
)
# Reviewed official key addition, 2026-10-10: retain the existing key and trust
# the approved GitHub Actions signing key. Pin the immutable revision and bytes
# together so a later edit to main cannot break this installer's integrity check.
# https://github.com/Gravewright/marketplace/commit/56aefb9db91666f7573bfdcdc2f6e9a6f2100527
DEFAULT_MARKETPLACE_KEYS_SHA256 = '8f98a1bc4abf9c394b2818c9a34d28bb73cf39dd0b159a42ccb541b8a0b32815'
# Compare cached trust stores against the same reviewed public keys. A merged
# custom store has different bytes, so its file hash cannot establish this pin.
DEFAULT_MARKETPLACE_PUBLIC_KEYS = {
    'gravewright-2026': 'PXbpURq9J1jLkPnnwBVN/5B+zrb0p5MaWQAe/ltJ8LY=',
    'gravewright-2026-10': 'GEEbh7w29FAsH+XqMhGV+nlCZhroohrJEOwoNy5g48E=',
}
DEFAULT_MARKETPLACE_CHOICE = '.default-marketplace-choice'


class RunnerLanguage:
    """Use the project locale, with reviewed copy available before DB setup."""

    def __init__(self):
        self.locale = 'en'
        self.messages = {}

    def configure(self, locale):
        self.locale = locale or 'en'
        self.messages = {}
        if self.locale == 'pt-BR':
            path = Path(__file__).resolve().parents[1] / 'gravewright/modules/locale_overrides/pt-BR.json'
            self.messages = json.loads(path.read_text(encoding='utf-8'))

    def from_project(self):
        from dotenv import dotenv_values
        defaults = dotenv_values(ROOT / '.env.example', interpolate=False)
        values = dotenv_values(ROOT / '.env', interpolate=False)
        self.configure(values.get('DEFAULT_LOCALE', defaults.get('DEFAULT_LOCALE', 'en')))

    def load_translator(self):
        from gravewright.modules.localization import catalogs
        catalog = catalogs().get(self.locale)
        if catalog:
            self.messages.update(catalog['messages'])

    def text(self, source, **values):
        translated = self.messages.get(source, source)
        try:
            return translated.format(**values) if values else translated
        except (KeyError, ValueError, IndexError):
            return source.format(**values) if values else source


LANGUAGE = RunnerLanguage()


def tr(source, **values):
    return LANGUAGE.text(source, **values)


class RunnerError(Exception):
    """An actionable startup failure safe to display in the launcher console."""

    def __init__(self, source, **values):
        super().__init__(tr(source, **values))


class HTTPSOnlyRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != 'https':
            raise RunnerError('The default marketplace redirected to an insecure address.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _download_default_keys():
    try:
        opener = build_opener(ProxyHandler({}), HTTPSOnlyRedirects())
        with opener.open(Request(DEFAULT_MARKETPLACE_KEYS_URL, headers={
            'User-Agent': 'Gravewright-Runner/1',
        }), timeout=30) as response:
            raw = response.read(1024 * 1024 + 1)
    except RunnerError:
        raise
    except Exception as error:
        raise RunnerError('Could not download the default marketplace public keys.') from error
    if (len(raw) > 1024 * 1024
            or hashlib.sha256(raw).hexdigest() != DEFAULT_MARKETPLACE_KEYS_SHA256):
        raise RunnerError('The default marketplace key file failed its integrity check.')
    try:
        keys = json.loads(raw)
        if (not isinstance(keys, dict) or not keys
                or any(not isinstance(key_id, str) or not key_id
                       or not isinstance(value, str)
                       or len(base64.b64decode(value, validate=True)) != 32
                       for key_id, value in keys.items())):
            raise ValueError
    except (ValueError, TypeError):
        raise RunnerError('The default marketplace public keys are invalid.') from None
    return raw


def _write_private(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + f'.{secrets.token_hex(8)}.tmp')
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _update_dotenv(path, values):
    try:
        original = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        original = ''
    except (OSError, UnicodeError) as error:
        raise RunnerError('Could not read the Runner configuration at {path}.', path=path) from error
    remaining = dict(values)
    output = []
    for line in original.splitlines():
        name = line.split('=', 1)[0].strip() if '=' in line and not line.lstrip().startswith('#') else ''
        if name.startswith('export '):
            name = name[7:].strip()
        if name in values:
            if name in remaining:
                output.append(f'{name}={json.dumps(remaining.pop(name), ensure_ascii=False)}')
        else:
            output.append(line)
    if remaining:
        if output and output[-1]:
            output.append('')
        output.append('# Settings saved by Gravewright Runner.')
        output.extend(f'{name}={json.dumps(value, ensure_ascii=False)}'
                      for name, value in remaining.items())
    _write_private(path, ('\n'.join(output) + '\n').encode('utf-8'))


def configure_environment(directory, *, prompt=input):
    """Collect installer answers before updating the personal environment file."""
    from dotenv import dotenv_values

    user = dotenv_values(ROOT / '.env', interpolate=False)
    values = {**dotenv_values(ROOT / '.env.example', interpolate=False), **user}
    LANGUAGE.configure(values.get('DEFAULT_LOCALE'))
    fields = (
        ('APP_NAME', 'Table name', 'text'),
        ('DEFAULT_LOCALE', 'Language (en, pt-BR)', 'locale'),
        ('GRAVEWRIGHT_PORT', 'Local port (1-65535)', 'port'),
        ('GRAVEWRIGHT_MODULES_ROOT', 'Modules folder', 'text'),
        ('CAMPAIGN_JOIN_CODE_ENABLED', 'Join codes', 'bool'),
        ('CAMPAIGN_SNAPSHOTS_ENABLED', 'Campaign snapshots', 'bool'),
        ('CAMPAIGN_EXPORT_ENABLED', 'Campaign export', 'bool'),
        ('GRAVEWRIGHT_ALLOW_TUNNELS', 'Allow access through tunnels', 'bool'),
    )
    print(tr('Configure: {config}\nEnter = keep current value. Ctrl+C = cancel.', config=ROOT / ".env"), flush=True)
    answers = {}
    try:
        for key, label, kind in fields:
            current = values.get(key) or ''
            if key == 'GRAVEWRIGHT_MODULES_ROOT' and not user.get(key):
                current = values.get(key) or 'data/media/modules'
            hint = tr(' (y/n)') if kind == 'bool' else ''
            while True:
                value = prompt(f'{tr(label)}{hint} [{current}]: ').strip() or current
                if any(ord(char) < 32 for char in value):
                    print(tr('Invalid value.'), flush=True)
                    continue
                if kind == 'port':
                    try:
                        number = int(value)
                    except ValueError:
                        number = 0
                    if not 1 <= number <= 65535:
                        print(tr('Use 1-65535.'), flush=True)
                        continue
                    value = str(number)
                elif kind == 'locale':
                    value = {'en': 'en', 'pt-br': 'pt-BR'}.get(value.casefold())
                    if value is None:
                        print(tr('Use en / pt-BR.'), flush=True)
                        continue
                elif kind == 'bool':
                    value = {'s': 'true', 'sim': 'true', 'y': 'true', 'yes': 'true',
                             'true': 'true', '1': 'true', 'n': 'false', 'nao': 'false',
                             'não': 'false', 'no': 'false', 'false': 'false', '0': 'false'}.get(value.casefold())
                    if value is None:
                        print(tr('Use y/n.'), flush=True)
                        continue
                elif not value:
                    print(tr('Enter a value.'), flush=True)
                    continue
                answers[key] = value
                if kind == 'locale':
                    LANGUAGE.configure(value)
                break
    except (EOFError, KeyboardInterrupt):
        raise RunnerError('Configuration cancelled; answers were not saved. '
                          'Run interactively to configure, or use --check for unattended checks.') from None
    _update_dotenv(ROOT / '.env', answers)
    print(tr('Configuration saved.'), flush=True)
    return True


def marketplace_directory(directory):
    """Keep a project's catalog choice separate from other local installations."""
    identity = os.path.normcase(str(ROOT.resolve()))
    return directory / 'marketplace' / hashlib.sha256(identity.encode('utf-8')).hexdigest()


def official_marketplace_keys(directory, raw, configured=''):
    """Add the pinned keys without overwriting a custom trust-store file."""
    official = json.loads(raw)
    keys = {}
    if configured:
        key_path = Path(configured).expanduser()
        if not key_path.is_absolute():
            key_path = ROOT / key_path
        try:
            keys = json.loads(key_path.read_text(encoding='utf-8'))
            if (not isinstance(keys, dict)
                    or any(not isinstance(name, str) or not name
                           or not isinstance(value, str)
                           or len(base64.b64decode(value, validate=True)) != 32
                           for name, value in keys.items())):
                raise ValueError
        except (OSError, UnicodeError, ValueError, TypeError) as error:
            raise RunnerError('The configured marketplace public keys could not be read or are invalid.') from error
        if any(name in keys and keys[name] != value for name, value in official.items()):
            raise RunnerError('The official marketplace signing key conflicts with the configured trust store.')
        if all(keys.get(name) == value for name, value in official.items()):
            return key_path
    key_path = marketplace_directory(directory) / 'trusted-keys.json'
    _write_private(key_path, json.dumps({**keys, **official}).encode('utf-8') if configured else raw)
    return key_path


def install_default_marketplace(directory, download=None):
    """Install the pinned official key file and persist the catalog settings."""
    raw = (download or _download_default_keys)()
    key_path = official_marketplace_keys(
        directory, raw, os.environ.get('GRAVEWRIGHT_MARKETPLACE_KEYS_FILE', '').strip(),
    )
    values = {
        'GRAVEWRIGHT_MARKETPLACE_URL': DEFAULT_MARKETPLACE_URL,
        'GRAVEWRIGHT_MARKETPLACE_KEYS_FILE': key_path.as_posix(),
    }
    _update_dotenv(ROOT / '.env', values)
    os.environ.update(values)
    _write_private(marketplace_directory(directory) / DEFAULT_MARKETPLACE_CHOICE, b'installed\n')
    return {**values, 'keyPath': str(key_path)}


def _cached_default_keys(path):
    """Return a valid local trust store only when it contains the pinned keys."""
    path = Path(path).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    try:
        raw = path.read_bytes()
        keys = json.loads(raw)
        if (not isinstance(keys, dict)
                or any(not isinstance(name, str) or not name
                       or not isinstance(value, str)
                       or len(base64.b64decode(value, validate=True)) != 32
                       for name, value in keys.items())
                or any(keys.get(name) != value for name, value in DEFAULT_MARKETPLACE_PUBLIC_KEYS.items())):
            return None
    except (OSError, UnicodeError, ValueError, TypeError):
        return None
    return raw


def ensure_default_marketplace(directory, download=None):
    """Configure the official catalog automatically, preserving custom catalogs.

    Previously declined choices do not disable the installer's default. Existing
    official configuration with validated local keys needs no network or writes.
    """
    catalog = os.environ.get('GRAVEWRIGHT_MARKETPLACE_URL', '').strip()
    if catalog and catalog != DEFAULT_MARKETPLACE_URL:
        return False
    configured = os.environ.get('GRAVEWRIGHT_MARKETPLACE_KEYS_FILE', '').strip()
    raw = _cached_default_keys(configured or marketplace_directory(directory) / 'trusted-keys.json')
    if catalog and configured and raw is not None:
        return False
    result = install_default_marketplace(
        directory, download=(lambda: raw) if raw is not None else download,
    )
    print(tr('Default marketplace installed. Public keys: {path}', path=result["keyPath"]), flush=True)
    return True


def data_directory(value=None):
    """Use persistent per-user state, independently of project configuration."""
    if value:
        directory = Path(value).expanduser().resolve()
    elif sys.platform == 'win32':
        directory = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'Gravewright/data'
    elif sys.platform == 'darwin':
        directory = Path.home() / 'Library/Application Support/Gravewright/data'
    else:
        directory = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'Gravewright/data'
    directory = directory.resolve()
    if directory == ROOT:
        raise RunnerError('The data directory must be separate from the project root.')
    return directory


def complete_configuration(config, user, defaults):
    """Fill missing settings from the example without changing saved values."""
    if all(user.get(key) is not None for key in defaults):
        return
    from config.size_limits import migrate_sizes
    user = migrate_sizes(user)
    template = (ROOT / '.env.example').read_text(encoding='utf-8')
    original = config.read_text(encoding='utf-8')
    values = {**defaults, **{key: value for key, value in user.items() if value is not None}}
    output, written = [], set()
    for line in template.splitlines():
        assignment = line.strip()
        if assignment.startswith('# DJANGO_SECRET_KEY='):
            assignment = assignment[2:]
        name = assignment.split('=', 1)[0].strip() if '=' in assignment else ''
        if not assignment.startswith('#') and name in values:
            output.append(f'{name}={json.dumps(values[name], ensure_ascii=False)}')
            written.add(name)
        else:
            output.append(line)
    extra = {key: value for key, value in values.items() if key not in written}
    comments = [line for line in original.splitlines()
                if line.lstrip().startswith('#') and line not in template.splitlines()]
    if extra or comments:
        output.extend(['', *comments])
        output.extend(f'{key}={json.dumps(value, ensure_ascii=False)}' for key, value in extra.items())
    _write_private(config, ('\n'.join(output) + '\n').encode('utf-8'))


@contextmanager
def instance_lock(directory):
    """Hold an OS lock through migrations and server lifetime; crashes release it.

    Keep the lock file after exit: unlinking a locked file can let a second
    process lock a different inode and enter the same database concurrently.
    """
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / 'runner.lock').open('a+b') as handle:
        handle.seek(0, os.SEEK_END)
        if not handle.tell():
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
            raise RunnerError('Gravewright Runner is already using this data directory. '
                              'Close the other Runner before starting again.') from error
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def prepare_environment(directory, port_override=None):
    """Load project configuration and resolve storage relative to the project.

    Inherited application settings are replaced by the project configuration;
    the desktop profile still enforces local network bounds. Values are literal;
    ${...} does not interpolate secrets, and existing configuration is preserved.
    """
    sys.path.insert(0, str(ROOT))
    from dotenv import dotenv_values
    from config.size_limits import SIZE_DEFAULTS, migrate_sizes

    config = ROOT / '.env'
    if not config.exists():
        content = f'DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}\n'
        descriptor = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content.encode('utf-8'))

    defaults = {key: value for key, value in
                dotenv_values(ROOT / '.env.example', interpolate=False).items()
                if value is not None}
    user = dotenv_values(config, interpolate=False)
    allowed = set(defaults) | set(SIZE_DEFAULTS) | {'DJANGO_SECRET_KEY', 'DJANGO_SECURE_COOKIES'}
    values = {**defaults, **{key: value for key, value in migrate_sizes(user).items()
                           if key in allowed and value is not None}}
    LANGUAGE.configure(values.get('DEFAULT_LOCALE'))
    secret = user.get('DJANGO_SECRET_KEY', '')
    if not secret or len(secret) < 50 or secret.startswith('django-insecure-'):
        raise RunnerError('Set a private DJANGO_SECRET_KEY of at least 50 characters in {config}.', config=config)
    try:
        port = int(port_override if port_override is not None else values['GRAVEWRIGHT_PORT'])
        if not 1 <= port <= 65535:
            raise ValueError
    except (TypeError, ValueError):
        raise RunnerError('GRAVEWRIGHT_PORT must be a number from 1 to 65535.') from None
    complete_configuration(config, user, defaults)
    def storage(name, fallback):
        path = Path(values.get(name) or fallback).expanduser()
        return str((path if path.is_absolute() else ROOT / path).resolve())

    database = storage('GRAVEWRIGHT_DATABASE', 'data/gravewright.sqlite3')
    media = storage('GRAVEWRIGHT_MEDIA_ROOT', 'data/media')
    modules = storage('GRAVEWRIGHT_MODULES_ROOT', str(Path(media) / 'modules'))
    tunnels = values.get('GRAVEWRIGHT_ALLOW_TUNNELS', 'false').strip().lower()
    if tunnels not in {'true', 'false'}:
        raise RunnerError('GRAVEWRIGHT_ALLOW_TUNNELS must be true or false.')
    origin = '' if tunnels == 'true' else f'http://127.0.0.1:{port}'

    # Generated POSIX launchers retain the installer's private native toolchain
    # for source-only dependencies during future supervised environment builds.
    build_tools = os.environ.get('GRAVEWRIGHT_BUILD_TOOLS_PATH') if os.name != 'nt' else None
    # Purge inherited application settings, including undocumented Runner internals.
    for name in tuple(os.environ):
        if name.startswith(('DJANGO_', 'GRAVEWRIGHT_')) or name in allowed:
            del os.environ[name]
    os.environ.update(values)
    if build_tools:
        os.environ['GRAVEWRIGHT_BUILD_TOOLS_PATH'] = build_tools
    os.environ.update(
        DJANGO_SETTINGS_MODULE='config.runner', DJANGO_DEBUG='false',
        DJANGO_SECRET_KEY=secret, DJANGO_ALLOWED_HOSTS='*' if tunnels == 'true' else '127.0.0.1',
        DJANGO_SECURE_COOKIES=values.get('DJANGO_SECURE_COOKIES', 'false') if tunnels == 'true' else 'false', DATABASE_ECHO='false',
        GRAVEWRIGHT_HOST='127.0.0.1', GRAVEWRIGHT_PORT=str(port),
        GRAVEWRIGHT_PUBLIC_ORIGIN=origin,
        GRAVEWRIGHT_ALLOW_TUNNELS=tunnels,
        GRAVEWRIGHT_REDIS_URL='', TRUSTED_PROXIES='127.0.0.1/32,::1/128' if tunnels == 'true' else '',
        GRAVEWRIGHT_DATABASE=database,
        GRAVEWRIGHT_MEDIA_ROOT=media,
        GRAVEWRIGHT_MODULES_ROOT=modules,
        GRAVEWRIGHT_RUNNER_DATA=str(directory),
        GRAVEWRIGHT_RUNNER_TOKEN=secrets.token_urlsafe(32),
        PYTHONUTF8='1',
    )
    # The initial choice is explicit in Windows; source assets are UTF-8 too.
    return port


def check_port(port):
    """Fail before changing the database if the requested endpoint is occupied."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            # Match Daphne on POSIX: a stopped listener's TIME_WAIT connections
            # must not prevent restarting; an active listener still owns its port.
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(('127.0.0.1', port))
        except OSError as error:
            raise RunnerError('Port {port} is unavailable. Close the program using it or change GRAVEWRIGHT_PORT in the Runner configuration.', port=port) from error


def configure_logging(directory):
    log_dir = directory / 'logs'
    log_dir.mkdir(exist_ok=True)
    handler = RotatingFileHandler(log_dir / 'runner.log', maxBytes=2 * 1024 * 1024,
                                  backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
    return log_dir / 'runner.log'


def ensure_portuguese_translation(directory):
    """Install and globally activate the official signed Portuguese catalogs."""
    from django.conf import settings
    if settings.DEFAULT_LOCALE != 'pt-BR':
        return
    from django.db import transaction
    from gravewright.modules.models import Package
    from gravewright.modules.packages import ModulePackages, ModuleFailure, MAX_ARCHIVE, compatible, host
    from gravewright.modules.views import download
    from gravewright.administration.release_metadata import version_key

    try:
        engine = host()
        row = Package.objects.filter(module_id='gravewright.translator', revoked=False).order_by('-pk').first()
        if row and 'pt-BR' in row.locale_catalogs and compatible(row.manifest['sdk']['requires']):
            engine.verify_installed(row)
        else:
            print(tr('Installing the official Translator for pt-BR...'), flush=True)
            raw_keys = _download_default_keys()
            official = json.loads(raw_keys)
            key_path = official_marketplace_keys(directory, raw_keys, settings.GRAVEWRIGHT_MARKETPLACE_KEYS_FILE)
            engine = ModulePackages(engine.directory, official)
            records = json.loads(download(DEFAULT_MARKETPLACE_URL, 2 * 1024 * 1024))
            if not isinstance(records, list) or len(records) > 5000:
                raise ValueError('Invalid official catalog')
            candidates = []
            for record in records:
                if not isinstance(record, dict):
                    raise ValueError('Invalid official catalog record')
                if record.get('id') == 'gravewright.translator':
                    engine.verify(record, require_compatible=False)
                    if record.get('status') != 'revoked' and compatible(record['sdk']):
                        candidates.append(record)
            if not candidates:
                raise RunnerError('The official catalog has no compatible Translator release.')
            record = max(candidates, key=lambda item: version_key(item['version']))
            manifest = engine.install(record, download(record['download'], MAX_ARCHIVE))
            row = Package.objects.get(module_id=manifest['id'], version=manifest['version'])
            if 'pt-BR' not in row.locale_catalogs:
                raise RunnerError('The official Translator does not contain pt-BR catalogs.')
            marketplace = {'GRAVEWRIGHT_MARKETPLACE_KEYS_FILE': key_path.as_posix()}
            _update_dotenv(ROOT / '.env', marketplace)
            os.environ.update(marketplace)
            for key, value in marketplace.items():
                setattr(settings, key, value)
        with transaction.atomic():
            Package.objects.filter(global_enabled=True).exclude(locale_catalogs={}).exclude(pk=row.pk).update(global_enabled=False)
            row.global_enabled = True
            row.save(update_fields=['global_enabled'])
        LANGUAGE.load_translator()
        print(tr('Translator {version} is installed and active for pt-BR.', version=row.version), flush=True)
    except (ModuleFailure, OSError, ValueError, KeyError, TypeError) as error:
        raise RunnerError('Could not install or verify the required pt-BR Translator. '
                          'Check your connection, signing keys and module files, then retry.') from error


def prepare_application(directory):
    """Run checks and migrations, and collect only public static assets locally."""
    import django
    from django.core.management import call_command

    Path(os.environ['GRAVEWRIGHT_DATABASE']).parent.mkdir(parents=True, exist_ok=True)
    Path(os.environ['GRAVEWRIGHT_MEDIA_ROOT']).mkdir(parents=True, exist_ok=True)
    for name in ('compendiums', 'staticfiles'):
        (directory / name).mkdir(exist_ok=True)
    django.setup()
    call_command('check', verbosity=0)
    print(tr('Preparing the database and application files...'), flush=True)
    call_command('migrate', interactive=False, verbosity=0)
    ensure_portuguese_translation(directory)
    LANGUAGE.load_translator()
    call_command('collectstatic', interactive=False, verbosity=0)


def finish_asyncio(loop):
    """Finish remaining HTTP middleware work before interpreter thread shutdown.

    Daphne stops its reactor after cancelling application tasks. Django's
    sync/async middleware bridges can still own child tasks and worker threads;
    those threads need the event loop alive to finish their cancellation. Use
    the same draining order as asyncio.Runner before releasing the data lock.
    """
    import asyncio

    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
    if pending:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.run_until_complete(loop.shutdown_default_executor())
    loop.close()


def serve(port, open_browser=True):
    """Run Daphne in this process; closing the Runner cannot orphan a server."""
    from daphne.server import Server
    from twisted.internet import reactor
    from config.runner_asgi import application

    url = f'http://127.0.0.1:{port}'
    token = os.environ['GRAVEWRIGHT_RUNNER_TOKEN']
    stopped = threading.Event()
    ready = threading.Event()
    server = Server(application, endpoints=[f'tcp:port={port}:interface=127.0.0.1'],
                    signal_handlers=True, verbosity=1)

    def wait_ready():
        # Bypass system HTTP proxies for this loopback-only readiness request.
        opener = build_opener(ProxyHandler({}))
        deadline = time.monotonic() + 60
        while not stopped.is_set() and time.monotonic() < deadline:
            try:
                with opener.open(url + '/__gravewright_runner__/ready', timeout=1) as response:
                    if response.status == 200 and json.loads(response.read(4096)) == {'runner': token}:
                        ready.set()
                        print(tr('Gravewright is ready: {url}', url=url), flush=True)
                        print(tr('Keep this window open. Press Ctrl+C to stop the Runner.'), flush=True)
                        if open_browser:
                            try:
                                if not webbrowser.open(url):
                                    print(tr('Open the address above in your browser.'), flush=True)
                            except Exception:
                                LOGGER.exception('Could not open the default browser')
                                print(tr('Open the address above in your browser.'), flush=True)
                        return
            except (OSError, ValueError):
                pass
            stopped.wait(0.2)
        if not stopped.is_set():
            LOGGER.error('Server readiness timed out')
            reactor.callFromThread(server.stop)

    watcher = threading.Thread(target=wait_ready, name='runner-readiness', daemon=True)
    watcher.start()
    # Windows automation can send Ctrl+Break to the Runner's process group.
    # Treat it like Ctrl+C so active WebSockets and SQLite connections close.
    import signal
    previous_break = None
    if hasattr(signal, 'SIGBREAK'):
        previous_break = signal.signal(signal.SIGBREAK, lambda *_: reactor.callFromThread(server.stop))
    try:
        server.run()
    finally:
        stopped.set()
        watcher.join(timeout=2)
        if previous_break is not None:
            signal.signal(signal.SIGBREAK, previous_break)
        finish_asyncio(reactor._asyncioEventloop)
    if not ready.is_set():
        raise RunnerError('The server could not start. Check the Runner log for details.')


def main(argv=None):
    LANGUAGE.from_project()
    parser = argparse.ArgumentParser(description=tr('Gravewright Runner: install data and run locally.'),
                                     allow_abbrev=False)
    parser.add_argument('--data-dir', help=tr('Override the persistent user-data directory.'))
    parser.add_argument('--port', type=int, help=tr('Use this port for this run without editing configuration.'))
    parser.add_argument('--no-browser', action='store_true', help=tr('Print the address without opening a browser.'))
    parser.add_argument('--check', action='store_true', help=tr('Prepare and check the installation, then exit.'))
    parser.add_argument('--configure-default-marketplace', action='store_true',
                        help=tr('Ask personal settings and configure the official marketplace automatically, then exit.'))
    args = parser.parse_args(argv)
    log_path = None
    try:
        directory = data_directory(args.data_dir)
        with instance_lock(directory):
            port = prepare_environment(directory, args.port)
            if not args.check and args.configure_default_marketplace:
                configure_environment(directory)
                port = prepare_environment(directory, args.port)
                ensure_default_marketplace(directory)
                prepare_application(directory)
                from gravewright.administration.models import HostSettings
                HostSettings.objects.update_or_create(pk=1, defaults={'default_locale': os.environ['DEFAULT_LOCALE']})
                return 0
            if not args.check:
                check_port(port)
            log_path = configure_logging(directory)
            from gravewright.version import release_label
            LOGGER.info('Starting Gravewright Runner - %s', release_label())
            print(tr('Gravewright Runner - {version}\nConfig: {config}\n'
                     'Database: {database}\nMedia: {media}\n'
                     'Runner state: {directory}\nLog: {log}',
                     version=release_label(), config=ROOT / '.env',
                     database=os.environ['GRAVEWRIGHT_DATABASE'],
                     media=os.environ['GRAVEWRIGHT_MEDIA_ROOT'],
                     directory=directory, log=log_path), flush=True)
            from scripts.update_supervisor import Supervisor
            state = directory / 'updates'
            if not (state / 'transaction.json').exists():
                prepare_application(directory)
            def ready():
                url = f'http://127.0.0.1:{port}'
                print(tr('Gravewright is ready: {url}', url=url), flush=True)
                print(tr('Keep this window open. Press Ctrl+C to stop the Runner.'), flush=True)
                if not args.no_browser:
                    webbrowser.open(url)
            supervisor = Supervisor(ROOT, state, os.environ['GRAVEWRIGHT_DATABASE'], os.environ['GRAVEWRIGHT_MEDIA_ROOT'],
                                    '127.0.0.1', port, on_ready=ready)
            if args.check:
                supervisor.recover()
                supervisor.command(supervisor.active, supervisor.python(supervisor.active), 'manage.py', 'check')
                print(tr('Gravewright Runner checks passed.'), flush=True)
            else:
                import signal
                def stop_runner(*_):
                    raise KeyboardInterrupt
                signal.signal(signal.SIGTERM, stop_runner)
                if hasattr(signal, 'SIGHUP'):
                    # Closing the terminal must also drain the separately
                    # supervised server, rather than leave it running orphaned.
                    signal.signal(signal.SIGHUP, stop_runner)
                if hasattr(signal, 'SIGBREAK'):
                    signal.signal(signal.SIGBREAK, stop_runner)
                supervisor.run()
                print(tr('Gravewright Runner stopped.'), flush=True)
        return 0
    except KeyboardInterrupt:
        print(tr('\nGravewright Runner stopped.'), flush=True)
        return 0
    except RunnerError as error:
        print(tr('Gravewright Runner: {error}', error=error), file=sys.stderr, flush=True)
        return 1
    except Exception:
        if log_path:
            LOGGER.exception('Runner startup failed')
            print(tr('Gravewright Runner could not start. See {log}', log=log_path), file=sys.stderr, flush=True)
        else:
            print(tr('Gravewright Runner could not prepare its configuration. Check the data-directory permissions and installed dependencies.'), file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
