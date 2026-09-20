"""Prepare private user data and supervise the local Gravewright server and updates.

Windows users enter through Gravewright Runner.bat, which installs the locked
dependencies. This helper is also portable for automated checks with --data-dir.
It never loads or edits the source checkout's .env or development database.
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
    'https://raw.githubusercontent.com/Gravewright/marketplace/main/trusted-keys.json'
)
DEFAULT_MARKETPLACE_KEYS_SHA256 = '0cb7f0d636f36ff73e1f49a6f0af5f7b7bba34b2e77a0d0f0ad92b0b53517ec3'
DEFAULT_MARKETPLACE_CHOICE = '.default-marketplace-choice'


class RunnerError(Exception):
    """An actionable startup failure safe to display in the launcher console."""


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
        raise RunnerError(f'Could not read the Runner configuration at {path}.') from error
    remaining = dict(values)
    output = []
    for line in original.splitlines():
        name = line.split('=', 1)[0].strip() if '=' in line and not line.lstrip().startswith('#') else ''
        if name in remaining:
            output.append(f'{name}={json.dumps(remaining.pop(name), ensure_ascii=False)}')
        else:
            output.append(line)
    if remaining:
        if output and output[-1]:
            output.append('')
        output.append('# Official Gravewright Marketplace installed by Gravewright Runner.')
        output.extend(f'{name}={json.dumps(value, ensure_ascii=False)}'
                      for name, value in remaining.items())
    _write_private(path, ('\n'.join(output) + '\n').encode('utf-8'))


def install_default_marketplace(directory, download=None):
    """Install the pinned official key file and persist the catalog settings."""
    raw = (download or _download_default_keys)()
    key_path = directory / 'marketplace' / 'trusted-keys.json'
    _write_private(key_path, raw)
    values = {
        'GRAVEWRIGHT_MARKETPLACE_URL': DEFAULT_MARKETPLACE_URL,
        'GRAVEWRIGHT_MARKETPLACE_KEYS_FILE': key_path.as_posix(),
    }
    _update_dotenv(directory / '.env', values)
    os.environ.update(values)
    _write_private(directory / DEFAULT_MARKETPLACE_CHOICE, b'installed\n')
    return {**values, 'keyPath': str(key_path)}


def offer_default_marketplace(directory, prompt=input, download=None):
    """Offer the official signed catalog once and persist the owner's choice."""
    catalog = os.environ.get('GRAVEWRIGHT_MARKETPLACE_URL', '').strip()
    keyfile = os.environ.get('GRAVEWRIGHT_MARKETPLACE_KEYS_FILE', '').strip()
    marker = directory / DEFAULT_MARKETPLACE_CHOICE
    if catalog or keyfile or marker.exists():
        return False
    try:
        answer = prompt(
            'Install the default Gravewright Marketplace? '
            '(Instalar o Marketplace padrão?) [y/N]: '
        ).strip().casefold()
    except (EOFError, KeyboardInterrupt):
        print('', flush=True)
        return False
    if answer not in {'y', 'yes', 's', 'sim'}:
        _write_private(marker, b'declined\n')
        print('Default marketplace installation skipped.', flush=True)
        return False
    result = install_default_marketplace(directory, download=download)
    print(f'Default marketplace installed. Public keys: {result["keyPath"]}', flush=True)
    return True


def data_directory(value=None):
    """Use a persistent Windows user directory, never the installed source tree."""
    if value:
        directory = Path(value).expanduser().resolve()
    elif os.environ.get('LOCALAPPDATA'):
        directory = (Path(os.environ['LOCALAPPDATA']) / 'Gravewright' / 'data').resolve()
    elif sys.platform == 'darwin':
        directory = Path.home() / 'Library/Application Support/Gravewright/data'
    else:
        directory = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'Gravewright/data'
    if directory == ROOT:
        raise RunnerError('The data directory must be separate from the project root.')
    return directory


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
    """Merge sample feature defaults with user settings, then enforce local bounds.

    Environment values from another Django checkout cannot select a different
    database, Redis server or public origin. User settings are read literally;
    ${...} does not interpolate secrets, and existing configuration is preserved.
    """
    from dotenv import dotenv_values

    config = directory / '.env'
    if not config.exists():
        content = (
            '# Gravewright Runner: local user configuration. Keep this file private.\n'
            '# Stop the Runner before editing. Feature settings from .env.example\n'
            '# may be added here. Network/security/storage are managed by the Runner.\n'
            f'DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}\n'
            'GRAVEWRIGHT_PORT=3000\n'
        )
        descriptor = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(content)

    defaults = {key: value for key, value in
                dotenv_values(ROOT / '.env.example', interpolate=False).items()
                if value is not None}
    user = dotenv_values(config, interpolate=False)
    allowed = set(defaults) | {'DJANGO_SECRET_KEY', 'DJANGO_SECURE_COOKIES'}
    values = {**defaults, **{key: value for key, value in user.items()
                           if key in allowed and value is not None}}
    secret = user.get('DJANGO_SECRET_KEY', '')
    if not secret or len(secret) < 50 or secret.startswith('django-insecure-'):
        raise RunnerError(f'Set a private DJANGO_SECRET_KEY of at least 50 characters in {config}.')
    try:
        port = int(port_override if port_override is not None else values['GRAVEWRIGHT_PORT'])
        if not 1 <= port <= 65535:
            raise ValueError
    except (TypeError, ValueError):
        raise RunnerError('GRAVEWRIGHT_PORT must be a number from 1 to 65535.') from None
    configured_modules = (user.get('GRAVEWRIGHT_MODULES_ROOT') or '').strip()
    modules_root = Path(configured_modules).expanduser() if configured_modules else directory / 'media/modules'
    if not modules_root.is_absolute():
        modules_root = directory / modules_root
    modules_root = modules_root.resolve()

    # Purge inherited application settings, including undocumented Runner internals.
    for name in tuple(os.environ):
        if name.startswith(('DJANGO_', 'GRAVEWRIGHT_')) or name in allowed:
            del os.environ[name]
    os.environ.update(values)
    os.environ.update(
        DJANGO_SETTINGS_MODULE='config.runner', DJANGO_DEBUG='false',
        DJANGO_SECRET_KEY=secret, DJANGO_ALLOWED_HOSTS='127.0.0.1',
        DJANGO_SECURE_COOKIES='false', DATABASE_ECHO='false',
        GRAVEWRIGHT_HOST='127.0.0.1', GRAVEWRIGHT_PORT=str(port),
        GRAVEWRIGHT_PUBLIC_ORIGIN=f'http://127.0.0.1:{port}',
        GRAVEWRIGHT_REDIS_URL='', TRUSTED_PROXIES='',
        GRAVEWRIGHT_DATABASE=str(directory / 'gravewright.sqlite3'),
        GRAVEWRIGHT_MEDIA_ROOT=str(directory / 'media'),
        GRAVEWRIGHT_MODULES_ROOT=str(modules_root),
        GRAVEWRIGHT_RUNNER_DATA=str(directory),
        GRAVEWRIGHT_RUNNER_TOKEN=secrets.token_urlsafe(32),
        PYTHONUTF8='1',
    )
    # The initial choice is explicit in Windows; source assets are UTF-8 too.
    sys.path.insert(0, str(ROOT))
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
            raise RunnerError(f'Port {port} is unavailable. Close the program using it '
                              'or change GRAVEWRIGHT_PORT in the Runner configuration.') from error


