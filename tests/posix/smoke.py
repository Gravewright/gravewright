"""Exercise real Linux/macOS installation and the generated local Runner.

All preparation runs in disposable source/tool/state directories. HOME and the
parent environment stay unchanged. --source-check is portable to Windows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'test-results/posix-runner'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def check_sources():
    required = ['Install Linux.sh', 'Install macOS.command', 'scripts/posix/install.sh',
                'scripts/posix/runner.sh', 'scripts/posix/create_runner.py',
                'scripts/posix/mac_tools.sh', 'scripts/posix/mac_build.py']
    shell = shutil.which('bash')
    if os.name == 'nt':
        # Windows may expose an inaccessible WSL app-execution alias.
        git_bash = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Git/bin/bash.exe'
        shell = str(git_bash) if git_bash.is_file() else None
    for name in required:
        path = ROOT / name
        raw = path.read_bytes()
        if name.endswith(('.sh', '.command')):
            assert b'\r' not in raw and b'\0' not in raw, f'{name}: shell scripts require LF, without NUL'
            if shell:
                subprocess.run([shell, '-n', path.as_posix()], check=True, capture_output=True)
    print('POSIX launcher source checks passed.', flush=True)


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def stop(process, *, graceful=False):
    if process.poll() is not None:
        return
    process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=25)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=10)
        if graceful:
            raise AssertionError('Runner did not stop gracefully after SIGTERM')


def run(arguments, *, cwd, env, log, timeout=1500, expected=0):
    with log.open('wb') as stream:
        process = subprocess.Popen(arguments, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                   stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            stop(process)
            raise
    output = log.read_text(encoding='utf-8', errors='replace')
    assert code == expected, f'Exit {code}, expected {expected}; inspect {log}'
    return output


def snapshot(paths):
    return {str(path): (digest(path), path.stat().st_mtime_ns if path.exists() else None)
            for path in paths}


def ignore_source(directory, names):
    excluded = {'.git', '.venv', '.codex', '.agents', '.aws', '.ssh', 'node_modules',
                '__pycache__', '.pytest_cache', 'test-results', 'data', 'media', 'staticfiles',
                'dist', 'build', 'logs', 'backups', 'tmp'}
    private = shutil.ignore_patterns('*.sqlite*', '*.log*', 'Gravewright Runner.*')
    ignored = set(private(directory, names))
    ignored.update(name for name in names if name in excluded or
                   (name.startswith('.env') and name != '.env.example'))
    # Operator-installed systems never belong in a core acceptance fixture.
    if Path(directory) in (ROOT / 'extensions/api', ROOT / 'extensions/django'):
        ignored.update(name for name in names if not (name.startswith('README') and name.endswith('.md')))
    return ignored


def find_tool(runtime, name, fallback_path):
    candidates = [path for path in (runtime / name).rglob(name)
                  if path.is_file() and os.access(path, os.X_OK)]
    if len(candidates) == 1:
        return candidates[0]
    existing = shutil.which(name, path=fallback_path)
    assert existing, f'Prepared {name} was not found under {runtime} or the restricted PATH'
    return Path(existing)


def private_build_tools(runtime, data):
    """Prove Intel macOS builds use the prepared private toolchain, not CI's."""
    if sys.platform != 'darwin' or platform.machine().lower() not in {'x86_64', 'amd64'}:
        return []
    saved = list((data / '.runner-launchers').glob('*.command'))
    assert len(saved) == 1, 'Expected one freshly generated immutable macOS launcher'
    values = {}
    for line in saved[0].read_text(encoding='utf-8').splitlines():
        for name in ('GRAVEWRIGHT_BUILD_TOOLS_PATH', 'OPENSSL_DIR', 'OPENSSL_STATIC',
                     'CARGO_HOME', 'AUTOBAHN_USE_NVX'):
            if line.startswith(name + '='):
                words = shlex.split(line)
                assert len(words) == 1, 'Build environment is not a literal quoted assignment'
                values[name] = words[0].split('=', 1)[1]
    assert values.get('AUTOBAHN_USE_NVX') == '0', 'macOS must disable Autobahn optional native vectors'
    assert values.get('OPENSSL_STATIC') == '1', 'Intel cryptography must link prepared OpenSSL statically'
    bins = [Path(item) for item in values.get('GRAVEWRIGHT_BUILD_TOOLS_PATH', '').split(os.pathsep) if item]
    assert bins and all(path.is_relative_to(runtime) for path in bins), 'Rust tools escaped private runtime'
    cargo_home = Path(values.get('CARGO_HOME', ''))
    openssl = Path(values.get('OPENSSL_DIR', ''))
    assert cargo_home.is_relative_to(runtime) and cargo_home.is_dir(), 'Cargo cache must be private'
    assert openssl.is_relative_to(runtime) and openssl.is_dir(), 'OpenSSL must be prepared privately'
    binaries = []
    for name in ('rustc', 'cargo'):
        matches = [path / name for path in bins if (path / name).is_file()]
        assert len(matches) == 1 and os.access(matches[0], os.X_OK), f'Missing private {name}'
        binaries.extend(matches)
    for name in ('libcrypto.a', 'libssl.a'):
        matches = list(openssl.rglob(name))
        assert len(matches) == 1, f'Missing private static {name}'
        binaries.extend(matches)
    return [*binaries, cargo_home, openssl]


