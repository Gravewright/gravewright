"""Generate the machine-specific startup BAT after installation succeeds."""

import argparse
import hashlib
import os
from pathlib import Path
import secrets
import sys


def batch_value(value):
    value = str(value)
    if any(char in value for char in '\r\n"'):
        raise ValueError('Runner paths cannot contain quotes or newlines.')
    return value.replace('%', '%%')


def create_runner(project, python, data, uv=None, runtime_project=None):
    project = Path(project).resolve()
    launchers = Path(data).resolve() / '.runner-launchers'
    launchers.mkdir(parents=True, exist_ok=True)
    bootstrap_raw = (project / 'scripts/windows/launch_runner.py').read_bytes()
    bootstrap = launchers / (hashlib.sha256(bootstrap_raw).hexdigest() + '.py')
    if not bootstrap.exists():
        bootstrap.write_bytes(bootstrap_raw)
    elif bootstrap.read_bytes() != bootstrap_raw:
        raise ValueError('The saved recovery helper has changed')
    template = (project / 'scripts/windows/runner.bat').read_text(encoding='utf-8')
    content = template.replace('@@PYTHON@@', batch_value(Path(python).resolve()))
    content = content.replace('@@DATA@@', batch_value(Path(data).resolve()))
    content = content.replace('@@UV@@', batch_value(uv or os.environ.get('GW_UV', '')))
    content = content.replace('@@PROJECT@@', batch_value(Path(runtime_project).resolve() if runtime_project else project))
    content = content.replace('@@BOOTSTRAP@@', batch_value(bootstrap))
    raw = content.replace('\r\n', '\n').replace('\n', '\r\n').encode('utf-8')
    # CMD must not keep executing the project BAT while an update replaces it.
    # Transfer control (without CALL) to an immutable copy outside the project.
    launcher = launchers / (hashlib.sha256(raw).hexdigest() + '.bat')
    if not launcher.exists():
        launcher.write_bytes(raw)
    elif launcher.read_bytes() != raw:
        raise ValueError('The saved runner copy has changed')
    wrapper = ('@echo off\r\nsetlocal EnableExtensions DisableDelayedExpansion\r\n'
               'for /f "tokens=2 delims=:" %%C in (\'chcp\') do set "GW_LAUNCHER_CODEPAGE=%%C"\r\n'
               'chcp 65001 >nul\r\n'
               f'set "GW_PYTHON={batch_value(Path(python).resolve())}"\r\n'
               f'"{batch_value(launcher)}" %*\r\n')
    destination = project / 'Gravewright Runner.bat'
    temporary = destination.with_name(f'.Gravewright-{secrets.token_hex(8)}.bat')
    try:
        temporary.write_bytes(wrapper.encode('utf-8'))
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', required=True, type=Path)
    parser.add_argument('--runtime-project', type=Path, help='Final project path when preparing a staged update.')
    args = parser.parse_args()
    print(f'Created: {create_runner(Path(__file__).resolve().parents[2], sys.executable, args.data_dir, runtime_project=args.runtime_project)}')