def configure_logging(directory):
    log_dir = directory / 'logs'
    log_dir.mkdir(exist_ok=True)
    handler = RotatingFileHandler(log_dir / 'runner.log', maxBytes=2 * 1024 * 1024,
                                  backupCount=3, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
    return log_dir / 'runner.log'


def prepare_application(directory):
    """Run checks and migrations, and collect only public static assets locally."""
    import django
    from django.core.management import call_command

    for name in ('media', 'compendiums', 'staticfiles'):
        (directory / name).mkdir(exist_ok=True)
    django.setup()
    call_command('check', verbosity=0)
    print('Preparing the database and application files...', flush=True)
    call_command('migrate', interactive=False, verbosity=0)
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
                        print(f'Gravewright is ready: {url}', flush=True)
                        print('Keep this window open. Press Ctrl+C to stop the Runner.', flush=True)
                        if open_browser:
                            try:
                                if not webbrowser.open(url):
                                    print('Open the address above in your browser.', flush=True)
                            except Exception:
                                LOGGER.exception('Could not open the default browser')
                                print('Open the address above in your browser.', flush=True)
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
    parser = argparse.ArgumentParser(description='Gravewright Runner: install data and run locally.')
    parser.add_argument('--data-dir', help='Override the persistent user-data directory.')
    parser.add_argument('--port', type=int, help='Use this port for this run without editing configuration.')
    parser.add_argument('--no-browser', action='store_true', help='Print the address without opening a browser.')
    parser.add_argument('--check', action='store_true', help='Prepare and check the installation, then exit.')
    parser.add_argument('--configure-default-marketplace', action='store_true',
                        help='Offer the official marketplace, save the choice, then exit.')
    args = parser.parse_args(argv)
    log_path = None
    try:
        directory = data_directory(args.data_dir)
        with instance_lock(directory):
            port = prepare_environment(directory, args.port)
            if args.configure_default_marketplace:
                offer_default_marketplace(directory)
                return 0
            if not args.check:
                check_port(port)
            log_path = configure_logging(directory)
            from gravewright.version import release_label
            LOGGER.info('Starting Gravewright Runner - %s', release_label())
            print(f'Gravewright Runner - {release_label()}\nData: {directory}\nLog: {log_path}', flush=True)
            from scripts.update_supervisor import Supervisor
            state = directory / 'updates'
            if not (state / 'active.json').exists() and not (state / 'transaction.json').exists():
                prepare_application(directory)
            def ready():
                url = f'http://127.0.0.1:{port}'
                print(f'Gravewright is ready: {url}', flush=True)
                print('Keep this window open. Press Ctrl+C to stop the Runner.', flush=True)
                if not args.no_browser:
                    webbrowser.open(url)
            supervisor = Supervisor(ROOT, state, directory / 'gravewright.sqlite3', directory / 'media',
                                    '127.0.0.1', port, on_ready=ready)
            if args.check:
                supervisor.recover()
                supervisor.command(supervisor.active, supervisor.python(supervisor.active), 'manage.py', 'check')
                print('Gravewright Runner checks passed.', flush=True)
            else:
                import signal
                def stop_runner(*_):
                    raise KeyboardInterrupt
                signal.signal(signal.SIGTERM, stop_runner)
                if hasattr(signal, 'SIGBREAK'):
                    signal.signal(signal.SIGBREAK, stop_runner)
                supervisor.run()
                print('Gravewright Runner stopped.', flush=True)
        return 0
    except KeyboardInterrupt:
        print('\nGravewright Runner stopped.', flush=True)
        return 0
    except RunnerError as error:
        print(f'Gravewright Runner: {error}', file=sys.stderr, flush=True)
        return 1
    except Exception:
        if log_path:
            LOGGER.exception('Runner startup failed')
            print(f'Gravewright Runner could not start. See {log_path}', file=sys.stderr, flush=True)
        else:
            print('Gravewright Runner could not prepare its configuration. '
                  'Check the data-directory permissions and installed dependencies.', file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
