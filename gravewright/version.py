"""Read the installed release identity from the project's Python metadata."""

from functools import cache
from pathlib import Path
import tomllib

from gravewright.administration.release_metadata import normalize_version, version_label


@cache
def release_version():
    """Return the public identifier used by npm metadata and release artifacts."""
    project = Path(__file__).resolve().parent.parent / 'pyproject.toml'
    return normalize_version(tomllib.loads(project.read_text(encoding='utf-8'))['project']['version'])


def release_label():
    """Return the user-facing name, for example Alpha 0.1.0."""
    return version_label(release_version())
