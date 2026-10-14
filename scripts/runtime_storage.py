"""Keep managed runtimes, caches and temporary files with the extracted project."""

import os
from pathlib import Path
import tempfile


def configure_runtime_storage(project, tools_root=None):
    """Set local runtime paths before launching tools or loading app settings.

    Defaults use ``project/data/runner``. Explicit tool-root overrides remain
    supported, with relative paths resolved against the project's final root.
    This never reads or imports runtime state from AppData, XDG or Home.
    Return the resolved tools directory for launchers and other callers.
    """
    project = Path(project).resolve()
    configured = tools_root if tools_root is not None else os.environ.get('GRAVEWRIGHT_RUNNER_ROOT')
    path = Path(configured or 'data/runner').expanduser()
    directory = (path if path.is_absolute() else project / path).resolve()
    temporary = directory / 'tmp'
    temporary.mkdir(parents=True, exist_ok=True)
    values = {
        'GRAVEWRIGHT_RUNNER_ROOT': str(directory),
        'UV_CACHE_DIR': str(directory / 'cache'),
        'UV_PYTHON_INSTALL_DIR': str(directory / 'python'),
        'UV_PYTHON_BIN_DIR': str(directory / 'python-bin'),
        'UV_PYTHON_INSTALL_BIN': '0',
        'UV_PYTHON_INSTALL_REGISTRY': '0',
        'UV_PYTHON_NO_REGISTRY': '1',
        'npm_config_cache': str(directory / 'npm-cache'),
        'CARGO_HOME': str(directory / 'cargo'),
        'RUSTUP_HOME': str(directory / 'rustup'),
        'XDG_CACHE_HOME': str(directory / 'xdg-cache'),
        'XDG_DATA_HOME': str(directory / 'xdg-data'),
        'XDG_CONFIG_HOME': str(directory / 'xdg-config'),
        'TEMP': str(temporary),
        'TMP': str(temporary),
        'TMPDIR': str(temporary),
    }
    if os.name == 'nt':
        # Windows Shell/COM helpers also create process-local metadata caches.
        # Redirect those children without changing the user's HOME or profile.
        local = directory / 'profile/local'
        roaming = directory / 'profile/roaming'
        local.mkdir(parents=True, exist_ok=True)
        roaming.mkdir(parents=True, exist_ok=True)
        values.update(LOCALAPPDATA=str(local), APPDATA=str(roaming))
    os.environ.update(values)
    # Dependencies may already have cached the platform's profile temp folder.
    # Setting this explicitly also prevents tempfile's global fallback search.
    tempfile.tempdir = str(temporary)
    return directory