def exercise(work):
    project = work / 'Gravewright São Paulo & (fixture)'
    runtime = project / 'data/runner'
    data = project / 'data'
    shutil.copytree(ROOT, project, ignore=ignore_source, symlinks=True)
    # Deliberately present a developer venv which installation must not replace.
    sentinel = project / '.venv/developer-data.txt'
    sentinel.parent.mkdir()
    sentinel.write_text('preserve developer environment\n', encoding='utf-8')
    lockfiles = [sentinel, project / 'uv.lock', project / 'gravewright/maps/frontend/package-lock.json']
    original_source = snapshot(lockfiles)
    original_environment = dict(os.environ)
    home = Path.home()
    personal = [home / name for name in ('.profile', '.bashrc', '.bash_profile', '.zshrc',
                                         '.npmrc', '.config/uv/uv.toml', '.cargo/config',
                                         '.cargo/config.toml', '.cargo/env', '.rustup/settings.toml')]
    original_personal = snapshot(personal)
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(('DJANGO_', 'GRAVEWRIGHT_', 'UV_', 'PYTHON', 'NPM_CONFIG_', 'npm_config_',
                           'CARGO', 'RUST', 'OPENSSL', 'PKG')) or key in {
            'VIRTUAL_ENV', 'LOCALAPPDATA', 'BASH_ENV', 'ENV', 'NODE_OPTIONS', 'NODE_PATH'}:
            env.pop(key)
    # Child-only overrides; preserve HOME and real user configuration.
    env.update(XDG_DATA_HOME=str(work / 'XDG data'),
               XDG_CACHE_HOME=str(work / 'XDG cache'), XDG_CONFIG_HOME=str(work / 'XDG config'),
               NPM_CONFIG_USERCONFIG=str(work / 'isolated.npmrc'),
               NPM_CONFIG_GLOBALCONFIG=str(work / 'isolated-global.npmrc'),
               PYTHONUTF8='1', NO_COLOR='1')
    env['PATH'] = '/usr/bin:/bin:/usr/sbin:/sbin'
    bash = '/bin/bash'
    installer = 'Install macOS.command' if sys.platform == 'darwin' else 'Install Linux.sh'
    launcher = 'Gravewright Runner.command' if sys.platform == 'darwin' else 'Gravewright Runner.sh'
    port = free_port()
    args = ['--check', '--no-browser', '--no-pause', '--port', str(port)]
    print('Preparing real POSIX installation in isolated Unicode/space paths...', flush=True)
    first = run([bash, str(project / installer), *args], cwd=work, env=env,
                log=OUTPUT / 'first-install.log')
    assert 'Gravewright Runner checks passed.' in first, 'Installation did not finish application checks'
    generated = project / launcher
    assert generated.is_file() and generated.stat().st_mode & stat.S_IXUSR, 'Missing executable generated Runner'
    assert (project / '.env').is_file() and (project / 'data/gravewright.sqlite3').is_file()
    assert not (data / '.env').exists(), 'Configuration must remain in the project root'
    assert runtime.is_dir(), 'Default tools must stay inside the extracted project'
    assert list((data / '.runner-launchers').glob('*.py')), 'Missing immutable recovery launcher'
    uv = find_tool(runtime, 'uv', env['PATH'])
    node = find_tool(runtime, 'node', env['PATH'])
    python_paths = list((runtime / 'environments').glob('*/bin/python'))
    assert len(python_paths) == 1, f'Expected one private virtual environment, found {python_paths}'
    python = python_paths[0]
    configuration = digest(project / '.env')
    installed_lock = project / 'gravewright/maps/frontend/node_modules/.package-lock.json'
    bundle = project / 'gravewright/table/static/gravewright_table/media-workspace.js'
    assert installed_lock.is_file() and bundle.is_file(), 'Frontend was not prepared'
    toolchain = private_build_tools(runtime, data)
    prepared_paths = [uv, node, installed_lock, bundle, *toolchain]
    prepared = snapshot(prepared_paths)
    env['PATH'] = os.pathsep.join((str(uv.parent), str(node.parent), env['PATH']))
    offline = dict(env, UV_OFFLINE='1', npm_config_offline='true',
                   HTTP_PROXY='http://127.0.0.1:9', HTTPS_PROXY='http://127.0.0.1:9',
                   ALL_PROXY='http://127.0.0.1:9', http_proxy='http://127.0.0.1:9',
                   https_proxy='http://127.0.0.1:9', all_proxy='http://127.0.0.1:9', NO_PROXY='', no_proxy='')
    print('Repeating unchanged installation with offline package modes and blocked download proxies...', flush=True)
    repeat = run([bash, str(project / installer), *args], cwd=work, env=offline,
                 log=OUTPUT / 'offline-install.log')
    assert 'Gravewright Runner checks passed.' in repeat
    assert snapshot(prepared_paths) == prepared, 'Offline installation rewrote prepared tools/assets'
    assert digest(project / '.env') == configuration, 'Repeated installation changed saved configuration'
    checked = run([bash, str(generated), '--check', '--no-browser'], cwd=work, env=offline,
                  log=OUTPUT / 'runner-check.log', timeout=120)
    assert 'Gravewright Runner checks passed.' in checked
    assert '[1/7]' not in checked and 'npm ci' not in checked, 'Generated Runner performed installation work'
    run([bash, str(generated), '--port', '70000', '--no-browser'], cwd=work, env=offline,
        log=OUTPUT / 'invalid-port.log', expected=1, timeout=30)

    print('Starting the prepared Runner and waiting for actual HTTP readiness...', flush=True)
    opener = build_opener(ProxyHandler({}))
    with (OUTPUT / 'server.log').open('wb') as stream:
        process = subprocess.Popen([bash, str(generated), '--no-browser', '--port', str(port)],
                                   cwd=work, env=offline, stdin=subprocess.DEVNULL,
                                   stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 90
            ready = False
            while time.monotonic() < deadline:
                assert process.poll() is None, 'Runner exited before readiness; inspect server.log'
                try:
                    with opener.open(f'http://127.0.0.1:{port}/__gravewright_runner__/ready', timeout=2) as response:
                        ready = response.status == 200
                    if ready:
                        break
                except (OSError, URLError):
                    time.sleep(.2)
            assert ready, 'HTTP readiness timed out; inspect server.log'
            with opener.open(f'http://127.0.0.1:{port}/', timeout=5) as response:
                assert response.status == 200 and b'Gravewright' in response.read(), 'Application page failed'
            stop(process, graceful=True)
            assert process.returncode == 0, f'Graceful shutdown exited {process.returncode}'
        finally:
            stop(process)
    with socket.socket() as probe:
        assert probe.connect_ex(('127.0.0.1', port)) != 0, 'Runner left its HTTP listener running'
    run([bash, str(generated), '--check', '--no-browser'], cwd=work, env=offline,
        log=OUTPUT / 'post-shutdown-check.log', timeout=120)
    assert snapshot(lockfiles) == original_source, 'Installation changed source lockfiles/developer venv'
    assert digest(project / '.env') == configuration, 'Runner changed saved configuration'
    assert snapshot(personal) == original_personal, 'Personal configuration changed'
    assert dict(os.environ) == original_environment, 'Parent process environment changed'
    for name in ('XDG data', 'XDG cache', 'XDG config'):
        assert not (work / name).exists(), 'Installation wrote to an external user-profile directory'
    logs = data / 'logs'
    if logs.exists():
        shutil.copytree(logs, OUTPUT / 'application-logs', dirs_exist_ok=True)
    return {'platform': sys.platform, 'architecture': platform.machine(), 'home_unchanged': True,
            'source_and_personal_config_unchanged': True, 'offline_reuse': True,
            'private_intel_toolchain': bool(toolchain),
            'http_ready': True, 'graceful_shutdown': True, 'post_shutdown_lock_released': True,
            'python': subprocess.check_output([str(python), '--version'], text=True).strip(),
            'uv': subprocess.check_output([str(uv), '--version'], text=True).strip(),
            'node': subprocess.check_output([str(node), '--version'], text=True).strip()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-check', action='store_true')
    args = parser.parse_args()
    check_sources()
    if args.source_check:
        return
    if sys.platform not in {'linux', 'darwin'}:
        parser.error('Native smoke tests require Linux/macOS; use --source-check elsewhere')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='gravewright-posix-') as temporary:
        work = Path(temporary).resolve()
        try:
            report = exercise(work)
            (OUTPUT / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        finally:
            logs = work / 'Runner state ç/logs'
            if logs.exists():
                shutil.copytree(logs, OUTPUT / 'application-logs', dirs_exist_ok=True)
    print(f'POSIX Runner smoke passed. Diagnostics: {OUTPUT}', flush=True)


if __name__ == '__main__':
    main()
