"""Create native launchers for a prepared Linux or macOS installation."""

import argparse
import hashlib
import os
from pathlib import Path
import re
import secrets
import shlex
import sys


def shell_value(value):
    value = str(value)
    if any(char in value for char in '\0\r\n'):
        raise ValueError('Runner paths cannot contain NUL or newlines.')
    return shlex.quote(value)


def desktop_value(value):
    """Escape a Desktop Entry string, before the Exec field's own parsing."""
    return str(value).replace('\\', '\\\\').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')


def desktop_argument(value):
    # Exec is not a shell command: quote reserved characters for its tokenizer,
    # escape field codes, then apply the Desktop Entry string escapes.
    value = str(value).replace('%', '%%')
    value = re.sub(r'([\\"`$])', r'\\\1', value)
    return desktop_value('"' + value + '"')


def atomic_write(path, raw, mode=0o755):
    temporary = path.with_name('.Gravewright-' + secrets.token_hex(8) + path.suffix)
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(raw)
        temporary.chmod(mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def immutable(directory, raw, suffix, mode):
    path = directory / (hashlib.sha256(raw).hexdigest() + suffix)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('The saved recovery launcher has changed')
    else:
        atomic_write(path, raw, mode)
    return path


def build_environment(platform):
    """Keep verified native build tools available to later managed updates."""
    names = ('GRAVEWRIGHT_BUILD_TOOLS_PATH', 'OPENSSL_DIR', 'OPENSSL_STATIC', 'CARGO_HOME')
    values = {name: os.environ.get(name, '') for name in names}
    values['AUTOBAHN_USE_NVX'] = '0' if platform == 'darwin' else ''
    lines = []
    for name, value in values.items():
        if value:
            lines += [name + '=' + shell_value(value), 'export ' + name]
        else:
            # Do not borrow an unrelated shell's build configuration at startup.
            lines.append('unset ' + name)
    return '\n'.join(lines)


def create_runner(project, python, data, uv=None, runtime_project=None, *, port=None,
                  no_browser=False, platform=None):
    project = Path(project).resolve()
    runtime_project = Path(runtime_project).resolve() if runtime_project else project
    data = Path(data).expanduser().resolve()
    # Resolving bin/python follows a venv symlink to the shared interpreter,
    # which silently loses all the prepared virtual environment's packages.
    python = Path(os.path.abspath(python))
    platform = platform or sys.platform
    if platform not in {'linux', 'darwin'}:
        raise ValueError('The POSIX Runner supports Linux and macOS.')
    if port is not None and not 1 <= int(port) <= 65535:
        raise ValueError('The Runner port must be from 1 to 65535.')
    launchers = data / '.runner-launchers'
    launchers.mkdir(parents=True, exist_ok=True, mode=0o700)
    # This helper already uses native POSIX flock/execv, and is shared with
    # Windows so interrupted-update recovery has one implementation.
    bootstrap = immutable(launchers,
                          (project / 'scripts/windows/launch_runner.py').read_bytes(),
                          '.py', 0o600)
    defaults = []
    if port is not None:
        defaults += ['--port', str(int(port))]
    if no_browser:
        defaults.append('--no-browser')
    substitutions = {
        'PYTHON': shell_value(python), 'DATA': shell_value(data),
        'UV': shell_value(uv if uv is not None else os.environ.get('GW_UV', '')),
        'PROJECT': shell_value(runtime_project), 'BOOTSTRAP': shell_value(bootstrap),
        'DEFAULT_ARGS': shlex.join(defaults),
        'BUILD_ENV': build_environment(platform),
    }
    template = (project / 'scripts/posix/runner.sh').read_text(encoding='utf-8')
    content = re.sub(r'@@([A-Z_]+)@@', lambda match: substitutions[match[1]], template)
    suffix = '.command' if platform == 'darwin' else '.sh'
    launcher = immutable(launchers, content.replace('\r\n', '\n').encode('utf-8'), suffix, 0o700)
    # POSIX shells may read scripts incrementally. exec the external immutable
    # copy before the updater can replace this small project entrypoint.
    wrapper = '#!/bin/sh\nexec /bin/sh ' + shell_value(launcher) + ' "$@"\n'
    destination = project / ('Gravewright Runner' + suffix)
    atomic_write(destination, wrapper.encode('utf-8'))
    if platform == 'linux':
        desktop = (
            '[Desktop Entry]\nType=Application\nVersion=1.0\n'
            'Name=Gravewright\nComment=Start your Gravewright virtual tabletop\n'
            'Terminal=true\nCategories=Game;RolePlaying;\n'
            'Exec=/bin/sh ' + desktop_argument(runtime_project / destination.name) + '\n'
            'Path=' + desktop_value(runtime_project) + '\n'
            'Icon=' + desktop_value(runtime_project / 'gravewright/web/static/gravewright_web/favicon.svg') + '\n'
        )
        atomic_write(project / 'Gravewright Runner.desktop', desktop.encode('utf-8'))
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--runtime-project', type=Path,
                        help='Final project path when preparing a staged update.')
    parser.add_argument('--port', type=int)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    print(f'Created: {create_runner(Path(__file__).resolve().parents[2], sys.executable, args.data_dir, runtime_project=args.runtime_project, port=args.port, no_browser=args.no_browser)}')


if __name__ == '__main__':
    main()
